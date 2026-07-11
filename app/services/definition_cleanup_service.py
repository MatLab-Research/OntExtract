"""Authorized family-wide definition-result deletion workflow."""

from uuid import UUID

from app import db
from app.models.document import Document
from app.models.experiment_document import ExperimentDocument
from app.models.experiment_processing import (
    DocumentProcessingIndex,
    ExperimentDocumentProcessing,
    ProcessingArtifact,
)
from app.models.processing_job import ProcessingJob
from app.models.user import User
from app.services.base_service import (
    NotFoundError,
    PermissionError,
    ServiceError,
)


class DefinitionCleanupService:
    """Delete definition artifacts and jobs for an authorized document family."""

    @classmethod
    def clear(cls, document_uuid, actor_id):
        try:
            document = cls._document(document_uuid)
            root = document.get_root_document()
            actor = db.session.get(User, actor_id)
            if not actor or not actor.can_edit_resource(root):
                raise PermissionError('Permission denied')
            family_ids = {version.id for version in root.get_all_versions()}
            family_ids.add(root.id)
            experiment_document_ids = [
                association.id
                for association in ExperimentDocument.query.filter(
                    ExperimentDocument.document_id.in_(family_ids)
                ).all()
            ]
            processing_ids = []
            if experiment_document_ids:
                processing_ids = [
                    operation.id
                    for operation in ExperimentDocumentProcessing.query.filter(
                        ExperimentDocumentProcessing.experiment_document_id.in_(
                            experiment_document_ids
                        ),
                        ExperimentDocumentProcessing.processing_type == 'definitions',
                    ).all()
                ]
            deleted_artifacts = ProcessingArtifact.query.filter(
                ProcessingArtifact.document_id.in_(family_ids),
                ProcessingArtifact.artifact_type == 'term_definition',
            ).count()
            legacy_jobs = ProcessingJob.query.filter(
                ProcessingJob.document_id.in_(family_ids),
                ProcessingJob.job_type == 'definition_extraction',
            ).count()
            with db.session.begin_nested():
                if processing_ids:
                    DocumentProcessingIndex.query.filter(
                        DocumentProcessingIndex.processing_id.in_(processing_ids)
                    ).delete(synchronize_session=False)
                    ProcessingArtifact.query.filter(
                        ProcessingArtifact.processing_id.in_(processing_ids)
                    ).delete(synchronize_session=False)
                    ExperimentDocumentProcessing.query.filter(
                        ExperimentDocumentProcessing.id.in_(processing_ids)
                    ).delete(synchronize_session=False)
                ProcessingArtifact.query.filter(
                    ProcessingArtifact.document_id.in_(family_ids),
                    ProcessingArtifact.artifact_type == 'term_definition',
                ).delete(synchronize_session=False)
                cls._delete_legacy_jobs(family_ids)
            db.session.commit()
        except (NotFoundError, PermissionError):
            raise
        except Exception as exc:
            if not db.session.is_active:
                db.session.rollback()
            raise ServiceError('Failed to clear definition results') from exc
        jobs_deleted = legacy_jobs + len(processing_ids)
        return {
            'success': True,
            'deleted_count': deleted_artifacts,
            'jobs_deleted': jobs_deleted,
            'message': (
                f'Deleted {deleted_artifacts} definitions and '
                f'{jobs_deleted} processing jobs'
            ),
        }

    @staticmethod
    def _delete_legacy_jobs(family_ids):
        ProcessingJob.query.filter(
            ProcessingJob.document_id.in_(family_ids),
            ProcessingJob.job_type == 'definition_extraction',
        ).delete(synchronize_session=False)

    @staticmethod
    def _document(document_uuid):
        try:
            normalized = UUID(str(document_uuid))
        except (TypeError, ValueError, AttributeError) as exc:
            raise NotFoundError('Document not found') from exc
        document = Document.query.filter_by(uuid=normalized).first()
        if not document:
            raise NotFoundError('Document not found')
        return document