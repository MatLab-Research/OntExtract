"""
PROV-O Database Models - First-Class Citizens Implementation

Implements PROV-O concepts (Entity, Activity, Agent) directly in the relational structure
as described in section 3.2 of the JCDL paper, ensuring every analytical decision has
mandatory, queryable provenance.
"""

import uuid
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import CheckConstraint
from app import db


class ProvAgent(db.Model):
    """
    PROV-O Agent: Researchers, LLMs, and tools as primary entities
    
    Maps to prov:Agent in W3C PROV-O specification with exact property names
    """
    __tablename__ = 'prov_agents'
    
    agent_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_type = db.Column(db.String(20), nullable=False)  # Person, Organization, SoftwareAgent
    foaf_name = db.Column(db.String(255))                 # foaf:name
    foaf_givenname = db.Column(db.String(255))            # foaf:givenName (lowercase in DB)
    foaf_mbox = db.Column(db.String(255))                 # foaf:mbox (email)
    foaf_homepage = db.Column(db.String(500))             # foaf:homePage (lowercase in DB)
    agent_metadata = db.Column(JSONB, default={})         # Additional agent metadata
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    
    # Constraint to ensure valid PROV-O agent subclasses
    __table_args__ = (
        CheckConstraint(
            agent_type.in_(['Person', 'Organization', 'SoftwareAgent']),
            name='valid_prov_agent_type'
        ),
    )
    
    # Relationships (PROV-O properties)
    associated_activities = db.relationship('ProvActivity', foreign_keys='ProvActivity.wasassociatedwith', back_populates='associated_agent')
    attributed_entities = db.relationship('ProvEntity', foreign_keys='ProvEntity.wasattributedto', back_populates='attributed_agent')
    
    def __repr__(self):
        return f"<ProvAgent {self.foaf_name or self.agent_id} ({self.agent_type})>"
    
    @classmethod
    def get_or_create_langextract_agent(cls):
        """Get or create the LangExtract agent using PROV-O compliant properties"""
        agent = cls.query.filter_by(foaf_name='LangExtract Gemini').first()
        if not agent:
            agent = cls(
                agent_type='SoftwareAgent',
                foaf_name='LangExtract Gemini',
                agent_metadata={
                    'tool_type': 'document_analyzer',
                    'model_provider': 'google',
                    'model_id': 'gemini-2.0-flash-exp',
                    'capabilities': ['structured_extraction', 'character_positioning', 'semantic_analysis'],
                    'version': '1.0.9',
                    'reliability_score': 0.85
                }
            )
            db.session.add(agent)
            db.session.commit()
        return agent
    
    @classmethod
    def get_or_create_orchestrator_agent(cls, model_provider='anthropic'):
        """Get or create the orchestration LLM agent"""
        identifier = f'orchestrator_{model_provider}'
        agent = cls.query.filter_by(foaf_name=identifier).first()
        if not agent:
            metadata = {
                'tool_type': 'llm_orchestrator',
                'model_provider': model_provider,
                'capabilities': ['tool_selection', 'analysis_coordination', 'synthesis_planning'],
                'version': '1.0'
            }
            
            if model_provider == 'anthropic':
                metadata.update({
                    'model_id': 'claude-sonnet-4-5-20250929',
                    'reliability_score': 0.9
                })
            elif model_provider == 'openai':
                metadata.update({
                    'model_id': 'gpt-4',
                    'reliability_score': 0.85
                })
            
            agent = cls(
                agent_type='SoftwareAgent',
                foaf_name=identifier,
                agent_metadata=metadata
            )
            db.session.add(agent)
            db.session.commit()
        return agent
    
    @classmethod
    def get_or_create_user_agent(cls, user_id, user_metadata=None):
        """Get or create a human user agent"""
        identifier = f'researcher:{user_id}'
        agent = cls.query.filter_by(foaf_name=identifier).first()
        if not agent:
            agent = cls(
                agent_type='Person',
                foaf_name=identifier,
                agent_metadata=user_metadata or {'role': 'researcher'}
            )
            db.session.add(agent)
            db.session.commit()
        elif agent.agent_type != 'Person':
            # Fix legacy agents that were incorrectly typed
            agent.agent_type = 'Person'
            db.session.commit()
        return agent


class ProvActivity(db.Model):
    """
    PROV-O Activity: Analytical processes with embedded relationships
    
    Maps to prov:Activity in W3C PROV-O specification with exact property names
    """
    __tablename__ = 'prov_activities'
    
    activity_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    activity_type = db.Column(db.String(100), nullable=False)
    startedattime = db.Column(db.DateTime(timezone=True))      # prov:startedAtTime (lowercase in DB)
    endedattime = db.Column(db.DateTime(timezone=True))        # prov:endedAtTime (lowercase in DB)
    wasassociatedwith = db.Column(UUID(as_uuid=True), db.ForeignKey('prov_agents.agent_id'))  # prov:wasAssociatedWith (lowercase in DB)
    activity_parameters = db.Column(JSONB, default={})        # Activity configuration
    activity_status = db.Column(db.String(20), default='active')  # active, completed, failed
    activity_metadata = db.Column(JSONB, default={})          # Additional metadata
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships using PROV-O properties
    associated_agent = db.relationship('ProvAgent', foreign_keys=[wasassociatedwith], back_populates='associated_activities')
    generated_entities = db.relationship('ProvEntity', foreign_keys='ProvEntity.wasgeneratedby', back_populates='generating_activity')
    
    def __repr__(self):
        return f"<ProvActivity {self.activity_type} by {self.associated_agent.foaf_name if self.associated_agent else 'unknown'}>"
    
    @classmethod
    def create_langextract_activity(cls, document_id, langextract_agent, parameters=None):
        """Create a LangExtract document analysis activity using PROV-O properties"""
        return cls(
            activity_type='langextract_document_analysis',
            wasassociatedwith=langextract_agent.agent_id,
            startedattime=datetime.utcnow(),
            activity_parameters={
                'document_id': document_id,
                'extraction_method': 'langextract_gemini',
                'analysis_stage': 'structured_extraction',
                **(parameters or {})
            }
        )
    
    @classmethod
    def create_orchestration_activity(cls, orchestrator_agent, langextract_activity, parameters=None):
        """Create an LLM orchestration activity"""
        return cls(
            activity_type='llm_orchestration_coordination',
            wasassociatedwith=orchestrator_agent.agent_id,
            startedattime=datetime.utcnow(),
            activity_parameters={
                'input_activity_id': str(langextract_activity.activity_id),
                'orchestration_stage': 'tool_selection_and_coordination',
                'analysis_stage': 'orchestration_planning',
                **(parameters or {})
            }
        )
    
    def complete_activity(self, status='completed'):
        """Mark activity as completed with timestamp"""
        self.endedattime = datetime.utcnow()
        self.activity_status = status
        db.session.commit()


class ProvEntity(db.Model):
    """
    PROV-O Entity: Decisions and outputs with mandatory provenance
    
    Maps to prov:Entity in W3C PROV-O specification with exact property names
    """
    __tablename__ = 'prov_entities'
    
    entity_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type = db.Column(db.String(100), nullable=False)
    generatedattime = db.Column(db.DateTime(timezone=True))                                    # prov:generatedAtTime (lowercase in DB)
    invalidatedattime = db.Column(db.DateTime(timezone=True))                                 # prov:invalidatedAtTime (lowercase in DB)
    wasgeneratedby = db.Column(UUID(as_uuid=True), db.ForeignKey('prov_activities.activity_id'), nullable=False)  # prov:wasGeneratedBy (lowercase in DB)
    wasattributedto = db.Column(UUID(as_uuid=True), db.ForeignKey('prov_agents.agent_id'))   # prov:wasAttributedTo (lowercase in DB)
    wasderivedfrom = db.Column(UUID(as_uuid=True), db.ForeignKey('prov_entities.entity_id')) # prov:wasDerivedFrom (lowercase in DB)
    entity_value = db.Column(JSONB, nullable=False, default={})                              # prov:value (entity content)
    entity_metadata = db.Column(JSONB, default={})                                           # Additional metadata
    character_start = db.Column(db.Integer)                                                   # Character position tracking
    character_end = db.Column(db.Integer)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    
    # Constraint to ensure mandatory provenance
    __table_args__ = (
        CheckConstraint(
            'wasgeneratedby IS NOT NULL',
            name='must_have_generation_provenance'
        ),
        CheckConstraint(
            '(character_start IS NULL AND character_end IS NULL) OR (character_start IS NOT NULL AND character_end IS NOT NULL AND character_start <= character_end)',
            name='valid_character_positions'
        ),
    )
    
    # Relationships using PROV-O properties
    generating_activity = db.relationship('ProvActivity', foreign_keys=[wasgeneratedby], back_populates='generated_entities')
    attributed_agent = db.relationship('ProvAgent', foreign_keys=[wasattributedto], back_populates='attributed_entities')
    derived_from_entity = db.relationship('ProvEntity', remote_side=[entity_id], foreign_keys=[wasderivedfrom])
    
    def __repr__(self):
        return f"<ProvEntity {self.entity_type} from {self.generating_activity.activity_type if self.generating_activity else 'unknown'}>"
    
    @classmethod
    def create_langextract_entity(cls, langextract_activity, extraction_results):
        """Create entity representing LangExtract extraction results using PROV-O properties"""
        return cls(
            entity_type='langextract_document_extraction',
            generatedattime=datetime.utcnow(),
            wasgeneratedby=langextract_activity.activity_id,
            wasattributedto=langextract_activity.wasassociatedwith,
            entity_value={
                'extraction_results': extraction_results,
                'extraction_timestamp': datetime.utcnow().isoformat(),
                'character_level_positions': True,
                'extraction_confidence': extraction_results.get('extraction_confidence', 0.5),
                'key_concepts_count': len(extraction_results.get('key_concepts', [])),
                'temporal_markers_count': len(extraction_results.get('temporal_markers', [])),
                'domain_indicators': extraction_results.get('domain_indicators', [])
            }
        )
    
    @classmethod
    def create_orchestration_entity(cls, orchestration_activity, orchestration_plan):
        """Create entity representing orchestration plan"""
        return cls(
            entity_type='llm_orchestration_plan',
            entity_content={
                'orchestration_plan': orchestration_plan,
                'plan_timestamp': datetime.utcnow().isoformat(),
                'tools_selected': orchestration_plan.get('orchestration_plan', {}).get('selected_tools', []),
                'confidence': orchestration_plan.get('orchestration_plan', {}).get('confidence', 0.5),
                'synthesis_strategy': orchestration_plan.get('synthesis_preparation', {}).get('strategy', 'sequential'),
                'ready_for_execution': orchestration_plan.get('ready_for_execution', False)
            },
            generated_by_activity=orchestration_activity.activity_id
        )


class ProvRelationship(db.Model):
    """
    PROV-O Relationships: wasGeneratedBy, wasAssociatedWith, wasDerivedFrom, etc.
    
    Tracks explicit relationships between entities, activities, and agents
    """
    __tablename__ = 'prov_relationships'
    
    relationship_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    relationship_type = db.Column(db.String(50), nullable=False)  # wasGeneratedBy, wasDerivedFrom, etc.
    subject_type = db.Column(db.String(20), nullable=False)  # entity, activity, agent
    subject_id = db.Column(UUID(as_uuid=True), nullable=False)
    object_type = db.Column(db.String(20), nullable=False)  # entity, activity, agent
    object_id = db.Column(UUID(as_uuid=True), nullable=False)
    relationship_metadata = db.Column(JSONB)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Constraints for valid PROV-O relationships
    __table_args__ = (
        CheckConstraint(
            subject_type.in_(['entity', 'activity', 'agent']),
            name='valid_subject_type'
        ),
        CheckConstraint(
            object_type.in_(['entity', 'activity', 'agent']),
            name='valid_object_type'
        ),
        CheckConstraint(
            relationship_type.in_([
                'wasGeneratedBy',      # entity wasGeneratedBy activity
                'wasAssociatedWith',   # activity wasAssociatedWith agent
                'wasDerivedFrom',      # entity wasDerivedFrom entity
                'wasInformedBy',       # activity wasInformedBy activity
                'actedOnBehalfOf',     # agent actedOnBehalfOf agent
                'wasAttributedTo',     # entity wasAttributedTo agent
                'used',                # activity used entity
                'wasStartedBy',        # activity wasStartedBy entity
                'wasEndedBy'           # activity wasEndedBy entity
            ]),
            name='valid_relationship_type'
        ),
    )
    
    def __repr__(self):
        return f"<ProvRelationship {self.subject_type}:{self.subject_id} {self.relationship_type} {self.object_type}:{self.object_id}>"
    
    @classmethod
    def create_generation_relationship(cls, entity, activity):
        """Create wasGeneratedBy relationship"""
        return cls(
            relationship_type='wasGeneratedBy',
            subject_type='entity',
            subject_id=entity.entity_id,
            object_type='activity',
            object_id=activity.activity_id,
            relationship_metadata={'created_automatically': True}
        )
    
    @classmethod
    def create_derivation_relationship(cls, derived_entity, source_entity, derivation_type='transformation'):
        """Create wasDerivedFrom relationship"""
        return cls(
            relationship_type='wasDerivedFrom',
            subject_type='entity',
            subject_id=derived_entity.entity_id,
            object_type='entity',
            object_id=source_entity.entity_id,
            relationship_metadata={'derivation_type': derivation_type}
        )
    
    @classmethod
    def create_information_flow_relationship(cls, downstream_activity, upstream_activity):
        """Create wasInformedBy relationship between activities"""
        return cls(
            relationship_type='wasInformedBy',
            subject_type='activity',
            subject_id=downstream_activity.activity_id,
            object_type='activity',
            object_id=upstream_activity.activity_id,
            relationship_metadata={'information_flow': True}
        )