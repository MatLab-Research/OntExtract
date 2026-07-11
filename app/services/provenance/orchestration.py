"""PROV-O orchestration lifecycle tracking."""

import uuid
from datetime import datetime
from typing import Any, Dict

from app import db
from app.models.prov_o_models import ProvActivity, ProvEntity
from .serialization import _serialize_value


class ProvenanceOrchestrationTrackingMixin:
    @classmethod
    def track_orchestration_start(
        cls,
        run_id: str,
        experiment,
        user,
        parameters: Dict[str, Any] = None
    ) -> ProvActivity:
        """Track start of orchestration run."""
        agent = cls.get_or_create_user_agent(user.id, user.username)
        llm_agent = cls.get_or_create_llm_agent()

        activity = ProvActivity(
            activity_id=uuid.UUID(run_id),
            activity_type='orchestration_run',
            startedattime=datetime.utcnow(),
            wasassociatedwith=llm_agent.agent_id,
            activity_parameters=_serialize_value({
                'experiment_id': experiment.id,
                'initiated_by_user': user.id,
                'parameters': parameters or {}
            }),
            activity_status='active'
        )
        db.session.add(activity)
        db.session.commit()

        return activity

    @classmethod
    def track_orchestration_complete(
        cls,
        run_id: str,
        strategy: Dict[str, Any],
        results: Dict[str, Any] = None
    ) -> ProvEntity:
        """Track completion of orchestration run."""
        activity = ProvActivity.query.get(uuid.UUID(run_id))
        if not activity:
            raise ValueError(f"Orchestration activity {run_id} not found")

        activity.endedattime = datetime.utcnow()
        activity.activity_status = 'completed'
        activity.activity_metadata = _serialize_value(results or {})

        entity = ProvEntity(
            entity_type='processing_strategy',
            generatedattime=datetime.utcnow(),
            wasgeneratedby=activity.activity_id,
            wasattributedto=activity.wasassociatedwith,
            entity_value=_serialize_value({
                'strategy': strategy,
                'confidence': strategy.get('confidence', 0.0),
                'reasoning': strategy.get('reasoning', '')
            })
        )
        db.session.add(entity)
        db.session.commit()

        return entity
