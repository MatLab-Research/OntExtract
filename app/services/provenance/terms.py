"""PROV-O term creation and update tracking."""

from datetime import datetime
from typing import Any, Dict

from app import db
from app.models.prov_o_models import ProvActivity, ProvEntity
from .serialization import _serialize_value


class ProvenanceTermTrackingMixin:
    @classmethod
    def track_term_creation(cls, term, user) -> tuple[ProvActivity, ProvEntity]:
        """
        Track term creation with PROV-O.

        Args:
            term: Term model instance
            user: User model instance

        Returns:
            (activity, entity) tuple
        """
        # Get/create user agent
        agent = cls.get_or_create_user_agent(user.id, user.username)

        # Create activity
        activity = ProvActivity(
            activity_type='term_creation',
            startedattime=term.created_at or datetime.utcnow(),
            endedattime=term.created_at or datetime.utcnow(),
            wasassociatedwith=agent.agent_id,
            activity_parameters={
                'term_text': term.term_text,
                'research_domain': term.research_domain,
                'term_id': str(term.id)
            },
            activity_status='completed'
        )
        db.session.add(activity)
        db.session.flush()  # Get activity_id

        # Check if term has a source (from first version's corpus_source)
        first_version = term.get_current_version()
        source_entity_id = None

        if first_version and first_version.corpus_source:
            # Create/get entity for the external source (OED, dictionary, etc.)
            source_entity = cls.get_or_create_source_entity(first_version.corpus_source)
            source_entity_id = source_entity.entity_id

        # Create entity representing the term
        entity = ProvEntity(
            entity_type='term',
            generatedattime=term.created_at or datetime.utcnow(),
            wasgeneratedby=activity.activity_id,
            wasattributedto=agent.agent_id,
            wasderivedfrom=source_entity_id,  # Link to source if available
            entity_value=_serialize_value({
                'term_id': str(term.id),
                'term_text': term.term_text,
                'research_domain': term.research_domain,
                'status': term.status
            }),
            entity_metadata={'created_via': 'ui'}
        )
        db.session.add(entity)
        db.session.commit()

        return activity, entity

    @classmethod
    def track_term_update(cls, term, user, changes: Dict[str, Any]) -> tuple[ProvActivity, ProvEntity]:
        """Track term updates."""
        agent = cls.get_or_create_user_agent(user.id, user.username)

        activity = ProvActivity(
            activity_type='term_update',
            startedattime=datetime.utcnow(),
            endedattime=datetime.utcnow(),
            wasassociatedwith=agent.agent_id,
            activity_parameters=_serialize_value({
                'term_id': str(term.id),
                'term_text': term.term_text,
                'fields_changed': list(changes.keys()),
                'num_changes': len(changes)
            }),
            activity_status='completed'
        )
        db.session.add(activity)
        db.session.flush()

        # Find previous entity for this term
        previous_entity = ProvEntity.query.filter_by(
            entity_type='term',
            entity_value=db.func.jsonb_build_object('term_id', term.id)
        ).order_by(ProvEntity.created_at.desc()).first()

        entity = ProvEntity(
            entity_type='term',
            generatedattime=datetime.utcnow(),
            wasgeneratedby=activity.activity_id,
            wasattributedto=agent.agent_id,
            wasderivedfrom=previous_entity.entity_id if previous_entity else None,
            entity_value=_serialize_value({
                'term_id': str(term.id),
                'term_text': term.term_text,
                'research_domain': term.research_domain,
                'status': term.status
            }),
            entity_metadata=_serialize_value({
                'changes': changes,  # Full change details stored here
                'updated_via': 'ui'
            })
        )
        db.session.add(entity)
        db.session.commit()

        return activity, entity
