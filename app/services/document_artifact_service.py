"""Document-family embedding and segmentation artifact read models."""

from uuid import UUID

from app import db
from app.models import Document, ProcessingJob, TextSegment
from app.models.experiment_processing import ProcessingArtifact
from app.services.base_service import NotFoundError
from app.services.processing_results import get_document_family_ids


class DocumentArtifactService:
    """Read unified artifacts and legacy job metadata for document APIs."""

    @classmethod
    def get_embeddings(cls, document_id):
        document = db.session.get(Document, document_id)
        if not document:
            raise NotFoundError(f'Document {document_id} not found')
        root = document.get_root_document()
        family_ids = get_document_family_ids(root)
        versions = cls._versions_by_id(family_ids)

        artifacts = ProcessingArtifact.query.filter(
            ProcessingArtifact.document_id.in_(family_ids),
            ProcessingArtifact.artifact_type == 'embedding_vector',
        ).order_by(ProcessingArtifact.created_at.desc()).all()
        embeddings = [
            cls._serialize_artifact(artifact, versions.get(artifact.document_id))
            for artifact in artifacts
        ]
        if not embeddings:
            embeddings = cls._legacy_embeddings(family_ids, versions)

        return {
            'success': True,
            'document_id': document_id,
            'source_document_id': root.id,
            'embeddings': embeddings,
            'count': len(embeddings),
            'processed_versions_count': len(versions),
        }

    @classmethod
    def get_embedding_preview(cls, embedding_id):
        if str(embedding_id).startswith('job_'):
            return {
                'success': True,
                'embedding': cls._legacy_preview(embedding_id),
            }
        try:
            artifact_uuid = UUID(str(embedding_id))
        except (TypeError, ValueError, AttributeError):
            raise NotFoundError('Embedding not found')

        artifact = db.session.get(ProcessingArtifact, artifact_uuid)
        if not artifact or artifact.artifact_type != 'embedding_vector':
            raise NotFoundError('Embedding not found')
        version = db.session.get(Document, artifact.document_id)
        return {
            'success': True,
            'embedding': cls._serialize_artifact(
                artifact,
                version,
                include_vector=True,
            ),
        }

    @classmethod
    def get_segments(cls, document_id):
        document = db.session.get(Document, document_id)
        if not document:
            raise NotFoundError(f'Document {document_id} not found')
        root = document.get_root_document()
        family_ids = get_document_family_ids(root)
        versions = cls._versions_by_id(family_ids)
        segments = TextSegment.query.filter(
            TextSegment.document_id.in_(family_ids)
        ).all()

        grouped = {}
        for segment in segments:
            version = versions.get(segment.document_id)
            method = cls._segment_method(segment, version)
            grouped.setdefault(method, []).append(
                cls._serialize_segment(segment, version, method)
            )
        methods = []
        for method, method_segments in grouped.items():
            method_segments.sort(
                key=lambda segment: segment.get('segment_number') or 0
            )
            methods.append({
                'method': method,
                'count': len(method_segments),
                'segments': method_segments,
            })
        methods.sort(key=lambda method: method['count'], reverse=True)
        return {
            'success': True,
            'document_id': document_id,
            'source_document_id': root.id,
            'segmentation_methods': methods,
            'total_segments': len(segments),
            'processed_versions_count': len(versions),
        }

    @staticmethod
    def _versions_by_id(family_ids):
        versions = Document.query.filter(Document.id.in_(family_ids)).all()
        return {version.id: version for version in versions}

    @classmethod
    def _serialize_artifact(cls, artifact, version, include_vector=False):
        content = artifact.get_content() or {}
        metadata = artifact.get_metadata() or {}
        model = content.get('model', metadata.get('model', 'Unknown Model'))
        method = metadata.get('method', 'Unknown')
        dimensions = metadata.get('dimensions', len(content.get('vector', [])))
        context = content.get('text', '')
        result = {
            'id': str(artifact.id),
            'document_id': artifact.document_id,
            'version_number': version.version_number if version else None,
            'version_type': version.version_type if version else None,
            'processing_type': cls._processing_type(version),
            'term': (
                'Full Document'
                if artifact.artifact_index == -1
                else f'Segment {artifact.artifact_index}'
            ),
            'period': metadata.get('period_category'),
            'model_name': model,
            'dimensions': dimensions,
            'context_window': context[:500] if context else None,
            'extraction_method': method,
            'metadata': {
                **metadata,
                'source': 'processing_artifact',
                'artifact_id': str(artifact.id),
                'embedding_level': content.get(
                    'embedding_level',
                    metadata.get('embedding_level'),
                ),
                'dimensions': dimensions,
            },
            'created_at': (
                artifact.created_at.isoformat() if artifact.created_at else None
            ),
            'updated_at': None,
            'embedding': None,
        }
        if include_vector:
            result['embedding'] = content.get('vector', [])
        return result

    @classmethod
    def _legacy_embeddings(cls, family_ids, versions):
        jobs = ProcessingJob.query.filter(
            ProcessingJob.document_id.in_(family_ids),
            ProcessingJob.job_type == 'generate_embeddings',
            ProcessingJob.status == 'completed',
        ).order_by(ProcessingJob.completed_at.desc()).all()
        return [
            cls._serialize_legacy_job(job, versions.get(job.document_id))
            for job in jobs
        ]

    @classmethod
    def _legacy_preview(cls, embedding_id):
        try:
            job_id = int(str(embedding_id).replace('job_', '', 1))
        except (TypeError, ValueError):
            raise NotFoundError('Embedding not found')
        job = db.session.get(ProcessingJob, job_id)
        if not job or job.job_type != 'generate_embeddings':
            raise NotFoundError('Embedding not found')
        version = db.session.get(Document, job.document_id)
        result = cls._serialize_legacy_job(job, version)
        result['embedding'] = []
        result['metadata']['note'] = (
            'Vector data not available - this is derived from processing job metadata'
        )
        return result

    @classmethod
    def _serialize_legacy_job(cls, job, version):
        results = job.get_result_data() or {}
        method = results.get('embedding_method', 'Unknown')
        model = results.get('model_used', 'Unknown Model')
        return {
            'id': f'job_{job.id}',
            'document_id': job.document_id,
            'version_number': version.version_number if version else None,
            'version_type': version.version_type if version else None,
            'processing_type': cls._processing_type(version),
            'term': 'Full Document',
            'period': None,
            'model_name': model if model != 'Unknown Model' else method,
            'dimensions': results.get('embedding_dimensions', 0),
            'context_window': (
                f"Document chunks: {results.get('chunk_count', 0)}"
            ),
            'extraction_method': method,
            'metadata': {
                'source': 'processing_job',
                'job_id': job.id,
                'processing_time': results.get('processing_time'),
                'dimensions': results.get('embedding_dimensions', 0),
                'chunk_count': results.get('chunk_count', 0),
            },
            'created_at': (
                job.completed_at.isoformat() if job.completed_at else None
            ),
            'updated_at': job.updated_at.isoformat() if job.updated_at else None,
            'embedding': None,
        }

    @staticmethod
    def _processing_type(version):
        if version and version.processing_metadata:
            return version.processing_metadata.get('type', 'unknown')
        return 'unknown'

    @classmethod
    def _segment_method(cls, segment, version):
        if segment.segmentation_method and segment.segmentation_method != 'manual':
            return segment.segmentation_method
        if segment.processing_method:
            return segment.processing_method
        return cls._processing_type(version)

    @staticmethod
    def _serialize_segment(segment, version, method):
        return {
            'id': segment.id,
            'document_id': segment.document_id,
            'version_number': version.version_number if version else None,
            'version_type': version.version_type if version else None,
            'processing_type': method,
            'segment_type': segment.segment_type,
            'segment_number': segment.segment_number,
            'content': segment.content,
            'word_count': segment.word_count,
            'character_count': segment.character_count,
            'start_position': segment.start_position,
            'end_position': segment.end_position,
            'language': segment.language,
            'created_at': (
                segment.created_at.isoformat() if segment.created_at else None
            ),
            'topics': segment.get_topics(),
            'keywords': segment.get_keywords(),
            'sentiment_score': segment.sentiment_score,
            'complexity_score': segment.complexity_score,
        }
