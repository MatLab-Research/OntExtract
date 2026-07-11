"""Experiment-scoped temporal-expression result read model."""

from app import db
from app.models.experiment import Experiment
from app.models.experiment_document import ExperimentDocument
from app.models.experiment_processing import (
    ExperimentDocumentProcessing,
    ProcessingArtifact,
)
from app.services.base_service import NotFoundError


class ExperimentTemporalResultsService:
    """Normalize completed temporal artifacts belonging to one experiment."""

    @classmethod
    def get_context(cls, experiment_id):
        experiment = db.session.get(Experiment, experiment_id)
        if not experiment:
            raise NotFoundError(f'Experiment {experiment_id} not found')
        documents = cls._latest_documents(experiment_id)
        document_ids = [document.id for document in documents]
        lookup = {document.id: document for document in documents}
        expressions = [
            cls._expression(artifact, lookup.get(artifact.document_id))
            for artifact in cls._artifacts(experiment_id, document_ids)
        ]
        expressions.sort(key=lambda item: (
            item.get('document_year') or 9999,
            item.get('start_position')
            if item.get('start_position') is not None else 0,
            item['id'],
        ))
        by_type = {}
        by_document = {}
        for expression in expressions:
            by_type.setdefault(expression['type'], []).append(expression)
            document_id = expression['document_id']
            by_document.setdefault(document_id, {
                'document': lookup.get(document_id),
                'expressions': [],
            })['expressions'].append(expression)
        return {
            'experiment': experiment,
            'documents': documents,
            'temporal_expressions': expressions,
            'expressions_by_type': by_type,
            'expressions_by_document': by_document,
            'total_expressions': len(expressions),
        }

    @staticmethod
    def _latest_documents(experiment_id):
        associations = ExperimentDocument.query.filter_by(
            experiment_id=experiment_id
        ).all()
        families = {}
        for association in associations:
            document = association.document
            root_id = document.source_document_id or document.id
            families.setdefault(root_id, []).append(document)
        documents = [
            max(
                family,
                key=lambda document: (
                    document.version_number or 0,
                    document.id,
                ),
            )
            for family in families.values()
        ]
        documents.sort(key=lambda document: document.id)
        return documents

    @staticmethod
    def _artifacts(experiment_id, document_ids):
        if not document_ids:
            return []
        return ProcessingArtifact.query.join(
            ExperimentDocumentProcessing,
            ProcessingArtifact.processing_id == ExperimentDocumentProcessing.id,
        ).join(
            ExperimentDocument,
            ExperimentDocumentProcessing.experiment_document_id
            == ExperimentDocument.id,
        ).filter(
            ExperimentDocument.experiment_id == experiment_id,
            ExperimentDocument.document_id.in_(document_ids),
            ExperimentDocumentProcessing.status == 'completed',
            ProcessingArtifact.artifact_type == 'temporal_marker',
        ).order_by(
            ProcessingArtifact.document_id,
            ProcessingArtifact.artifact_index,
            ProcessingArtifact.created_at,
            ProcessingArtifact.id,
        ).all()

    @classmethod
    def _expression(cls, artifact, document):
        content = artifact.get_content()
        metadata = artifact.get_metadata()
        metadata = metadata if isinstance(metadata, dict) else {}
        if isinstance(content, str):
            values = {'text': content}
        elif isinstance(content, dict):
            values = content
        else:
            values = {}
        expression_type = cls._text(values.get('type'), 'UNKNOWN').upper()
        method = cls._text(
            metadata.get('method'),
            artifact.processing_operation.processing_method
            if artifact.processing_operation else 'unknown',
        )
        start = values.get('start')
        end = values.get('end')
        if start is None:
            start = metadata.get('start_char')
        if end is None:
            end = metadata.get('end_char')
        return {
            'id': f'artifact_{artifact.id}',
            'text': cls._text(values.get('text')),
            'type': expression_type,
            'normalized': values.get('normalized'),
            'start_position': cls._position(start),
            'end_position': cls._position(end),
            'confidence': cls._confidence(values.get('confidence', 0.75)),
            'context': cls._text(values.get('context')),
            'method': method,
            'source': cls._source(method, metadata),
            **cls._document_fields(artifact.document_id, document),
        }

    @staticmethod
    def _source(method, metadata):
        source = metadata.get('source')
        if isinstance(source, str) and source.strip():
            return source.strip()
        normalized = method.casefold()
        if 'langextract' in normalized or 'orchestrat' in normalized:
            return 'orchestration'
        if 'spacy' in normalized:
            return 'spacy'
        return 'processing'

    @staticmethod
    def _document_fields(document_id, document):
        return {
            'document_id': document_id,
            'document_title': (
                document.title if document else f'Document {document_id}'
            ),
            'document_uuid': str(document.uuid) if document else None,
            'document_year': (
                document.publication_date.year
                if document and document.publication_date else None
            ),
        }

    @staticmethod
    def _text(value, default=''):
        return value.strip() if isinstance(value, str) and value.strip() else default

    @staticmethod
    def _position(value):
        try:
            value = int(value)
        except (TypeError, ValueError):
            return None
        return value if value >= 0 else None

    @staticmethod
    def _confidence(value):
        try:
            value = float(value)
        except (TypeError, ValueError):
            return 0.0
        return max(0.0, min(value, 1.0))
