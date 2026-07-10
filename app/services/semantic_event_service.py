"""Semantic event configuration and provenance workflow."""

import json
import logging
from datetime import datetime
from uuid import uuid4

from app import db
from app.models.document import Document
from app.models.experiment import Experiment
from app.models.experiment_document import ExperimentDocument
from app.models.user import User
from app.services.base_service import NotFoundError, PermissionError, ValidationError
from app.services.local_ontology_service import get_ontology_service
from app.services.provenance_service import ProvenanceService


logger = logging.getLogger(__name__)


class SemanticEventService:
    """Create, update, and remove experiment-scoped semantic events."""

    def __init__(
        self,
        ontology_service=None,
        provenance_service=None,
        clock=None,
        id_factory=None,
        workflow_logger=None,
    ):
        self.ontology_service = ontology_service or get_ontology_service()
        self.provenance_service = provenance_service or ProvenanceService
        self.clock = clock or datetime.utcnow
        self.id_factory = id_factory or uuid4
        self.logger = workflow_logger or logger

    def save(self, experiment_id, data, actor):
        experiment = self._owned_temporal_experiment(experiment_id, actor.id)
        normalized = self._validate_event_data(data)
        config = self._configuration(experiment)
        events = config.get('semantic_events', [])
        if not isinstance(events, list):
            events = []

        supplied_id = normalized.get('id')
        existing_index = next(
            (
                index for index, event in enumerate(events)
                if event.get('id') == supplied_id
            ),
            None,
        ) if supplied_id else None
        if supplied_id and existing_index is None:
            raise NotFoundError(f'Semantic event {supplied_id} not found')
        existing = events[existing_index] if existing_index is not None else None
        event_id = supplied_id or str(self.id_factory())
        related_documents = self._related_documents(
            experiment,
            normalized['related_document_ids'],
        )
        ontology = self._ontology_metadata(normalized['event_type'])
        now = self.clock().isoformat()
        event = {
            'id': event_id,
            'event_type': normalized['event_type'],
            'from_period': normalized['from_period'],
            'to_period': normalized['to_period'],
            'description': normalized['description'],
            'related_documents': related_documents,
            'type_label': (
                ontology['label']
                if ontology else normalized['event_type'].replace('_', ' ').title()
            ),
            'type_uri': ontology['uri'] if ontology else None,
            'definition': ontology['definition'] if ontology else None,
            'citation': ontology['citation'] if ontology else None,
            'example': ontology['example'] if ontology else None,
            'created_by': (existing.get('created_by') or actor.id) if existing else actor.id,
            'created_at': (existing.get('created_at') or now) if existing else now,
            'modified_by': actor.id if existing else None,
            'modified_at': now if existing else None,
        }
        if existing_index is None:
            events.append(event)
        else:
            events[existing_index] = event
        self._commit_events(experiment, config, events)
        self._track_best_effort(
            event['event_type'],
            experiment,
            actor,
            event,
            related_documents,
            is_update=existing is not None,
        )
        return {'success': True, 'semantic_events': events}

    def remove(self, experiment_id, event_id, actor):
        experiment = self._owned_temporal_experiment(experiment_id, actor.id)
        if not event_id:
            raise ValidationError('Missing event_id')
        event_id = str(event_id).strip()
        config = self._configuration(experiment)
        events = config.get('semantic_events', [])
        if not isinstance(events, list):
            events = []
        existing = next(
            (event for event in events if event.get('id') == event_id),
            None,
        )
        if not existing:
            raise NotFoundError(f'Semantic event {event_id} not found')
        remaining = [event for event in events if event.get('id') != event_id]
        self._commit_events(experiment, config, remaining)
        self._track_best_effort(
            existing.get('event_type', 'unknown'),
            experiment,
            actor,
            existing,
            None,
            is_deletion=True,
        )
        return {'success': True, 'semantic_events': remaining}

    @staticmethod
    def _validate_event_data(data):
        if not isinstance(data, dict):
            raise ValidationError('JSON payload required')
        missing = [
            field for field in ('event_type', 'from_period', 'description')
            if data.get(field) in (None, '')
        ]
        if missing:
            raise ValidationError(
                'Missing required fields: event_type, from_period, description'
            )
        event_type = data['event_type']
        description = data['description']
        if not isinstance(event_type, str) or not event_type.strip():
            raise ValidationError('event_type must be a non-empty string')
        if not isinstance(description, str) or not description.strip():
            raise ValidationError('description must be a non-empty string')
        from_period = SemanticEventService._year(
            data['from_period'],
            'from_period',
        )
        to_period = (
            SemanticEventService._year(data['to_period'], 'to_period')
            if data.get('to_period') not in (None, '') else None
        )
        if to_period is not None and to_period < from_period:
            raise ValidationError('to_period must not precede from_period')
        related_ids = data.get('related_document_ids', [])
        if not isinstance(related_ids, list):
            raise ValidationError('related_document_ids must be a list')
        try:
            related_ids = list(dict.fromkeys(int(value) for value in related_ids))
        except (TypeError, ValueError) as exc:
            raise ValidationError(
                'related_document_ids must contain integer IDs'
            ) from exc
        event_id = data.get('id')
        if event_id is not None:
            event_id = str(event_id).strip()
            if not event_id:
                event_id = None
        return {
            'id': event_id,
            'event_type': event_type.strip(),
            'from_period': from_period,
            'to_period': to_period,
            'description': description.strip(),
            'related_document_ids': related_ids,
        }

    @staticmethod
    def _year(value, field):
        try:
            year = int(value)
        except (TypeError, ValueError) as exc:
            raise ValidationError(f'{field} must be a valid year') from exc
        if year < 1 or year > 9999:
            raise ValidationError(f'{field} must be a valid year')
        return year

    def _related_documents(self, experiment, requested_ids):
        allowed_ids = {
            association.document_id
            for association in ExperimentDocument.query.filter_by(
                experiment_id=experiment.id
            ).all()
        }
        allowed_ids.update(document.id for document in experiment.documents)
        allowed_ids.update(reference.id for reference in experiment.references)
        allowed_ids.update(
            document.id
            for document in Document.query.filter_by(
                experiment_id=experiment.id
            ).all()
        )
        invalid = set(requested_ids) - allowed_ids
        if invalid:
            raise ValidationError(
                'Related documents must belong to the experiment'
            )
        documents = {
            document.id: document
            for document in Document.query.filter(Document.id.in_(requested_ids)).all()
        } if requested_ids else {}
        return [
            {
                'id': document_id,
                'uuid': str(documents[document_id].uuid),
                'title': documents[document_id].title or 'Untitled Document',
            }
            for document_id in requested_ids
            if document_id in documents
        ]

    def _ontology_metadata(self, event_type):
        return next(
            (
                item for item in self.ontology_service.get_all_for_dropdown()
                if item['value'] == event_type
            ),
            None,
        )

    @staticmethod
    def _configuration(experiment):
        if isinstance(experiment.configuration, dict):
            return dict(experiment.configuration)
        if not experiment.configuration:
            return {}
        try:
            config = json.loads(experiment.configuration)
            return config if isinstance(config, dict) else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    @staticmethod
    def _commit_events(experiment, config, events):
        config['semantic_events'] = events
        experiment.configuration = json.dumps(config)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

    def _track_best_effort(
        self,
        event_type,
        experiment,
        actor,
        event,
        related_documents,
        **flags,
    ):
        try:
            self.provenance_service.track_semantic_event(
                event_type=event_type,
                experiment=experiment,
                user=actor,
                event_metadata=event,
                related_documents=related_documents,
                **flags,
            )
        except Exception as exc:
            db.session.rollback()
            self.logger.warning(
                f'Failed to track semantic event provenance: {exc}'
            )

    @staticmethod
    def _owned_temporal_experiment(experiment_id, actor_id):
        experiment = (
            Experiment.query.filter_by(id=experiment_id)
            .with_for_update()
            .first()
        )
        if not experiment:
            raise NotFoundError('Experiment not found')
        actor = db.session.get(User, actor_id)
        if not actor or not actor.can_edit_resource(experiment):
            raise PermissionError('Permission denied')
        if experiment.experiment_type != 'temporal_evolution':
            raise ValidationError(
                'Semantic events are only available for temporal evolution experiments'
            )
        return experiment
