"""Asynchronous cleanup jobs and reviewed cleaned-version persistence."""

import logging
import threading
from uuid import UUID

from app import db
from app.models.document import Document
from app.models.experiment_document import ExperimentDocument
from app.models.processing_job import ProcessingJob
from app.services.base_service import NotFoundError, ValidationError
from app.services.inheritance_versioning_service import InheritanceVersioningService
from app.services.text_cleanup_service import TextCleanupService


logger = logging.getLogger(__name__)


class DocumentCleanupWorkflow:
    """Coordinate text cleanup jobs and reviewed document versions."""

    def __init__(self, cleanup_service_factory=TextCleanupService, thread_factory=None):
        self.cleanup_service_factory = cleanup_service_factory
        self.thread_factory = thread_factory or threading.Thread

    @staticmethod
    def get_document(document_uuid):
        try:
            normalized_uuid = UUID(str(document_uuid))
        except (TypeError, ValueError, AttributeError):
            raise NotFoundError(f'Document {document_uuid} not found')
        document = Document.query.filter_by(uuid=normalized_uuid).first()
        if not document:
            raise NotFoundError(f'Document {document_uuid} not found')
        return document

    def start_cleanup(self, document, user_id, flask_app):
        if not document.content:
            raise ValidationError('Document has no content to clean')

        content = document.content
        job = ProcessingJob(
            document_id=document.id,
            job_type='clean_text',
            status='running',
            user_id=user_id,
        )
        job.set_parameters({
            'original_length': len(content),
            'current_chunk': 0,
            'total_chunks': 1,
            'progress_message': 'Starting text cleanup...',
        })
        db.session.add(job)
        db.session.commit()

        thread = self.thread_factory(
            target=self._run_cleanup_job,
            args=(flask_app, job.id, content),
            daemon=True,
        )
        thread.start()
        return {
            'success': True,
            'job_id': job.id,
            'status': 'running',
            'message': 'Text cleanup started. Poll for progress updates.',
        }

    def _run_cleanup_job(self, flask_app, job_id, document_content):
        with flask_app.app_context():
            try:
                job = db.session.get(ProcessingJob, job_id)
                if not job:
                    raise NotFoundError(f'Processing job {job_id} not found')

                def update_progress(current_chunk, total_chunks):
                    refreshed_job = db.session.get(ProcessingJob, job_id)
                    refreshed_job.set_parameters({
                        'original_length': len(document_content),
                        'current_chunk': current_chunk,
                        'total_chunks': total_chunks,
                        'progress_message': (
                            f'Processing chunk {current_chunk} of {total_chunks}...'
                        ),
                    })
                    db.session.commit()

                cleaned_text, metadata = self.cleanup_service_factory().clean_text(
                    document_content,
                    progress_callback=update_progress,
                )
                chunks = metadata.get('chunks_processed', 1)
                job.status = 'completed'
                job.completed_at = db.func.now()
                job.set_parameters({
                    'original_length': len(document_content),
                    'cleaned_length': len(cleaned_text),
                    'model': metadata.get('model'),
                    'input_tokens': metadata.get('input_tokens'),
                    'output_tokens': metadata.get('output_tokens'),
                    'chunks_processed': chunks,
                    'current_chunk': chunks,
                    'total_chunks': chunks,
                    'progress_message': 'Cleanup complete',
                })
                job.set_result_data({
                    'original_text': document_content,
                    'cleaned_text': cleaned_text,
                    'metadata': metadata,
                })
                db.session.commit()
            except Exception as exc:
                db.session.rollback()
                failed_job = db.session.get(ProcessingJob, job_id)
                if failed_job:
                    failed_job.status = 'failed'
                    failed_job.completed_at = db.func.now()
                    failed_job.set_parameters({
                        'error': str(exc),
                        'original_length': len(document_content),
                        'progress_message': f'Error: {exc}',
                    })
                    db.session.commit()
                logger.error(f'Background text cleanup failed: {exc}', exc_info=True)

    @classmethod
    def save_reviewed_cleanup(cls, document, data, user_id):
        if not data:
            raise ValidationError('No data provided')
        cleaned_content = data.get('cleaned_content')
        if not cleaned_content:
            raise ValidationError('No cleaned content provided')

        accepted = data.get('changes_accepted', 0)
        rejected = data.get('changes_rejected', 0)
        original_length = data.get('original_length', 0)
        cleaned_length = data.get('cleaned_length', len(cleaned_content))
        metadata = {
            'changes_accepted': accepted,
            'changes_rejected': rejected,
            'cleanup_method': 'llm_claude',
            'original_length': original_length,
            'cleaned_length': cleaned_length,
        }

        cleaned_version = InheritanceVersioningService.create_new_version(
            original_document=document,
            processing_type='text_cleanup',
            processing_metadata=metadata,
        )
        cleaned_version.version_type = 'cleaned'
        cleaned_version.content = cleaned_content
        cleaned_version.content_preview = cleaned_content[:500]
        cleaned_version.character_count = len(cleaned_content)
        cleaned_version.word_count = len(cleaned_content.split())
        db.session.flush()

        original_job = ProcessingJob.query.filter_by(
            document_id=document.id,
            job_type='clean_text',
            status='completed',
        ).order_by(ProcessingJob.created_at.desc()).first()
        cleanup_job = cls._create_reviewed_job(
            cleaned_version,
            original_job,
            user_id,
            original_length,
            cleaned_length,
            accepted,
            rejected,
        )
        cls._propagate_to_experiments(cleaned_version)
        db.session.commit()
        return {
            'success': True,
            'version_uuid': str(cleaned_version.uuid),
            'message': (
                f'Saved cleaned text ({accepted} changes accepted, '
                f'{rejected} rejected)'
            ),
            'document_id': cleaned_version.id,
            'job_id': cleanup_job.id,
        }

    @staticmethod
    def _create_reviewed_job(
        cleaned_version,
        original_job,
        user_id,
        original_length,
        cleaned_length,
        accepted,
        rejected,
    ):
        job = ProcessingJob(
            document_id=cleaned_version.id,
            job_type='clean_text',
            status='completed',
            user_id=user_id,
            completed_at=db.func.now(),
        )
        original_parameters = original_job.get_parameters() if original_job else {}
        parameters = {
            'original_length': original_length,
            'cleaned_length': cleaned_length,
            'changes_accepted': accepted,
            'changes_rejected': rejected,
            'model': original_parameters.get(
                'model',
                'claude-sonnet-4-5-20250929',
            ),
            'cleanup_method': 'llm_claude_reviewed',
        }
        if original_job:
            parameters.update({
                'input_tokens': original_parameters.get('input_tokens', 0),
                'output_tokens': original_parameters.get('output_tokens', 0),
                'chunks_processed': original_parameters.get('chunks_processed', 1),
            })
        job.set_parameters(parameters)
        db.session.add(job)
        db.session.flush()
        return job

    @staticmethod
    def _propagate_to_experiments(cleaned_version):
        root = cleaned_version.get_root_document()
        family_ids = [version.id for version in root.get_all_versions()]
        experiment_ids = {
            experiment_document.experiment_id
            for experiment_document in ExperimentDocument.query.filter(
                ExperimentDocument.document_id.in_(family_ids)
            ).all()
        }
        for experiment_id in experiment_ids:
            existing = ExperimentDocument.query.filter_by(
                experiment_id=experiment_id,
                document_id=cleaned_version.id,
            ).first()
            if not existing:
                db.session.add(ExperimentDocument(
                    experiment_id=experiment_id,
                    document_id=cleaned_version.id,
                ))
                db.session.flush()
                logger.info(
                    f'Added cleaned version {cleaned_version.id} to experiment '
                    f'{experiment_id} (no processing records)'
                )
