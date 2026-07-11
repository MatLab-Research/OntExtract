"""Authorization, validation, and persistence for document segmentation."""

from app import db
from app.models.document import Document
from app.models.experiment import Experiment, experiment_documents
from app.models.experiment_document import ExperimentDocument
from app.models.processing_job import ProcessingJob
from app.models.text_segment import TextSegment
from app.models.user import User
from app.services.base_service import (
    NotFoundError,
    PermissionError,
    ServiceError,
    ValidationError,
)
from app.services.inheritance_versioning_service import InheritanceVersioningService


class DocumentSegmentationService:
    """Run and remove segmentation while enforcing resource boundaries."""

    METHODS = {'paragraph', 'sentence', 'semantic', 'langextract'}

    def __init__(
        self,
        version_provider,
        traditional_runner,
        langextract_runner,
        workflow_logger=None,
    ):
        self.version_provider = version_provider
        self.traditional_runner = traditional_runner
        self.langextract_runner = langextract_runner
        self.logger = workflow_logger

    def segment(self, document_uuid, data, actor_id):
        document = Document.query.filter_by(uuid=document_uuid).first()
        if not document:
            raise NotFoundError('Document not found')
        actor = db.session.get(User, actor_id)
        values = self._validated_request(data)
        experiment = self._experiment(
            values['experiment_id'],
            document,
            actor,
        )
        if not experiment and (
            not actor or not actor.can_edit_resource(document)
        ):
            raise PermissionError('Permission denied')
        if not document.content:
            raise ValidationError('Document has no content to segment')

        try:
            version = self.version_provider(
                document,
                experiment.id if experiment else None,
                actor,
                values['method'],
                values['chunk_size'],
                values['overlap'],
                self.logger,
            )
            if values['method'] == 'langextract':
                return self.langextract_runner(version, document, actor)

            outcome, status = self.traditional_runner(
                version,
                document,
                actor,
                values['method'],
                values['chunk_size'],
                values['overlap'],
            )
            if not outcome.get('job'):
                return outcome, status
            return self._success_payload(
                outcome,
                version,
                document,
            ), status
        except (NotFoundError, PermissionError, ValidationError):
            raise
        except Exception as exc:
            db.session.rollback()
            raise ServiceError('Document segmentation failed') from exc

    @classmethod
    def delete_segments(cls, document_id, actor_id):
        document = db.session.get(Document, document_id)
        if not document:
            raise NotFoundError('Document not found')
        actor = db.session.get(User, actor_id)
        if not cls._can_edit_document(actor, document):
            raise PermissionError('Permission denied')
        segment_count = TextSegment.query.filter_by(
            document_id=document.id
        ).count()
        if not segment_count:
            raise ValidationError('No segments found to delete')
        try:
            deleted_count = TextSegment.query.filter_by(
                document_id=document.id
            ).delete(synchronize_session=False)
            job = ProcessingJob(
                document_id=document.id,
                job_type='delete_segments',
                status='completed',
                user_id=actor_id,
            )
            job.set_parameters({'segments_deleted': deleted_count})
            job.set_result_data({
                'segments_deleted': deleted_count,
                'deletion_method': 'bulk_delete',
            })
            db.session.add(job)
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            raise ServiceError('Failed to delete document segments') from exc
        return {
            'success': True,
            'job_id': job.id,
            'segments_deleted': deleted_count,
            'message': f'Deleted {deleted_count} text segments',
        }

    @classmethod
    def _validated_request(cls, data):
        if data is None:
            data = {}
        if not isinstance(data, dict):
            raise ValidationError('JSON object is required')
        method = data.get('method', 'paragraph')
        if method not in cls.METHODS:
            raise ValidationError('Unsupported segmentation method')
        chunk_size = cls._integer(data.get('chunk_size', 500), 'chunk_size')
        overlap = cls._integer(data.get('overlap', 50), 'overlap')
        if chunk_size < 50 or chunk_size > 100000:
            raise ValidationError('chunk_size must be between 50 and 100000')
        if overlap < 0 or overlap >= chunk_size:
            raise ValidationError(
                'overlap must be non-negative and smaller than chunk_size'
            )
        experiment_id = data.get('experiment_id')
        if experiment_id not in (None, ''):
            experiment_id = cls._integer(experiment_id, 'experiment_id')
        else:
            experiment_id = None
        return {
            'method': method,
            'chunk_size': chunk_size,
            'overlap': overlap,
            'experiment_id': experiment_id,
        }

    @classmethod
    def _experiment(cls, experiment_id, document, actor):
        if experiment_id is None:
            return None
        experiment = db.session.get(Experiment, experiment_id)
        if not experiment:
            raise NotFoundError('Experiment not found')
        if not actor or not actor.can_edit_resource(experiment):
            raise PermissionError('Permission denied')
        if not cls._family_is_linked(experiment_id, document):
            raise ValidationError('Document is not linked to this experiment')
        return experiment

    @staticmethod
    def _family_is_linked(experiment_id, document):
        root = document.get_root_document()
        family_ids = [root.id]
        family_ids.extend(
            version.id
            for version in Document.query.filter_by(
                source_document_id=root.id
            ).all()
        )
        if document.experiment_id == experiment_id:
            return True
        if ExperimentDocument.query.filter(
            ExperimentDocument.experiment_id == experiment_id,
            ExperimentDocument.document_id.in_(family_ids),
        ).first():
            return True
        return db.session.execute(
            db.select(experiment_documents.c.document_id).where(
                experiment_documents.c.experiment_id == experiment_id,
                experiment_documents.c.document_id.in_(family_ids),
            ).limit(1)
        ).first() is not None

    @staticmethod
    def _can_edit_document(actor, document):
        if actor and actor.can_edit_resource(document):
            return True
        if not actor or document.experiment_id is None:
            return False
        experiment = db.session.get(Experiment, document.experiment_id)
        return bool(experiment and actor.can_edit_resource(experiment))

    @staticmethod
    def _integer(value, field):
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise ValidationError(f'{field} must be an integer') from exc

    @staticmethod
    def _success_payload(outcome, version, original):
        count = outcome['segment_count']
        return {
            'success': True,
            'job_id': outcome['job'].id,
            'segments_created': count,
            'base_document_id': (
                InheritanceVersioningService._get_base_document_id(original)
            ),
            'latest_version_id': version.id,
            'processing_version_id': version.id,
            'processing_version_uuid': str(version.uuid),
            'version_number': version.version_number,
            'message': (
                f'Document segmented into {count} chunks '
                f'(version {version.version_number} with inherited processing)'
            ),
            'redirect_url': f'/input/document/{version.uuid}',
        }
