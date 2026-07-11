"""Authorized read models for provenance timelines, graphs, and lineage."""

from uuid import UUID

from sqlalchemy import or_

from app import db
from app.models.document import Document
from app.models.experiment import Experiment
from app.models.prov_o_models import ProvAgent, ProvEntity
from app.models.term import Term
from app.models.user import User
from app.services.base_service import (
    NotFoundError,
    PermissionError,
    ValidationError,
)
from app.services.provenance_service import provenance_service


class ProvenanceVisualizationService:
    """Validate provenance filters and constrain data to the current actor."""

    ACTIVITY_TYPES = [
        'term_creation',
        'term_update',
        'document_upload',
        'text_extraction',
        'metadata_extraction_pdf',
        'metadata_extraction',
        'document_save',
        'metadata_update',
        'metadata_field_update',
        'document_segmentation',
        'embedding_generation',
        'entity_extraction',
        'temporal_extraction',
        'definition_extraction',
        'experiment_creation',
        'experiment_document_processing',
        'tool_execution',
        'orchestration_run',
        'semantic_event_creation',
        'semantic_event_update',
        'semantic_event_deletion',
    ]

    @classmethod
    def timeline_context(cls, args, actor_id):
        actor = cls._actor(actor_id)
        filters = cls._filters(args, actor)
        include_deleted = cls._boolean(args.get('include_deleted'))
        if include_deleted and not actor.is_admin:
            raise PermissionError('Permission denied')
        document_ids = (
            [item.id for item in filters['document'].get_all_versions()]
            if filters['document'] else None
        )
        timeline = provenance_service.get_timeline(
            experiment_id=cls._id(filters['experiment']),
            document_ids=document_ids,
            activity_type=filters['activity_type'],
            term_id=cls._id(filters['term']),
            limit=filters['limit'],
            include_invalidated=include_deleted,
            user_id=cls._user_scope(actor, filters),
        )
        experiments, documents, terms = cls._filter_options(actor)
        return {
            'timeline': timeline,
            'experiments': experiments,
            'documents': documents,
            'terms': terms,
            'activity_types': cls.ACTIVITY_TYPES,
            'selected_experiment_id': cls._id(filters['experiment']),
            'selected_document_id': cls._id(filters['document']),
            'selected_activity_type': filters['activity_type'],
            'selected_term_id': (
                str(filters['term'].id) if filters['term'] else None
            ),
            'version_count': len(document_ids) if document_ids else 0,
            'include_deleted': include_deleted,
            'limit': filters['limit'],
        }

    @classmethod
    def experiment_context(cls, experiment_id, actor_id):
        actor = cls._actor(actor_id)
        experiment = cls._experiment(experiment_id, actor)
        return {
            'experiment': experiment,
            'timeline': provenance_service.get_timeline(
                experiment_id=experiment.id,
                limit=100,
            ),
        }

    @classmethod
    def graph_context(cls, args, actor_id):
        actor = cls._actor(actor_id)
        filters = cls._filters(args, actor)
        context = {}
        if filters['document']:
            document = filters['document']
            context.update({
                'document': document.title or f'Document {document.id}',
                'document_id': document.id,
                'document_uuid': str(document.uuid),
            })
        if filters['experiment']:
            context.update({
                'experiment': filters['experiment'].name,
                'experiment_id': filters['experiment'].id,
            })
        if filters['term']:
            context.update({
                'term': filters['term'].term_text,
                'term_id': str(filters['term'].id),
            })
        return {
            'filter_context': context,
            'experiment_id': cls._id(filters['experiment']),
            'document_id': cls._id(filters['document']),
            'term_id': str(filters['term'].id) if filters['term'] else None,
        }

    @classmethod
    def timeline_data(cls, args, actor_id):
        actor = cls._actor(actor_id)
        filters = cls._filters(args, actor)
        timeline = provenance_service.get_timeline(
            experiment_id=cls._id(filters['experiment']),
            document_ids=(
                [item.id for item in filters['document'].get_all_versions()]
                if filters['document'] else None
            ),
            activity_type=filters['activity_type'],
            term_id=cls._id(filters['term']),
            limit=filters['limit'],
            user_id=cls._user_scope(actor, filters),
        )
        return {'success': True, 'timeline': timeline, 'count': len(timeline)}

    @classmethod
    def graph_data(cls, args, actor_id):
        actor = cls._actor(actor_id)
        filters = cls._filters(args, actor)
        return {
            'success': True,
            **provenance_service.get_graph_data(
                experiment_id=cls._id(filters['experiment']),
                document_id=cls._id(filters['document']),
                term_id=cls._id(filters['term']),
                limit=filters['limit'],
                user_id=cls._user_scope(actor, filters),
            ),
        }

    @classmethod
    def lineage_context(cls, entity_id, actor_id):
        actor = cls._actor(actor_id)
        entity_uuid = cls._uuid(entity_id, 'Invalid entity ID')
        entity = db.session.get(ProvEntity, entity_uuid)
        if not entity:
            raise NotFoundError('Entity not found')
        if not actor.is_admin and not cls._can_view_entity(entity, actor):
            raise PermissionError('Permission denied')
        lineage = provenance_service.get_entity_lineage(entity_uuid)
        if not actor.is_admin:
            lineage = [
                item for item in lineage
                if cls._can_view_entity(item, actor)
            ]
        return {
            'entity': entity,
            'lineage': lineage,
        }

    @classmethod
    def _filters(cls, args, actor):
        experiment_id = cls._optional_int(args.get('experiment_id'))
        document_id = cls._optional_int(args.get('document_id'))
        document_uuid = args.get('document_uuid')
        term_id = args.get('term_id')
        experiment = (
            cls._experiment(experiment_id, actor) if experiment_id else None
        )
        document = None
        if document_id:
            document = cls._document(document_id, actor)
        elif document_uuid:
            normalized = cls._uuid(document_uuid, 'Invalid document UUID')
            document = Document.query.filter_by(uuid=normalized).first()
            if not document:
                raise NotFoundError('Document not found')
            cls._require_edit(actor, document.get_root_document())
            document = document.get_root_document()
        term = cls._term(term_id, actor) if term_id else None
        activity_type = (args.get('activity_type') or '').strip() or None
        if activity_type and activity_type not in cls.ACTIVITY_TYPES:
            raise ValidationError('Invalid activity type')
        return {
            'experiment': experiment,
            'document': document,
            'term': term,
            'activity_type': activity_type,
            'limit': cls._limit(args.get('limit', 50)),
        }

    @staticmethod
    def _actor(actor_id):
        actor = db.session.get(User, actor_id)
        if not actor:
            raise PermissionError('Permission denied')
        return actor

    @classmethod
    def _experiment(cls, experiment_id, actor):
        experiment = db.session.get(Experiment, experiment_id)
        if not experiment:
            raise NotFoundError('Experiment not found')
        cls._require_edit(actor, experiment)
        return experiment

    @classmethod
    def _document(cls, document_id, actor):
        document = db.session.get(Document, document_id)
        if not document:
            raise NotFoundError('Document not found')
        root = document.get_root_document()
        cls._require_edit(actor, root)
        return root

    @staticmethod
    def _term(term_id, actor):
        term_uuid = ProvenanceVisualizationService._uuid(
            term_id,
            'Invalid term ID',
        )
        term = db.session.get(Term, term_uuid)
        if not term:
            raise NotFoundError('Term not found')
        if (
            not actor.is_admin
            and term.created_by is not None
            and term.created_by != actor.id
        ):
            raise PermissionError('Permission denied')
        return term

    @staticmethod
    def _filter_options(actor):
        experiments = Experiment.query
        documents = Document.query.filter_by(version_type='original')
        terms = Term.query
        if not actor.is_admin:
            experiments = experiments.filter_by(user_id=actor.id)
            documents = documents.filter_by(user_id=actor.id)
            terms = terms.filter(or_(
                Term.created_by == actor.id,
                Term.created_by.is_(None),
            ))
        return (
            experiments.order_by(Experiment.created_at.desc()).all(),
            documents.order_by(Document.created_at.desc()).all(),
            terms.order_by(Term.term_text).all(),
        )

    @staticmethod
    def _user_scope(actor, filters):
        if actor.is_admin:
            return None
        if any(filters[key] for key in ('experiment', 'document', 'term')):
            return None
        return actor.id

    @classmethod
    def _can_view_entity(cls, entity, actor):
        activity = entity.generating_activity
        if not activity:
            return False
        agent = db.session.get(ProvAgent, activity.wasassociatedwith)
        if agent and agent.foaf_name == f'researcher:{actor.id}':
            return True
        parameters = activity.activity_parameters or {}
        try:
            if parameters.get('experiment_id'):
                cls._experiment(int(parameters['experiment_id']), actor)
                return True
            if parameters.get('document_id'):
                cls._document(int(parameters['document_id']), actor)
                return True
            if parameters.get('term_id'):
                cls._term(parameters['term_id'], actor)
                return True
        except (NotFoundError, PermissionError, ValidationError, ValueError):
            return False
        return False

    @staticmethod
    def _require_edit(actor, resource):
        if not actor.can_edit_resource(resource):
            raise PermissionError('Permission denied')

    @staticmethod
    def _optional_int(value):
        if value in (None, ''):
            return None
        try:
            value = int(value)
        except (TypeError, ValueError) as exc:
            raise ValidationError('Invalid integer filter') from exc
        if value <= 0:
            raise ValidationError('Invalid integer filter')
        return value

    @staticmethod
    def _limit(value):
        try:
            value = int(value)
        except (TypeError, ValueError) as exc:
            raise ValidationError('limit must be an integer') from exc
        return max(1, min(value, 200))

    @staticmethod
    def _uuid(value, message):
        try:
            return value if isinstance(value, UUID) else UUID(str(value))
        except (TypeError, ValueError, AttributeError) as exc:
            raise ValidationError(message) from exc

    @staticmethod
    def _boolean(value):
        return str(value or '').casefold() in {'true', '1', 'yes', 'on'}

    @staticmethod
    def _id(resource):
        return resource.id if resource else None
