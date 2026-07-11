"""Human review preparation and approval for orchestration strategies."""

import json
import logging
from datetime import datetime

from app import db
from app.models import Document, Experiment
from app.models.experiment_orchestration_run import ExperimentOrchestrationRun
from app.models.temporal_experiment import DocumentTemporalMetadata
from app.services.base_service import NotFoundError, ValidationError
from app.services.orchestration_read_service import OrchestrationReadService


logger = logging.getLogger(__name__)


def _configuration_dict(experiment):
    """Return an experiment configuration as a mutable dictionary."""
    config = experiment.configuration or {}
    if isinstance(config, str):
        try:
            config = json.loads(config)
        except (json.JSONDecodeError, TypeError):
            config = {}
    return config if isinstance(config, dict) else {}


class OrchestrationReviewService:
    """Build the presentation context for a strategy review."""

    @classmethod
    def build_review_context(cls, experiment_id, run_id):
        experiment = db.session.get(Experiment, experiment_id)
        if not experiment:
            raise NotFoundError(f"Experiment {experiment_id} not found")

        run = db.session.get(ExperimentOrchestrationRun, run_id)
        if not run or run.experiment_id != experiment_id:
            raise NotFoundError(f"Orchestration run {run_id} not found")
        if run.status != 'reviewing':
            raise ValidationError(
                f'Orchestration run is not in review state (current: {run.status})'
            )

        documents = Document.query.filter_by(experiment_id=experiment_id).all()
        context = {
            'experiment': experiment,
            'run': run,
            'documents': [cls._serialize_document(document) for document in documents],
            'recommended_strategy': run.recommended_strategy or {},
            'has_existing_periods': False,
            'existing_periods': [],
            'suggested_periods': [],
            'time_periods': [],
            'period_documents': {},
            'period_metadata': {},
        }

        if experiment.experiment_type == 'temporal_evolution':
            cls._add_temporal_context(context, documents)
        return context

    @staticmethod
    def _serialize_document(document):
        return {
            'id': document.id,
            'uuid': str(document.uuid),
            'title': document.title or 'Untitled',
            'authors': document.authors,
            'publication_year': (
                document.publication_date.year
                if document.publication_date else None
            ),
            'word_count': document.word_count,
        }

    @classmethod
    def _add_temporal_context(cls, context, documents):
        experiment = context['experiment']
        config = _configuration_dict(experiment)
        named_periods = config.get('named_periods', [])
        period_documents = config.get('period_documents', {})

        if named_periods:
            context['has_existing_periods'] = True
            context['existing_periods'] = [
                cls._serialize_named_period(period, period_documents)
                for period in named_periods
            ]
        else:
            existing_metadata = DocumentTemporalMetadata.query.filter_by(
                experiment_id=experiment.id
            ).all()
            if existing_metadata:
                context['has_existing_periods'] = True
                context['existing_periods'] = cls._group_temporal_metadata(
                    existing_metadata
                )

        if not context['has_existing_periods']:
            context['suggested_periods'] = [
                cls._suggest_period(document)
                for document in documents
                if document.publication_date
            ]

        context['time_periods'] = config.get('time_periods', [])
        context['period_documents'] = config.get('period_documents', {})
        context['period_metadata'] = config.get('period_metadata', {})

    @staticmethod
    def _serialize_named_period(period, period_documents):
        start_year = period.get('start_year')
        end_year = period.get('end_year')
        document_count = 0
        for year_string, documents in period_documents.items():
            try:
                year = int(year_string)
                if start_year and end_year and start_year <= year <= end_year:
                    document_count += (
                        len(documents) if isinstance(documents, list) else 1
                    )
            except (ValueError, TypeError):
                pass
        return {
            'temporal_period': period.get('name', 'Unnamed Period'),
            'temporal_start_year': start_year,
            'temporal_end_year': end_year,
            'description': period.get('description', ''),
            'marker_color': '#6c757d',
            'document_count': document_count,
        }

    @staticmethod
    def _group_temporal_metadata(metadata_records):
        periods = {}
        for metadata in metadata_records:
            period_name = metadata.temporal_period
            if period_name not in periods:
                periods[period_name] = {
                    'temporal_period': period_name,
                    'temporal_start_year': metadata.temporal_start_year,
                    'temporal_end_year': metadata.temporal_end_year,
                    'marker_color': metadata.marker_color,
                    'document_count': 0,
                }
            periods[period_name]['document_count'] += 1
        return list(periods.values())

    @staticmethod
    def _suggest_period(document):
        year = document.publication_date.year
        title = document.title or 'Untitled'
        return {
            'name': f'{title[:30]}...' if len(title) > 30 else title,
            'start_year': year,
            'end_year': year,
            'document_id': document.id,
            'document_count': 1,
        }


class OrchestrationApprovalService:
    """Apply a review decision and queue an approved strategy for execution."""

    @classmethod
    def apply_decision(cls, run_id, data, reviewer_id):
        _, run = OrchestrationReadService.authorized_run(run_id, reviewer_id)
        if run.status != 'reviewing':
            raise ValidationError(
                f'Cannot approve strategy in {run.status} state'
            )

        if not data.get('strategy_approved', True):
            run.status = 'cancelled'
            run.review_notes = data.get(
                'review_notes',
                'User rejected strategy',
            )
            db.session.commit()
            return {
                'success': True,
                'status': 'cancelled',
                'message': 'Strategy rejected',
            }

        cls._generate_temporal_periods(run, data)
        run.strategy_approved = True
        run.modified_strategy = data.get('modified_strategy')
        run.review_notes = data.get('review_notes')
        run.reviewed_by = reviewer_id
        run.reviewed_at = datetime.utcnow()
        run.status = 'executing'
        run.current_stage = 'executing'
        db.session.commit()

        task = cls._dispatch_execution(run, data, reviewer_id)
        run.celery_task_id = task.id
        db.session.commit()
        logger.info(
            f'Started Celery task {task.id} for execution phase of run {run.id}'
        )
        return {
            'success': True,
            'status': 'executing',
            'message': 'Strategy approved - processing started in background',
        }

    @staticmethod
    def _dispatch_execution(run, data, reviewer_id):
        from app.tasks.orchestration import run_execution_phase_task

        return run_execution_phase_task.delay(
            str(run.id),
            modified_strategy=data.get('modified_strategy'),
            review_notes=data.get('review_notes'),
            reviewer_id=reviewer_id,
        )

    @classmethod
    def _generate_temporal_periods(cls, run, data):
        suggested_periods = data.get('suggested_periods', [])
        if not data.get('generate_periods', False) or not suggested_periods:
            return

        experiment = run.experiment
        if not experiment or experiment.experiment_type != 'temporal_evolution':
            return

        existing_metadata = DocumentTemporalMetadata.query.filter_by(
            experiment_id=experiment.id
        ).first()
        config = _configuration_dict(experiment)
        if existing_metadata or config.get('named_periods'):
            return

        periods = []
        period_documents = {}
        created_count = 0
        for period_data in suggested_periods:
            document_id = period_data.get('document_id')
            start_year = period_data.get('start_year')
            if not document_id or not start_year:
                continue

            period_name = period_data.get('name', '')
            end_year = period_data.get('end_year')
            db.session.add(DocumentTemporalMetadata(
                document_id=document_id,
                experiment_id=experiment.id,
                temporal_period=period_name,
                temporal_start_year=start_year,
                temporal_end_year=end_year or start_year,
                publication_year=start_year,
                extraction_method='auto_generated',
            ))
            created_count += 1
            if start_year not in periods:
                periods.append(start_year)
            period_documents.setdefault(str(start_year), []).append({
                'id': document_id,
                'title': period_name,
                'date_source': 'publication_date',
            })

        periods.sort()
        config['time_periods'] = periods
        config['period_documents'] = period_documents
        config['period_metadata'] = {
            str(year): {
                'source': 'auto-generated',
                'document_count': len(period_documents.get(str(year), [])),
            }
            for year in periods
        }
        if periods:
            config['start_year'] = min(periods)
            config['end_year'] = max(periods)
            config['periods_source'] = 'orchestration'
        experiment.configuration = json.dumps(config)
        db.session.flush()
        logger.info(
            f'Generated temporal metadata for {created_count} documents '
            f'in experiment {experiment.id}'
        )
