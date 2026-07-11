"""Embedding metadata, samples, verification, and job diagnostics."""

from app import db
from app.models.document import Document
from app.models.experiment_processing import ProcessingArtifact
from app.models.processing_job import ProcessingJob
from app.services.base_service import NotFoundError, PermissionError
from app.services.processing_results import get_document_family_ids


class EmbeddingDiagnosticsService:
    """Build honest embedding diagnostics across a document family."""

    @classmethod
    def get_document_info(cls, document_id):
        document, family_ids = cls._document_family(document_id)
        artifacts = cls._artifacts(family_ids)
        jobs = cls._jobs(family_ids)
        if artifacts:
            latest = artifacts[0]
            latest_run = cls._same_run(artifacts, latest)
            content = latest.get_content() or {}
            metadata = latest.get_metadata() or {}
            dimensions = metadata.get('dimensions', len(content.get('vector', [])))
            chunk_count = len(latest_run)
            return {
                'success': True,
                'has_embeddings': True,
                'document_id': document_id,
                'document_title': document.title,
                'job_id': None,
                'method': metadata.get('method', 'unknown'),
                'dimensions': dimensions,
                'chunk_count': chunk_count,
                'estimated_size_mb': cls._estimated_size(dimensions, chunk_count),
                'processing_time': None,
                'created_at': (
                    latest.created_at.isoformat() if latest.created_at else None
                ),
                'parameters': metadata,
                'source': 'processing_artifact',
            }
        successful = next((job for job in jobs if job.status == 'completed'), None)
        if not successful:
            return {
                'success': False,
                'error': 'No embeddings found for this document',
                'has_embeddings': False,
            }
        results = successful.get_result_data() or {}
        dimensions = results.get('embedding_dimensions', 0)
        chunk_count = results.get('chunk_count', 0)
        return {
            'success': True,
            'has_embeddings': True,
            'document_id': document_id,
            'document_title': document.title,
            'job_id': successful.id,
            'method': results.get('embedding_method', 'unknown'),
            'dimensions': dimensions,
            'chunk_count': chunk_count,
            'estimated_size_mb': cls._estimated_size(dimensions, chunk_count),
            'processing_time': results.get('processing_time'),
            'created_at': (
                successful.completed_at.isoformat()
                if successful.completed_at else None
            ),
            'parameters': successful.get_parameters() or {},
            'source': 'processing_job',
        }

    @classmethod
    def get_sample(cls, document_id):
        document, family_ids = cls._document_family(document_id)
        versions = {
            version.id: version
            for version in Document.query.filter(Document.id.in_(family_ids)).all()
        }
        artifacts = cls._artifacts(family_ids)
        samples = cls._artifact_samples(artifacts, versions)
        note = 'Showing stored embedding vector samples.'
        if not samples:
            samples = cls._legacy_samples(cls._jobs(family_ids), versions)
            note = (
                'Vector data is unavailable for legacy processing jobs; '
                'metadata and text previews are shown without fabricated values.'
            )
        if not samples:
            return {
                'success': False,
                'error': (
                    'No embeddings found for this document or its processed versions'
                ),
            }
        latest = samples[0]
        return {
            'success': True,
            'document_id': document_id,
            'source_document_id': document.get_root_document().id,
            'processed_versions': samples,
            'note': note,
            # Compatibility with current embedding modal callers.
            'method': latest['method'],
            'total_dimensions': latest['total_dimensions'],
            'total_chunks': latest['total_chunks'],
            'sample_chunks': latest['sample_chunks'],
        }

    @classmethod
    def verify(cls, document_id):
        _, family_ids = cls._document_family(document_id)
        artifacts = cls._artifacts(family_ids)
        jobs = cls._jobs(family_ids)
        successful = [job for job in jobs if job.status == 'completed']
        failed = [job for job in jobs if job.status == 'failed']
        result = {
            'success': True,
            'has_embeddings': bool(artifacts or successful),
            'total_attempts': len(jobs),
            'successful_attempts': len(successful),
            'failed_attempts': len(failed),
            'artifact_count': len(artifacts),
        }
        if not artifacts and not jobs:
            result['message'] = 'No embedding jobs or artifacts found for this document'
            return result
        if artifacts:
            latest = artifacts[0]
            latest_run = cls._same_run(artifacts, latest)
            content = latest.get_content() or {}
            metadata = latest.get_metadata() or {}
            dimensions = metadata.get('dimensions', len(content.get('vector', [])))
            result['latest_embedding'] = {
                'job_id': None,
                'method': metadata.get('method', 'unknown'),
                'dimensions': dimensions,
                'chunks': len(latest_run),
                'completed_at': (
                    latest.created_at.isoformat() if latest.created_at else None
                ),
                'processing_time': 0,
                'estimated_size_mb': cls._estimated_size(
                    dimensions,
                    len(latest_run),
                ),
                'source': 'processing_artifact',
            }
        elif successful:
            latest = successful[0]
            job_result = latest.get_result_data() or {}
            dimensions = job_result.get('embedding_dimensions', 0)
            chunks = job_result.get('chunk_count', 0)
            result['latest_embedding'] = {
                'job_id': latest.id,
                'method': job_result.get('embedding_method', 'unknown'),
                'dimensions': dimensions,
                'chunks': chunks,
                'completed_at': (
                    latest.completed_at.isoformat() if latest.completed_at else None
                ),
                'processing_time': job_result.get('processing_time', 0),
                'estimated_size_mb': cls._estimated_size(dimensions, chunks),
                'source': 'processing_job',
            }
        return result

    @staticmethod
    def get_job_details(job_id, user_id):
        job = db.session.get(ProcessingJob, job_id)
        if not job:
            raise NotFoundError(f'Processing job {job_id} not found')
        if job.user_id != user_id:
            raise PermissionError('Access denied')
        return {
            'success': True,
            'job_details': {
                'job_info': job.to_dict(),
                'parameters': job.get_parameters(),
                'results': job.get_result_data(),
                'error_details': (
                    job.get_error_details() if job.status == 'failed' else None
                ),
            },
        }

    @staticmethod
    def _document_family(document_id):
        document = db.session.get(Document, document_id)
        if not document:
            raise NotFoundError(f'Document {document_id} not found')
        return document, get_document_family_ids(document)

    @staticmethod
    def _artifacts(family_ids):
        return ProcessingArtifact.query.filter(
            ProcessingArtifact.document_id.in_(family_ids),
            ProcessingArtifact.artifact_type == 'embedding_vector',
        ).order_by(ProcessingArtifact.created_at.desc()).all()

    @staticmethod
    def _jobs(family_ids):
        jobs = ProcessingJob.query.filter(
            ProcessingJob.document_id.in_(family_ids),
            ProcessingJob.job_type == 'generate_embeddings',
        ).all()
        family_set = set(family_ids)
        for job in ProcessingJob.query.filter(
            ProcessingJob.document_id.notin_(family_ids),
            ProcessingJob.job_type == 'generate_embeddings',
        ).all():
            if job.get_parameters().get('original_document_id') in family_set:
                jobs.append(job)
        jobs.sort(
            key=lambda job: (
                job.completed_at or job.created_at,
                job.id,
            ),
            reverse=True,
        )
        return jobs

    @classmethod
    def _artifact_samples(cls, artifacts, versions):
        grouped = {}
        for artifact in artifacts:
            grouped.setdefault(artifact.document_id, []).append(artifact)
        samples = []
        for document_id, document_artifacts in grouped.items():
            document_artifacts = cls._same_run(
                document_artifacts,
                document_artifacts[0],
            )
            version = versions.get(document_id)
            chunks = []
            dimensions = 0
            method = 'unknown'
            for index, artifact in enumerate(document_artifacts[:3]):
                content = artifact.get_content() or {}
                metadata = artifact.get_metadata() or {}
                vector = content.get('vector', []) or []
                dimensions = metadata.get('dimensions', len(vector))
                method = metadata.get('method', method)
                text = content.get('text', '')
                chunks.append({
                    'chunk_id': artifact.artifact_index if artifact.artifact_index is not None else index,
                    'text_preview': text[:150] + ('...' if len(text) > 150 else ''),
                    'vector_sample': vector[:10],
                    'vector_length': dimensions,
                    'word_count': len(text.split()),
                    'source': 'processing_artifact',
                })
            samples.append({
                'version_id': document_id,
                'version_number': version.version_number if version else None,
                'processing_type': cls._processing_type(version),
                'method': method,
                'total_dimensions': dimensions,
                'total_chunks': len(document_artifacts),
                'sample_chunks': chunks,
                'source': 'processing_artifact',
            })
        return samples

    @staticmethod
    def _same_run(artifacts, latest):
        return [
            artifact
            for artifact in artifacts
            if artifact.processing_id == latest.processing_id
        ]

    @classmethod
    def _legacy_samples(cls, jobs, versions):
        samples = []
        seen_documents = set()
        for job in jobs:
            if job.status != 'completed' or job.document_id in seen_documents:
                continue
            seen_documents.add(job.document_id)
            version = versions.get(job.document_id) or db.session.get(
                Document,
                job.document_id,
            )
            result = job.get_result_data() or {}
            dimensions = result.get('embedding_dimensions', 0)
            chunk_count = result.get('chunk_count', 0)
            words = version.content.split() if version and version.content else []
            chunks = []
            for index in range(min(3, chunk_count)):
                start = index * 100
                chunk_words = words[start:start + 100]
                text = ' '.join(chunk_words)
                chunks.append({
                    'chunk_id': index,
                    'text_preview': text[:150] + ('...' if len(text) > 150 else ''),
                    'vector_sample': [],
                    'vector_length': dimensions,
                    'word_count': len(chunk_words),
                    'source': 'processing_job',
                })
            samples.append({
                'version_id': job.document_id,
                'version_number': version.version_number if version else None,
                'processing_type': cls._processing_type(version),
                'method': result.get('embedding_method', 'unknown'),
                'total_dimensions': dimensions,
                'total_chunks': chunk_count,
                'sample_chunks': chunks,
                'source': 'processing_job',
            })
        return samples

    @staticmethod
    def _processing_type(version):
        if version and version.processing_metadata:
            return version.processing_metadata.get('type', 'unknown')
        return 'unknown'

    @staticmethod
    def _estimated_size(dimensions, chunks):
        return round((dimensions * chunks * 4) / (1024 * 1024), 2)
