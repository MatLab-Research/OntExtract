"""Experiment processing and orchestration run status read models."""

from datetime import datetime, timedelta

from app import db
from app.models.document import Document
from app.models.experiment import Experiment
from app.models.experiment_document import ExperimentDocument
from app.models.experiment_orchestration_run import ExperimentOrchestrationRun
from app.models.experiment_processing import ExperimentDocumentProcessing
from app.models.processing_job import ProcessingJob
from app.models.text_segment import TextSegment
from app.services.base_service import NotFoundError


class OrchestrationStatusService:
    """Build orchestration status payloads with experiment-scoped processing."""

    ACTIVE_RUN_STATUSES = (
        'analyzing', 'recommending', 'reviewing', 'executing', 'synthesizing',
    )
    STAGE_PROGRESS = {
        'analyzing': 20,
        'recommending': 40,
        'reviewing': 50,
        'executing': 70,
        'synthesizing': 90,
        'completed': 100,
        'failed': 0,
    }
    JOB_TYPES = {
        'entity_extraction': 'entities',
        'extract_entities': 'entities',
        'generate_embeddings': 'embeddings',
        'segmentation': 'segmentation',
        'langextract_segmentation': 'segmentation',
    }

    def __init__(self, clock=None):
        self.clock = clock or datetime.utcnow

    @classmethod
    def get_experiment_processing_status(cls, experiment_id):
        experiment = cls._experiment(experiment_id)
        canonical = ExperimentDocument.query.filter_by(
            experiment_id=experiment_id
        ).all()
        canonical_by_document = {
            association.document_id: association
            for association in canonical
        }
        legacy_documents = Document.query.filter_by(
            experiment_id=experiment_id
        ).all()
        document_ids = set(canonical_by_document)
        document_ids.update(document.id for document in legacy_documents)
        documents = {
            document.id: document
            for document in Document.query.filter(Document.id.in_(document_ids)).all()
        } if document_ids else {}

        statuses = []
        for document_id in sorted(document_ids):
            association = canonical_by_document.get(document_id)
            if association:
                processing_types = cls._canonical_processing_types(association.id)
            else:
                processing_types = cls._legacy_processing_types(document_id)
            document = documents.get(document_id)
            statuses.append({
                'document_id': document_id,
                'title': document.title if document else f'Document {document_id}',
                'has_processing': bool(processing_types),
                'processing_types': processing_types,
            })

        processed_count = sum(item['has_processing'] for item in statuses)
        total = len(statuses)
        return {
            'experiment_id': experiment.id,
            'total_documents': total,
            'processed_documents': processed_count,
            'unprocessed_documents': total - processed_count,
            'has_partial_processing': 0 < processed_count < total,
            'has_full_processing': processed_count == total and total > 0,
            'documents': statuses,
        }

    def get_latest_active_run(self, experiment_id):
        self._experiment(experiment_id)
        threshold = self.clock() - timedelta(minutes=30)
        run = ExperimentOrchestrationRun.query.filter_by(
            experiment_id=experiment_id
        ).filter(
            ExperimentOrchestrationRun.status.in_(self.ACTIVE_RUN_STATUSES),
            ExperimentOrchestrationRun.started_at >= threshold,
        ).order_by(ExperimentOrchestrationRun.started_at.desc()).first()
        if not run:
            raise NotFoundError('No active orchestration run found')
        return {
            'run_id': str(run.id),
            'status': run.status,
            'current_stage': run.current_stage,
            'started_at': run.started_at.isoformat() if run.started_at else None,
        }

    @classmethod
    def get_run_status(cls, run_id):
        run = db.session.get(ExperimentOrchestrationRun, run_id)
        if not run:
            raise NotFoundError('Orchestration run not found')
        response = {
            'run_id': str(run.id),
            'status': run.status,
            'current_stage': run.current_stage or run.status,
            'current_operation': run.current_operation,
            'progress_percentage': cls.STAGE_PROGRESS.get(run.status, 0),
            'error_message': run.error_message,
            'stage_completed': {
                'analyze_experiment': run.experiment_goal is not None,
                'recommend_strategy': run.recommended_strategy is not None,
                'human_review': bool(run.strategy_approved),
                'execute_strategy': run.processing_results is not None,
                'synthesize_experiment': run.cross_document_insights is not None,
            },
        }
        if run.status == 'reviewing':
            response.update({
                'awaiting_user_approval': True,
                'recommended_strategy': run.recommended_strategy,
                'strategy_reasoning': run.strategy_reasoning,
                'confidence': run.confidence,
                'experiment_goal': run.experiment_goal,
            })
        if run.status == 'completed':
            response['completed_at'] = (
                run.completed_at.isoformat() if run.completed_at else None
            )
            response['duration_seconds'] = (
                (run.completed_at - run.started_at).total_seconds()
                if run.completed_at and run.started_at else None
            )
        return response

    @staticmethod
    def _canonical_processing_types(association_id):
        operations = ExperimentDocumentProcessing.query.filter_by(
            experiment_document_id=association_id,
            status='completed',
        ).order_by(ExperimentDocumentProcessing.created_at).all()
        return sorted({operation.processing_type for operation in operations})

    @classmethod
    def _legacy_processing_types(cls, document_id):
        types = set()
        if TextSegment.query.filter_by(document_id=document_id).first():
            types.add('segmentation')
        jobs = ProcessingJob.query.filter_by(
            document_id=document_id,
            status='completed',
        ).all()
        for job in jobs:
            types.add(cls.JOB_TYPES.get(job.job_type, job.job_type))
        return sorted(types)

    @staticmethod
    def _experiment(experiment_id):
        experiment = db.session.get(Experiment, experiment_id)
        if not experiment:
            raise NotFoundError('Experiment not found')
        return experiment
