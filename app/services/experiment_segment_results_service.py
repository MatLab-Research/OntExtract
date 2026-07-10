"""Experiment-scoped segmentation result read model."""

from sqlalchemy import func

from app import db
from app.models.document import Document
from app.models.experiment import Experiment
from app.models.experiment_document import ExperimentDocument
from app.models.experiment_processing import (
    ExperimentDocumentProcessing,
    ProcessingArtifact,
)
from app.models.text_segment import TextSegment
from app.services.base_service import NotFoundError


class ExperimentSegmentResultsService:
    """Normalize canonical and demonstrably owned segmentation results."""

    @classmethod
    def get_context(cls, experiment_id):
        experiment = db.session.get(Experiment, experiment_id)
        if not experiment:
            raise NotFoundError(f'Experiment {experiment_id} not found')
        documents = cls._latest_documents(experiment_id)
        document_ids = [document.id for document in documents]
        lookup = {document.id: document for document in documents}
        segments = []
        grouped = {}

        artifacts = cls._canonical_artifacts(experiment_id, document_ids)
        canonical_document_ids = set()
        for artifact in artifacts:
            canonical_document_ids.add(artifact.document_id)
            cls._append(
                segments,
                grouped,
                cls._artifact_segment(
                    artifact,
                    lookup.get(artifact.document_id),
                ),
                lookup,
            )

        fallback_ids = [
            document_id for document_id in document_ids
            if document_id not in canonical_document_ids
        ]
        for segment in cls._owned_text_segments(experiment_id, fallback_ids):
            cls._append(
                segments,
                grouped,
                cls._text_segment(
                    segment,
                    lookup.get(segment.document_id),
                ),
                lookup,
            )

        segments.sort(key=lambda item: (
            item.get('document_year') or 9999,
            item['document_id'],
            item.get('segment_number') or 0,
            str(item['id']),
        ))
        total = len(segments)
        return {
            'experiment': experiment,
            'documents': documents,
            'segments': segments,
            'segments_by_document': grouped,
            'total_segments': total,
            'avg_length': (
                sum(item['character_count'] for item in segments) / total
                if total else 0
            ),
            'avg_words': (
                sum(item['word_count'] for item in segments) / total
                if total else 0
            ),
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

        # Experiment versions can exist before a v2 association is added. Include
        # them in their root family so their owned TextSegment rows remain visible.
        experiment_versions = Document.query.filter_by(
            experiment_id=experiment_id
        ).all()
        for document in experiment_versions:
            root_id = document.source_document_id or document.id
            family = families.setdefault(root_id, [])
            if all(member.id != document.id for member in family):
                family.append(document)

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
    def _canonical_artifacts(experiment_id, document_ids):
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
            ProcessingArtifact.artifact_type == 'text_segment',
        ).order_by(
            ProcessingArtifact.document_id,
            ProcessingArtifact.artifact_index,
            ProcessingArtifact.created_at,
        ).all()

    @classmethod
    def _owned_text_segments(cls, experiment_id, document_ids):
        if not document_ids:
            return []
        counts = dict(db.session.query(
            ExperimentDocument.document_id,
            func.count(func.distinct(ExperimentDocument.experiment_id)),
        ).filter(
            ExperimentDocument.document_id.in_(document_ids)
        ).group_by(ExperimentDocument.document_id).all())
        allowed_ids = [
            document.id
            for document in Document.query.filter(Document.id.in_(document_ids)).all()
            if (
                document.experiment_id == experiment_id
                or (
                    document.experiment_id is None
                    and counts.get(document.id, 0) == 1
                )
            )
        ]
        if not allowed_ids:
            return []
        return TextSegment.query.filter(
            TextSegment.document_id.in_(allowed_ids)
        ).order_by(
            TextSegment.document_id,
            TextSegment.segment_number,
            TextSegment.created_at,
            TextSegment.id,
        ).all()

    @classmethod
    def _artifact_segment(cls, artifact, document):
        content = artifact.get_content()
        metadata = artifact.get_metadata()
        metadata = metadata if isinstance(metadata, dict) else {}
        if isinstance(content, str):
            text = content
            segment_type = metadata.get('method', 'unknown')
        elif isinstance(content, dict):
            text = content.get('text', '')
            segment_type = content.get(
                'segment_type',
                metadata.get('method', 'unknown'),
            )
        else:
            text = ''
            segment_type = metadata.get('method', 'unknown')
        default_words = len(text.split()) if text else 0
        return {
            'id': f'artifact_{artifact.id}',
            'segment_number': (artifact.artifact_index or 0) + 1,
            'content': text,
            'word_count': metadata.get('word_count', default_words),
            'character_count': len(text),
            'method': segment_type,
            'source': 'artifact',
            **cls._document_fields(artifact.document_id, document),
        }

    @classmethod
    def _text_segment(cls, segment, document):
        text = segment.content or ''
        explicit_method = segment.segmentation_method
        if not explicit_method or explicit_method == 'manual':
            explicit_method = segment.segment_type or explicit_method
        return {
            'id': segment.id,
            'segment_number': segment.segment_number,
            'content': text,
            'word_count': (
                segment.word_count
                if segment.word_count is not None else len(text.split())
            ),
            'character_count': (
                segment.character_count
                if segment.character_count is not None else len(text)
            ),
            'method': explicit_method or 'paragraph',
            'source': 'text_segment',
            **cls._document_fields(segment.document_id, document),
        }

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
    def _append(segments, grouped, segment, lookup):
        segments.append(segment)
        document_id = segment['document_id']
        grouped.setdefault(document_id, {
            'document': lookup.get(document_id),
            'segments': [],
        })['segments'].append(segment)
