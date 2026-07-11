"""Shared owner/admin authorization for experiment pipeline resources."""

from app import db
from app.models.document import Document
from app.models.experiment import Experiment
from app.models.experiment_document import ExperimentDocument
from app.models.experiment_processing import ExperimentDocumentProcessing
from app.models.user import User
from app.services.base_service import NotFoundError, PermissionError


class PipelineAccessService:
    """Resolve pipeline resources only after authorizing their experiment."""

    @classmethod
    def experiment(cls, experiment_id, actor_id):
        experiment = db.session.get(Experiment, experiment_id)
        if not experiment:
            raise NotFoundError(f'Experiment {experiment_id} not found')
        cls._authorize(experiment, actor_id)
        return experiment

    @classmethod
    def experiment_document(cls, experiment_document_id, actor_id):
        experiment_document = db.session.get(
            ExperimentDocument,
            experiment_document_id,
        )
        if not experiment_document:
            raise NotFoundError(
                f'Experiment document {experiment_document_id} not found'
            )
        cls._authorize(experiment_document.experiment, actor_id)
        return experiment_document

    @classmethod
    def document_in_experiment(cls, experiment_id, document_id, actor_id):
        cls.experiment(experiment_id, actor_id)
        experiment_document = ExperimentDocument.query.filter_by(
            experiment_id=experiment_id,
            document_id=document_id,
        ).first()
        if not experiment_document:
            raise NotFoundError(
                f'Document {document_id} not found in experiment {experiment_id}'
            )
        return experiment_document

    @classmethod
    def document_uuid_in_experiment(cls, experiment_id, document_uuid, actor_id):
        cls.experiment(experiment_id, actor_id)
        document = Document.query.filter_by(uuid=document_uuid).first()
        if not document:
            raise NotFoundError('Document not found')
        experiment_document = ExperimentDocument.query.filter_by(
            experiment_id=experiment_id,
            document_id=document.id,
        ).first()
        if not experiment_document:
            raise NotFoundError(
                f'Document {document.id} not found in experiment {experiment_id}'
            )
        return document

    @classmethod
    def processing(cls, processing_id, actor_id):
        processing = db.session.get(ExperimentDocumentProcessing, processing_id)
        if not processing:
            raise NotFoundError(
                f'Processing operation {processing_id} not found'
            )
        cls._authorize(processing.experiment_document.experiment, actor_id)
        return processing

    @staticmethod
    def _authorize(experiment, actor_id):
        actor = db.session.get(User, actor_id)
        if not actor or not actor.can_edit_resource(experiment):
            raise PermissionError('Permission denied')
