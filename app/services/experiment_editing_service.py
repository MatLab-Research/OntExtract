"""Authorized experiment editing read and write workflows."""

import json
from datetime import datetime

from sqlalchemy import or_

from app import db
from app.models.document import Document
from app.models.experiment import Experiment
from app.models.experiment_document import ExperimentDocument
from app.models.term import Term
from app.models.user import User
from app.services.base_service import (
    NotFoundError,
    PermissionError,
    ServiceError,
    ValidationError,
)
from app.services.experiment_resource_service import ExperimentResourceService


class ExperimentEditingService:
    """Edit experiment metadata and safely extend resource associations."""

    @classmethod
    def get_context(cls, experiment_id, actor_id):
        experiment, actor = cls._editable_experiment(experiment_id, actor_id)
        documents, references, terms = cls._options(actor)
        selected_documents = cls._document_roots(experiment)
        selected_references = list(experiment.references)
        return {
            'experiment': experiment,
            'documents': documents,
            'references': references,
            'terms': terms,
            'selected_document_uuids': {
                str(document.uuid) for document in selected_documents
            },
            'selected_reference_uuids': {
                str(reference.uuid) for reference in selected_references
            },
            'selected_term_id': (
                str(experiment.term_id) if experiment.term_id else None
            ),
            'configuration': cls._configuration(experiment),
        }

    @classmethod
    def update(cls, experiment_id, data, actor_id):
        experiment, actor = cls._editable_experiment(experiment_id, actor_id)
        if data.experiment_type and data.experiment_type != experiment.experiment_type:
            raise ValidationError('Experiment type cannot be changed')

        fields = data.model_fields_set
        document_selection = bool(
            {'document_uuids', 'document_ids'} & fields
        )
        reference_selection = bool(
            {'reference_uuids', 'reference_ids'} & fields
        )
        documents = None
        references = None
        term = None
        if document_selection:
            documents = ExperimentResourceService.resolve_documents(
                data.document_uuids,
                data.document_ids,
                'document',
                actor,
            )
            existing_ids = {
                document.id for document in cls._document_roots(experiment)
            }
            selected_ids = {document.id for document in documents}
            if not existing_ids.issubset(selected_ids):
                raise ValidationError(
                    'Existing documents cannot be removed in-place; duplicate '
                    'the experiment to change its document set'
                )
        if reference_selection:
            references = ExperimentResourceService.resolve_documents(
                data.reference_uuids,
                data.reference_ids,
                'reference',
                actor,
            )
        if 'term_id' in fields:
            term = ExperimentResourceService.resolve_term(data.term_id, actor)
            if experiment.experiment_type == 'temporal_evolution' and not term:
                raise ValidationError(
                    'A focus term is required for temporal evolution experiments'
                )

        try:
            with db.session.begin_nested():
                if data.name is not None:
                    experiment.name = data.name
                if data.description is not None:
                    experiment.description = data.description
                if data.configuration is not None:
                    configuration = cls._configuration(experiment)
                    configuration.update(data.configuration)
                    experiment.configuration = json.dumps(configuration)
                if 'term_id' in fields:
                    experiment.term_id = term.id if term else None
                if documents is not None:
                    existing_ids = {
                        document.id for document in cls._document_roots(experiment)
                    }
                    additions = [
                        document for document in documents
                        if document.id not in existing_ids
                    ]
                    if additions:
                        ExperimentResourceService.add_documents(
                            experiment,
                            additions,
                            actor,
                        )
                if references is not None:
                    ExperimentResourceService.replace_references(
                        experiment,
                        references,
                    )
                experiment.updated_at = datetime.utcnow()
            db.session.commit()
        except (NotFoundError, PermissionError, ValidationError):
            raise
        except Exception as exc:
            raise ServiceError('Failed to update experiment') from exc
        return experiment

    @staticmethod
    def _editable_experiment(experiment_id, actor_id):
        experiment = db.session.get(Experiment, experiment_id)
        if not experiment:
            raise NotFoundError(f'Experiment {experiment_id} not found')
        actor = db.session.get(User, actor_id)
        if not actor or not actor.can_edit_resource(experiment):
            raise PermissionError('Permission denied')
        if experiment.status not in {'draft', 'error'}:
            raise ValidationError(
                'Only draft or error experiments can be edited'
            )
        return experiment, actor

    @staticmethod
    def _options(actor):
        documents = Document.query.filter_by(
            document_type='document',
            version_type='original',
        )
        references = Document.query.filter_by(
            document_type='reference',
            version_type='original',
        )
        terms = Term.query
        if not actor.is_admin:
            documents = documents.filter_by(user_id=actor.id)
            references = references.filter_by(user_id=actor.id)
            terms = terms.filter(or_(
                Term.created_by == actor.id,
                Term.created_by.is_(None),
            ))
        return (
            documents.order_by(Document.created_at.desc()).all(),
            references.order_by(Document.created_at.desc()).all(),
            terms.order_by(Term.term_text).all(),
        )

    @staticmethod
    def _document_roots(experiment):
        associations = ExperimentDocument.query.filter_by(
            experiment_id=experiment.id
        ).all()
        documents = [association.document for association in associations]
        documents.extend(list(experiment.documents))
        roots = {}
        for document in documents:
            root = document.get_root_document()
            roots[root.id] = root
        return list(roots.values())

    @staticmethod
    def _configuration(experiment):
        if isinstance(experiment.configuration, dict):
            return dict(experiment.configuration)
        if not experiment.configuration:
            return {}
        try:
            value = json.loads(experiment.configuration)
            return value if isinstance(value, dict) else {}
        except (json.JSONDecodeError, TypeError):
            return {}
