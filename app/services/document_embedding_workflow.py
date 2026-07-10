"""Standalone document embedding version and job workflow."""

import re
import time
from types import SimpleNamespace
from uuid import UUID

from app import db
from app.models.document import Document
from app.models.processing_job import ProcessingJob
from app.services.base_service import NotFoundError, ValidationError
from app.services.inheritance_versioning_service import InheritanceVersioningService


class DocumentEmbeddingWorkflow:
    """Coordinate standalone embedding generation and legacy job tracking."""

    AVAILABLE_METHODS = ('local', 'openai', 'claude', 'period_aware')
    MAX_CHUNK_LENGTH = 8000

    def __init__(
        self,
        embedding_service_factory=None,
        period_service_factory=None,
        provenance_service=None,
        workflow_logger=None,
        timer=None,
    ):
        self.embedding_service_factory = (
            embedding_service_factory or self._default_embedding_service
        )
        self.period_service_factory = (
            period_service_factory or self._default_period_service
        )
        self.provenance_service = (
            provenance_service or self._default_provenance_service()
        )
        self.logger = workflow_logger
        self.timer = timer or time.time

    @staticmethod
    def get_document(document_uuid):
        identifier = str(document_uuid)
        if identifier.isdigit():
            document = db.session.get(Document, int(identifier))
            if document:
                return document
        try:
            normalized_uuid = UUID(identifier)
        except (TypeError, ValueError, AttributeError):
            raise NotFoundError(f'Document {document_uuid} not found')
        document = Document.query.filter_by(uuid=normalized_uuid).first()
        if not document:
            raise NotFoundError(f'Document {document_uuid} not found')
        return document

    def generate(self, original_document, data, user):
        data = data or {}
        method = data.get('method', 'local')
        if method not in self.AVAILABLE_METHODS:
            raise ValidationError(
                'Invalid embedding method. Available: '
                + ', '.join(self.AVAILABLE_METHODS)
            )
        if not original_document.content:
            raise ValidationError(
                'Document has no content to generate embeddings from'
            )

        experiment_id = data.get('experiment_id')
        processing_metadata = self._processing_metadata(method, experiment_id, data)
        processing_version = self._processing_version(
            original_document,
            experiment_id,
            user,
            processing_metadata,
        )
        job = self._create_job(
            original_document,
            processing_version,
            method,
            user.id,
        )
        job_id = job.id

        started_at = self.timer()
        try:
            result = self._execute(
                processing_version,
                original_document,
                method,
                data,
                started_at,
            )
            job.status = 'completed'
            job.processing_time = result['processing_time']
            job.set_result_data(result)
            self._track_provenance(
                processing_version,
                user,
                method,
                result,
            )
            db.session.commit()
        except Exception as exc:
            try:
                failed_job = db.session.get(ProcessingJob, job_id)
            except Exception:
                db.session.rollback()
                failed_job = db.session.get(ProcessingJob, job_id)
            if failed_job:
                failed_job.status = 'failed'
                failed_job.set_result_data({
                    'error': str(exc),
                    'embedding_method': method,
                    'processing_time': self.timer() - started_at,
                })
                db.session.commit()
            raise

        base_document_id = InheritanceVersioningService._get_base_document_id(
            original_document
        )
        return {
            'success': True,
            'job_id': job.id,
            'method': method,
            'base_document_id': base_document_id,
            'latest_version_id': processing_version.id,
            'processing_version_id': processing_version.id,
            'version_number': processing_version.version_number,
            'message': (
                f'Embeddings generated using {method} method '
                f'(version {processing_version.version_number} with inherited '
                'processing)'
            ),
            'redirect_url': f'/input/document/{processing_version.id}',
        }

    def _processing_version(
        self,
        original_document,
        experiment_id,
        user,
        processing_metadata,
    ):
        if experiment_id:
            version, created = (
                InheritanceVersioningService.get_or_create_experiment_version(
                    original_document=original_document,
                    experiment_id=experiment_id,
                    user=user,
                )
            )
            if self.logger:
                self.logger.info(
                    'Using experiment version %s for experiment %s (%s)',
                    version.id,
                    experiment_id,
                    'newly created' if created else 'existing',
                )
            return version
        version = InheritanceVersioningService.create_new_version(
            original_document=original_document,
            processing_type='embeddings',
            processing_metadata=processing_metadata,
        )
        if self.logger:
            self.logger.info(
                'Created processed version %s for manual embeddings',
                version.id,
            )
        return version

    @staticmethod
    def _processing_metadata(method, experiment_id, data):
        notes = f'Embeddings processing using {method} method'
        metadata = {
            'embedding_method': method,
            'experiment_id': experiment_id,
        }
        if method == 'period_aware':
            force_period = data.get('force_period')
            model_preference = data.get('model_preference')
            auto_detect = data.get('auto_detect_period', False)
            if force_period:
                notes += f' (forced period: {force_period})'
            if model_preference:
                notes += f' (preference: {model_preference})'
            if auto_detect:
                notes += ' (auto-detect period)'
            metadata.update({
                'force_period': force_period,
                'model_preference': model_preference,
                'auto_detect_period': auto_detect,
            })
        metadata['processing_notes'] = notes
        return metadata

    @staticmethod
    def _create_job(original_document, version, method, user_id):
        job = ProcessingJob(
            document_id=version.id,
            job_type='generate_embeddings',
            status='pending',
            user_id=user_id,
        )
        job.set_parameters({
            'embedding_method': method,
            'original_document_id': original_document.id,
            'version_type': version.version_type or 'processed',
        })
        db.session.add(job)
        db.session.commit()
        return job

    def _execute(self, version, original_document, method, data, started_at):
        period_info = None
        provider_priority = self._provider_priority(method)
        if method == 'period_aware':
            period_info = self._period_selection(version, original_document, data)

        embedding_service = self.embedding_service_factory(provider_priority)
        content = version.content
        chunks = [
            content[index:index + self.MAX_CHUNK_LENGTH]
            for index in range(0, len(content), self.MAX_CHUNK_LENGTH)
        ] or ['']
        embeddings = [
            embedding_service.get_embedding(chunk)
            for chunk in chunks
        ]
        result = {
            'embedding_method': method,
            'embedding_dimensions': embedding_service.get_dimension(),
            'chunk_count': len(chunks),
            'processing_time': self.timer() - started_at,
            'model_used': embedding_service.get_model_name(),
            'total_embeddings': len(embeddings),
            'content_length': len(content),
        }
        if period_info:
            result['period_aware'] = {
                'selected_model': period_info.get('model'),
                'selection_reason': period_info.get('selection_reason'),
                'selection_confidence': period_info.get('selection_confidence'),
                'era': period_info.get('era'),
                'domain': period_info.get('domain'),
                'handles_archaic': period_info.get('handles_archaic', False),
                'detected_year': period_info.get('period_detected'),
            }
        return result

    @staticmethod
    def _provider_priority(method):
        priorities = {
            'local': ['local'],
            'openai': ['openai', 'local'],
            'claude': ['claude', 'local'],
            'period_aware': ['local'],
        }
        return priorities[method]

    def _period_selection(self, version, original_document, data):
        year = (
            original_document.publication_date.year
            if original_document.publication_date else None
        )
        if year is None and data.get('force_period'):
            match = re.search(
                r'\b(1[6-9]\d{2}|20[0-2]\d)\b',
                str(data['force_period']),
            )
            year = int(match.group(1)) if match else None
        info = self.period_service_factory().select_model_for_period(
            year=year,
            domain=data.get('model_preference'),
            text_sample=(
                version.content[:1000]
                if data.get('auto_detect_period', False) else None
            ),
        )
        info['period_detected'] = year
        return info

    def _track_provenance(self, version, user, method, result):
        segments = [
            SimpleNamespace(id=index)
            for index in range(result['chunk_count'])
        ]
        self.provenance_service.track_embedding_generation(
            version,
            user,
            model_name=result['model_used'],
            segments=segments,
            embedding_method=method,
            dimension=result['embedding_dimensions'],
        )

    @staticmethod
    def _default_embedding_service(provider_priority):
        from shared_services.embedding.embedding_service import EmbeddingService

        return EmbeddingService(provider_priority=provider_priority)

    @staticmethod
    def _default_period_service():
        from app.services.period_aware_embedding_service import (
            get_period_aware_embedding_service,
        )

        return get_period_aware_embedding_service()

    @staticmethod
    def _default_provenance_service():
        from app.services.provenance_service import provenance_service

        return provenance_service
