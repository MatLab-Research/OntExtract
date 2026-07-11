"""Read models for experiment detail and manual results pages."""

import json
import logging

from sqlalchemy import func

from app import db
from app.models import Document, Experiment
from app.models.experiment_document import ExperimentDocument
from app.models.experiment_orchestration_run import ExperimentOrchestrationRun
from app.models.experiment_processing import (
    ExperimentDocumentProcessing,
    ProcessingArtifact,
)
from app.services.base_service import NotFoundError


logger = logging.getLogger(__name__)


class ExperimentDetailReadService:
    """Build canonical experiment dashboard and manual-result contexts."""

    ARTIFACT_TYPE_MAP = {
        'extracted_entity': 'entities',
        'term_definition': 'definitions',
        'temporal_marker': 'temporal',
        'embedding_vector': 'embeddings',
        'text_segment': 'segmentation',
    }

    @classmethod
    def get_detail_context(cls, experiment_id):
        experiment = cls._get_experiment(experiment_id)
        experiment_documents = cls._experiment_documents(experiment_id)
        latest_documents = cls._latest_family_members(experiment_documents)
        processing_summary = cls._artifact_summary(experiment_id)
        context = {
            'experiment': experiment,
            'recent_orchestration': cls._latest_orchestration(experiment_id),
            'processing_summary': processing_summary,
            'total_processing_ops': sum(processing_summary.values()),
            'documents_enhanced': [
                cls._detail_document(experiment_id, association, document)
                for association, document in latest_documents
            ],
            'temporal_data': None,
        }
        if experiment.experiment_type == 'temporal_evolution':
            context['temporal_data'] = cls._temporal_data(experiment_id)
        return context

    @classmethod
    def get_manual_results_context(cls, experiment_id):
        experiment = cls._get_experiment(experiment_id)
        experiment_documents = cls._experiment_documents(experiment_id)
        latest_documents = cls._latest_family_members(experiment_documents)
        processing_summary = cls._artifact_summary(experiment_id)
        return {
            'experiment': experiment,
            'processing_summary': processing_summary,
            'total_operations': sum(processing_summary.values()),
            'documents_with_processing': [
                cls._result_document(association, document)
                for association, document in latest_documents
            ],
            'config_data': cls._configuration(experiment),
        }

    @staticmethod
    def get_completed_orchestration(experiment_id):
        return ExperimentOrchestrationRun.query.filter_by(
            experiment_id=experiment_id,
            status='completed',
        ).order_by(ExperimentOrchestrationRun.completed_at.desc()).first()

    @staticmethod
    def _get_experiment(experiment_id):
        experiment = db.session.get(Experiment, experiment_id)
        if not experiment:
            raise NotFoundError(f'Experiment {experiment_id} not found')
        return experiment

    @staticmethod
    def _experiment_documents(experiment_id):
        return ExperimentDocument.query.filter_by(
            experiment_id=experiment_id
        ).all()

    @staticmethod
    def _latest_family_members(experiment_documents):
        families = {}
        for association in experiment_documents:
            document = association.document
            root_id = document.source_document_id or document.id
            families.setdefault(root_id, []).append((association, document))
        latest = []
        for family in families.values():
            latest.append(max(
                family,
                key=lambda item: (item[1].version_number or 0, item[1].id),
            ))
        latest.sort(key=lambda item: item[1].id)
        return latest

    @classmethod
    def _artifact_summary(cls, experiment_id):
        counts = db.session.query(
            ProcessingArtifact.artifact_type,
            func.count(ProcessingArtifact.id),
        ).join(
            ExperimentDocumentProcessing,
            ProcessingArtifact.processing_id == ExperimentDocumentProcessing.id,
        ).join(
            ExperimentDocument,
            ExperimentDocumentProcessing.experiment_document_id
            == ExperimentDocument.id,
        ).filter(
            ExperimentDocument.experiment_id == experiment_id,
            ExperimentDocumentProcessing.status == 'completed',
        ).group_by(ProcessingArtifact.artifact_type).all()
        summary = {}
        for artifact_type, count in counts:
            display_type = cls.ARTIFACT_TYPE_MAP.get(artifact_type, artifact_type)
            summary[display_type] = summary.get(display_type, 0) + count
        return summary

    @classmethod
    def _detail_document(cls, experiment_id, association, document):
        operations = cls._completed_operations(association.id)
        grouped = {}
        for operation in operations:
            grouped.setdefault(operation.processing_type, []).append({
                'method_key': operation.processing_method,
                'source': 'manual',
            })
        return {
            'document': document,
            'other_experiments_count': cls._other_experiment_count(
                experiment_id,
                document,
            ),
            'processing_by_type': grouped,
            'processing_count': len(operations),
        }

    @classmethod
    def _result_document(cls, association, document):
        operations = cls._completed_operations(association.id)
        processing = {}
        for operation in operations:
            processing[operation.processing_type] = (
                processing.get(operation.processing_type, 0) + 1
            )
        return {
            'document': document,
            'processing': processing,
            'total_ops': len(operations),
        }

    @staticmethod
    def _completed_operations(experiment_document_id):
        operations = ExperimentDocumentProcessing.query.filter_by(
            experiment_document_id=experiment_document_id,
            status='completed',
        ).order_by(ExperimentDocumentProcessing.created_at.desc()).all()
        unique = []
        seen = set()
        for operation in operations:
            key = (operation.processing_type, operation.processing_method)
            if key not in seen:
                seen.add(key)
                unique.append(operation)
        return unique

    @staticmethod
    def _other_experiment_count(experiment_id, document):
        root_id = document.source_document_id or document.id
        family_ids = [root_id]
        family_ids.extend(
            version.id
            for version in Document.query.filter_by(
                source_document_id=root_id
            ).all()
        )
        experiment_ids = {
            row.experiment_id
            for row in ExperimentDocument.query.filter(
                ExperimentDocument.document_id.in_(family_ids)
            ).all()
        }
        experiment_ids.discard(experiment_id)
        return len(experiment_ids)

    @staticmethod
    def _latest_orchestration(experiment_id):
        return ExperimentOrchestrationRun.query.filter_by(
            experiment_id=experiment_id
        ).order_by(ExperimentOrchestrationRun.started_at.desc()).first()

    @staticmethod
    def _temporal_data(experiment_id):
        try:
            from app.services.temporal_service import get_temporal_service

            return get_temporal_service().get_temporal_ui_data(experiment_id)
        except Exception as exc:
            logger.warning(
                f'Failed to get temporal data for experiment {experiment_id}: {exc}'
            )
            return None

    @staticmethod
    def _configuration(experiment):
        config = experiment.configuration or {}
        if isinstance(config, dict):
            return config
        try:
            parsed = json.loads(config)
            return parsed if isinstance(parsed, dict) else {}
        except (json.JSONDecodeError, TypeError):
            return {}
