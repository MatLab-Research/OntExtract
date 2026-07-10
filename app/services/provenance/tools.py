"""PROV-O processing tool execution tracking."""

from datetime import datetime
from typing import Any, Dict

from app import db
from app.models.prov_o_models import ProvActivity, ProvEntity, ProvRelationship
from .serialization import _serialize_value


class ProvenanceToolTrackingMixin:
    @classmethod
    def track_tool_execution(
        cls,
        tool_name: str,
        document,
        user,
        experiment,
        result_data: Dict[str, Any],
        started_at: datetime = None,
        ended_at: datetime = None
    ) -> tuple[ProvActivity, ProvEntity]:
        """
        Track tool execution (segment_paragraph, extract_entities, etc.).

        Args:
            tool_name: Name of tool executed
            document: Document model instance
            user: User model instance
            experiment: Experiment model instance
            result_data: Tool execution results
            started_at: Activity start time
            ended_at: Activity end time

        Returns:
            (activity, entity) tuple
        """
        agent = cls.get_or_create_user_agent(user.id, user.username)

        activity = ProvActivity(
            activity_type='tool_execution',
            startedattime=started_at or datetime.utcnow(),
            endedattime=ended_at or datetime.utcnow(),
            wasassociatedwith=agent.agent_id,
            activity_parameters=_serialize_value({
                'tool_name': tool_name,
                'document_id': document.id,
                'experiment_id': experiment.id
            }),
            activity_status='completed'
        )
        db.session.add(activity)
        db.session.flush()

        # Find document entity
        doc_entity = ProvEntity.query.filter(
            ProvEntity.entity_type == 'document',
            ProvEntity.entity_value['document_id'].astext == str(document.id)
        ).order_by(ProvEntity.created_at.desc()).first()

        entity = ProvEntity(
            entity_type='tool_result',
            generatedattime=ended_at or datetime.utcnow(),
            wasgeneratedby=activity.activity_id,
            wasattributedto=agent.agent_id,
            wasderivedfrom=doc_entity.entity_id if doc_entity else None,
            entity_value=_serialize_value({
                'tool_name': tool_name,
                'document_id': document.id,
                'experiment_id': experiment.id,
                'status': result_data.get('status'),
                'metadata': result_data.get('metadata', {})
            })
        )
        db.session.add(entity)

        # Create "used" relationship (activity used document)
        if doc_entity:
            used_rel = ProvRelationship(
                relationship_type='used',
                subject_type='activity',
                subject_id=activity.activity_id,
                object_type='entity',
                object_id=doc_entity.entity_id
            )
            db.session.add(used_rel)

        db.session.commit()

        return activity, entity
