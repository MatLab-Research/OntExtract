"""
Centralized PROV-O Provenance Tracking Service

Provides easy-to-use methods for tracking all actions in OntExtract:
- Term creation/updates
- Document uploads
- Experiment creation
- Tool executions
- Orchestration runs

Builds on the existing PROV-O database models (prov_agents, prov_activities, prov_entities).
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
import uuid

from app import db
from app.models.prov_o_models import ProvAgent, ProvActivity, ProvEntity, ProvRelationship


def _serialize_value(value: Any) -> Any:
    """
    Convert values to JSON-serializable format.
    Handles UUIDs, datetime objects, and nested structures.
    """
    if isinstance(value, uuid.UUID):
        return str(value)
    elif isinstance(value, datetime):
        return value.isoformat()
    elif isinstance(value, dict):
        return {k: _serialize_value(v) for k, v in value.items()}
    elif isinstance(value, (list, tuple)):
        return [_serialize_value(v) for v in value]
    else:
        return value


class ProvenanceService:
    """
    Centralized service for PROV-O provenance tracking.

    Makes it easy to track any action with proper PROV-O semantics:
    - Agent: Who did it (user, LLM, system)
    - Activity: What happened (term_creation, tool_execution, etc.)
    - Entity: What was created/modified (term, document, result)
    """

    # ========================================================================
    # AGENT MANAGEMENT
    # ========================================================================

    @staticmethod
    def get_or_create_user_agent(user_id: int, username: str = None) -> ProvAgent:
        """Get or create agent for a user."""
        return ProvAgent.get_or_create_user_agent(
            user_id=user_id,
            user_metadata={'username': username} if username else None
        )

    @staticmethod
    def get_or_create_system_agent() -> ProvAgent:
        """Get or create system agent for automated actions."""
        agent = ProvAgent.query.filter_by(foaf_name='system').first()
        if not agent:
            agent = ProvAgent(
                agent_type='SoftwareAgent',
                foaf_name='system',
                agent_metadata={
                    'tool_type': 'system',
                    'description': 'OntExtract system agent'
                }
            )
            db.session.add(agent)
            db.session.commit()
        return agent

    @staticmethod
    def get_or_create_llm_agent(provider: str = 'anthropic', model_id: str = None) -> ProvAgent:
        """Get or create LLM agent."""
        return ProvAgent.get_or_create_orchestrator_agent(model_provider=provider)

    # ========================================================================
    # TERM MANAGEMENT TRACKING
    # ========================================================================

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
                'description': term.description,
                'research_domain': term.research_domain,
                'status': term.status
            },
            activity_status='completed'
        )
        db.session.add(activity)
        db.session.flush()  # Get activity_id

        # Create entity representing the term
        entity = ProvEntity(
            entity_type='term',
            generatedattime=term.created_at or datetime.utcnow(),
            wasgeneratedby=activity.activity_id,
            wasattributedto=agent.agent_id,
            entity_value=_serialize_value({
                'term_id': term.id,
                'term_text': term.term_text,
                'description': term.description,
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
                'term_id': term.id,
                'changes': changes
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
                'term_id': term.id,
                'term_text': term.term_text,
                'description': term.description,
                'research_domain': term.research_domain,
                'status': term.status
            }),
            entity_metadata=_serialize_value({'changes': changes})
        )
        db.session.add(entity)
        db.session.commit()

        return activity, entity

    # ========================================================================
    # DOCUMENT MANAGEMENT TRACKING
    # ========================================================================

    @classmethod
    def track_document_upload(cls, document, user, experiment=None) -> tuple[ProvActivity, ProvEntity]:
        """Track document upload."""
        agent = cls.get_or_create_user_agent(user.id, user.username)

        activity = ProvActivity(
            activity_type='document_upload',
            startedattime=document.created_at or datetime.utcnow(),
            endedattime=document.created_at or datetime.utcnow(),
            wasassociatedwith=agent.agent_id,
            activity_parameters=_serialize_value({
                'filename': document.original_filename,
                'file_type': document.file_type,
                'content_type': document.content_type,
                'document_type': document.document_type,
                'experiment_id': experiment.id if experiment else None
            }),
            activity_status='completed'
        )
        db.session.add(activity)
        db.session.flush()

        entity = ProvEntity(
            entity_type='document',
            generatedattime=document.created_at or datetime.utcnow(),
            wasgeneratedby=activity.activity_id,
            wasattributedto=agent.agent_id,
            entity_value=_serialize_value({
                'document_id': document.id,
                'document_uuid': document.uuid,
                'filename': document.original_filename,
                'title': document.title,
                'content_type': document.content_type,
                'document_type': document.document_type,
                'word_count': document.word_count,
                'character_count': document.character_count
            })
        )
        db.session.add(entity)
        db.session.commit()

        return activity, entity

    @classmethod
    def track_metadata_extraction(
        cls,
        document,
        user,
        extraction_source: str,
        extracted_fields: Dict[str, Any],
        confidence: float = 0.9
    ) -> tuple[ProvActivity, ProvEntity]:
        """
        Track automated metadata extraction (CrossRef, Zotero, PDF analysis).

        Args:
            document: Document instance
            user: User who initiated the upload (attribution)
            extraction_source: 'crossref', 'zotero', 'pdf_analysis'
            extracted_fields: Dictionary of extracted metadata fields
            confidence: Confidence score of extraction
        """
        # Get appropriate agent (system/API agent for automated extraction)
        if extraction_source == 'crossref':
            agent = ProvAgent.query.filter_by(foaf_name='crossref_api').first()
            if not agent:
                agent = ProvAgent(
                    agent_type='SoftwareAgent',
                    foaf_name='crossref_api',
                    agent_metadata={
                        'tool_type': 'metadata_api',
                        'description': 'CrossRef API metadata extraction',
                        'url': 'https://api.crossref.org'
                    }
                )
                db.session.add(agent)
                db.session.flush()
        elif extraction_source == 'zotero':
            agent = ProvAgent.query.filter_by(foaf_name='zotero_api').first()
            if not agent:
                agent = ProvAgent(
                    agent_type='SoftwareAgent',
                    foaf_name='zotero_api',
                    agent_metadata={
                        'tool_type': 'metadata_api',
                        'description': 'Zotero API metadata extraction',
                        'url': 'https://www.zotero.org'
                    }
                )
                db.session.add(agent)
                db.session.flush()
        else:
            agent = cls.get_or_create_system_agent()

        activity = ProvActivity(
            activity_type='metadata_extraction',
            startedattime=datetime.utcnow(),
            endedattime=datetime.utcnow(),
            wasassociatedwith=agent.agent_id,
            activity_parameters=_serialize_value({
                'document_id': document.id,
                'extraction_source': extraction_source,
                'fields_extracted': list(extracted_fields.keys()),
                'confidence': confidence
            }),
            activity_status='completed'
        )
        db.session.add(activity)
        db.session.flush()

        # Find document entity to link derivation
        doc_entity = ProvEntity.query.filter(
            ProvEntity.entity_type == 'document',
            ProvEntity.entity_value['document_id'].astext == str(document.id)
        ).order_by(ProvEntity.created_at.desc()).first()

        entity = ProvEntity(
            entity_type='metadata',
            generatedattime=datetime.utcnow(),
            wasgeneratedby=activity.activity_id,
            wasattributedto=agent.agent_id,
            wasderivedfrom=doc_entity.entity_id if doc_entity else None,
            entity_value=_serialize_value({
                'document_id': document.id,
                'document_uuid': document.uuid,
                'extraction_source': extraction_source,
                'extracted_metadata': extracted_fields,
                'confidence': confidence
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

    @classmethod
    def track_metadata_update(
        cls,
        document,
        user,
        changes: Dict[str, Dict[str, Any]]
    ) -> tuple[ProvActivity, ProvEntity]:
        """
        Track manual metadata updates by users.

        Args:
            document: Document instance
            user: User making the update
            changes: Dict with 'old' and 'new' values for each field
                    e.g., {'title': {'old': 'Old Title', 'new': 'New Title'}}
        """
        agent = cls.get_or_create_user_agent(user.id, user.username)

        activity = ProvActivity(
            activity_type='metadata_update',
            startedattime=datetime.utcnow(),
            endedattime=datetime.utcnow(),
            wasassociatedwith=agent.agent_id,
            activity_parameters=_serialize_value({
                'document_id': document.id,
                'document_uuid': document.uuid,
                'fields_modified': list(changes.keys())
            }),
            activity_status='completed'
        )
        db.session.add(activity)
        db.session.flush()

        # Find previous metadata entity
        previous_entity = ProvEntity.query.filter(
            ProvEntity.entity_type == 'metadata',
            ProvEntity.entity_value['document_id'].astext == str(document.id)
        ).order_by(ProvEntity.created_at.desc()).first()

        entity = ProvEntity(
            entity_type='metadata',
            generatedattime=datetime.utcnow(),
            wasgeneratedby=activity.activity_id,
            wasattributedto=agent.agent_id,
            wasderivedfrom=previous_entity.entity_id if previous_entity else None,
            entity_value=_serialize_value({
                'document_id': document.id,
                'document_uuid': document.uuid,
                'source': 'manual_edit',
                'changes': changes,
                'updated_metadata': document.source_metadata
            })
        )
        db.session.add(entity)
        db.session.commit()

        return activity, entity

    # ========================================================================
    # EXPERIMENT TRACKING
    # ========================================================================

    @classmethod
    def track_experiment_creation(cls, experiment, user) -> tuple[ProvActivity, ProvEntity]:
        """Track experiment creation."""
        agent = cls.get_or_create_user_agent(user.id, user.username)

        activity = ProvActivity(
            activity_type='experiment_creation',
            startedattime=experiment.created_at or datetime.utcnow(),
            endedattime=experiment.created_at or datetime.utcnow(),
            wasassociatedwith=agent.agent_id,
            activity_parameters=_serialize_value({
                'experiment_name': experiment.name,
                'description': experiment.description,
                'term_id': experiment.term_id
            }),
            activity_status='completed'
        )
        db.session.add(activity)
        db.session.flush()

        entity = ProvEntity(
            entity_type='experiment',
            generatedattime=experiment.created_at or datetime.utcnow(),
            wasgeneratedby=activity.activity_id,
            wasattributedto=agent.agent_id,
            entity_value=_serialize_value({
                'experiment_id': experiment.id,
                'name': experiment.name,
                'description': experiment.description,
                'term_id': experiment.term_id,
                'status': experiment.status
            })
        )
        db.session.add(entity)
        db.session.commit()

        return activity, entity

    # ========================================================================
    # TOOL EXECUTION TRACKING
    # ========================================================================

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

    # ========================================================================
    # ORCHESTRATION TRACKING
    # ========================================================================

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

    # ========================================================================
    # QUERY HELPERS FOR TIMELINE UI
    # ========================================================================

    @staticmethod
    def get_timeline(
        experiment_id: int = None,
        user_id: int = None,
        activity_type: str = None,
        term_id: int = None,
        document_id: int = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get chronological timeline of activities with entities and agents.

        Args:
            experiment_id: Filter by experiment (optional)
            user_id: Filter by user (optional)
            activity_type: Filter by activity type (optional)
            term_id: Filter by term (optional)
            document_id: Filter by document (optional)
            limit: Maximum number of activities to return

        Returns:
            List of timeline entries with full PROV-O context
        """
        query = db.session.query(ProvActivity)\
            .order_by(ProvActivity.startedattime.desc())

        # Apply filters
        if activity_type:
            query = query.filter(ProvActivity.activity_type == activity_type)

        if experiment_id:
            query = query.filter(
                ProvActivity.activity_parameters['experiment_id'].astext == str(experiment_id)
            )

        if term_id:
            query = query.filter(
                ProvActivity.activity_parameters['term_id'].astext == str(term_id)
            )

        if document_id:
            query = query.filter(
                ProvActivity.activity_parameters['document_id'].astext == str(document_id)
            )

        if user_id:
            # Join with agents to filter by user
            user_agent = ProvAgent.get_or_create_user_agent(user_id)
            query = query.filter(ProvActivity.wasassociatedwith == user_agent.agent_id)

        activities = query.limit(limit).all()

        # Enrich with entities and agents
        timeline = []
        for activity in activities:
            # Get generated entities
            generated = ProvEntity.query.filter_by(wasgeneratedby=activity.activity_id).all()

            # Get used entities (via relationships)
            used_rels = ProvRelationship.query.filter_by(
                relationship_type='used',
                subject_id=activity.activity_id
            ).all()
            used = [
                ProvEntity.query.get(rel.object_id)
                for rel in used_rels
            ] if used_rels else []

            # Get agent
            agent = ProvAgent.query.get(activity.wasassociatedwith)

            timeline.append({
                'activity': {
                    'id': str(activity.activity_id),
                    'type': activity.activity_type,
                    'started_at': activity.startedattime.isoformat() if activity.startedattime else None,
                    'ended_at': activity.endedattime.isoformat() if activity.endedattime else None,
                    'status': activity.activity_status,
                    'parameters': activity.activity_parameters
                },
                'agent': {
                    'id': str(agent.agent_id),
                    'type': agent.agent_type,
                    'name': agent.foaf_name
                } if agent else None,
                'generated': [
                    {
                        'id': str(e.entity_id),
                        'type': e.entity_type,
                        'value': e.entity_value
                    }
                    for e in generated
                ],
                'used': [
                    {
                        'id': str(e.entity_id),
                        'type': e.entity_type,
                        'value': e.entity_value
                    }
                    for e in used if e
                ]
            })

        return timeline

    @staticmethod
    def get_entity_lineage(entity_id: uuid.UUID) -> List[ProvEntity]:
        """
        Get full lineage of an entity (all derivation ancestors).

        Args:
            entity_id: Entity UUID

        Returns:
            List of entities in lineage order (most recent first)
        """
        lineage = []
        current = ProvEntity.query.get(entity_id)

        while current:
            lineage.append(current)
            if current.wasderivedfrom:
                current = ProvEntity.query.get(current.wasderivedfrom)
            else:
                break

        return lineage


# Singleton instance
provenance_service = ProvenanceService()
