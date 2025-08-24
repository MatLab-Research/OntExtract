from sqlalchemy.dialects.postgresql import UUID, JSON, ARRAY
from datetime import datetime
from app import db
import uuid


class SemanticDriftActivity(db.Model):
    """PROV-O Activity: Semantic drift detection activities between time periods"""
    
    __tablename__ = 'semantic_drift_activities'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    activity_type = db.Column(db.String(50), default='semantic_drift_detection', nullable=False)
    
    # Temporal scope
    start_period = db.Column(db.String(50), nullable=False, index=True)
    end_period = db.Column(db.String(50), nullable=False, index=True)
    temporal_scope_years = db.Column(ARRAY(db.Integer))
    
    # PROV-O relationships
    used_entity = db.Column(UUID(as_uuid=True), db.ForeignKey('term_versions.id'), index=True)
    generated_entity = db.Column(UUID(as_uuid=True), db.ForeignKey('term_versions.id'), index=True)
    was_associated_with = db.Column(UUID(as_uuid=True), db.ForeignKey('analysis_agents.id'), index=True)
    
    # Drift detection metrics
    drift_metrics = db.Column(JSON)  # Detailed numerical results
    detection_algorithm = db.Column(db.String(100))
    algorithm_parameters = db.Column(JSON)
    
    # Activity metadata
    started_at_time = db.Column(db.DateTime(timezone=True))
    ended_at_time = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    activity_status = db.Column(db.String(20), default='completed', index=True)
    
    # Results
    drift_detected = db.Column(db.Boolean, default=False)
    drift_magnitude = db.Column(db.Numeric(4,3))
    drift_type = db.Column(db.String(30))  # gradual, sudden, domain_shift, semantic_bleaching
    evidence_summary = db.Column(db.Text)
    
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    input_version = db.relationship('TermVersion', foreign_keys=[used_entity], 
                                   backref='drift_activities_as_input', post_update=True)
    output_version = db.relationship('TermVersion', foreign_keys=[generated_entity],
                                    backref='drift_activities_as_output', post_update=True)
    analysis_agent = db.relationship('AnalysisAgent', backref='drift_activities')
    creator = db.relationship('User', backref='created_drift_activities')
    
    # Constraints
    __table_args__ = (
        db.CheckConstraint("activity_status IN ('running', 'completed', 'error', 'provisional')"),
        db.CheckConstraint("drift_magnitude >= 0 AND drift_magnitude <= 1")
    )
    
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def calculate_drift_score(self):
        """Calculate overall drift score from individual metrics"""
        if not self.drift_metrics:
            return None
        
        # Extract numerical drift measures
        metrics = self.drift_metrics
        scores = []
        
        if metrics.get('neighborhood_overlap') is not None:
            # Lower overlap = higher drift
            scores.append(1 - metrics['neighborhood_overlap'])
        
        if metrics.get('positional_change') is not None:
            scores.append(metrics['positional_change'])
        
        if metrics.get('similarity_reduction') is not None:
            scores.append(metrics['similarity_reduction'])
        
        if scores:
            return sum(scores) / len(scores)
        return None
    
    def get_temporal_span(self):
        """Get the temporal span of this drift analysis"""
        if not self.temporal_scope_years:
            return None
        return max(self.temporal_scope_years) - min(self.temporal_scope_years)
    
    def is_significant_drift(self, threshold=0.5):
        """Check if detected drift is significant"""
        drift_score = self.calculate_drift_score()
        return drift_score is not None and drift_score > threshold
    
    def get_drift_classification(self):
        """Classify the type and magnitude of drift"""
        drift_score = self.calculate_drift_score()
        if drift_score is None:
            return 'unknown'
        
        if drift_score < 0.2:
            return 'stable'
        elif drift_score < 0.4:
            return 'minor_drift'
        elif drift_score < 0.6:
            return 'moderate_drift'
        elif drift_score < 0.8:
            return 'major_drift'
        else:
            return 'radical_change'
    
    def to_dict(self, include_metrics=True):
        """Convert activity to dictionary for API responses"""
        result = {
            'id': str(self.id),
            'activity_type': self.activity_type,
            'start_period': self.start_period,
            'end_period': self.end_period,
            'temporal_scope_years': self.temporal_scope_years,
            'used_entity': str(self.used_entity) if self.used_entity else None,
            'generated_entity': str(self.generated_entity) if self.generated_entity else None,
            'was_associated_with': str(self.was_associated_with) if self.was_associated_with else None,
            'detection_algorithm': self.detection_algorithm,
            'activity_status': self.activity_status,
            'drift_detected': self.drift_detected,
            'drift_magnitude': float(self.drift_magnitude) if self.drift_magnitude else None,
            'drift_type': self.drift_type,
            'evidence_summary': self.evidence_summary,
            'started_at_time': self.started_at_time.isoformat() if self.started_at_time else None,
            'ended_at_time': self.ended_at_time.isoformat() if self.ended_at_time else None,
            'created_at': self.created_at.isoformat(),
            'creator': self.creator.username if self.creator else None,
            'temporal_span': self.get_temporal_span(),
            'drift_score': self.calculate_drift_score(),
            'drift_classification': self.get_drift_classification()
        }
        
        if include_metrics and self.drift_metrics:
            result['drift_metrics'] = self.drift_metrics
            result['algorithm_parameters'] = self.algorithm_parameters
        
        return result
    
    @staticmethod
    def get_activities_by_period_range(start_year, end_year):
        """Get activities within a temporal range"""
        return SemanticDriftActivity.query.filter(
            SemanticDriftActivity.temporal_scope_years.op('&&')(f'[{start_year},{end_year}]')
        ).all()
    
    @staticmethod
    def get_activities_for_term(term_id):
        """Get all drift activities for a specific term"""
        from app.models.term import TermVersion
        version_ids = db.session.query(TermVersion.id).filter_by(term_id=term_id).all()
        version_ids = [str(v[0]) for v in version_ids]
        
        return SemanticDriftActivity.query.filter(
            (SemanticDriftActivity.used_entity.in_(version_ids)) |
            (SemanticDriftActivity.generated_entity.in_(version_ids))
        ).all()
    
    def __repr__(self):
        return f'<SemanticDriftActivity {self.start_period}→{self.end_period}>'


class AnalysisAgent(db.Model):
    """PROV-O Agent: Software algorithms and human curators responsible for analysis"""
    
    __tablename__ = 'analysis_agents'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_type = db.Column(db.String(20), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    version = db.Column(db.String(50))
    
    # For software agents
    algorithm_type = db.Column(db.String(100))
    model_parameters = db.Column(JSON)
    training_data = db.Column(db.String(200))
    
    # For human agents
    expertise_domain = db.Column(db.String(100))
    institutional_affiliation = db.Column(db.String(200))
    
    # Agent metadata
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True, index=True)
    
    # Self-reference for user agents
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relationships
    user = db.relationship('User', backref='analysis_agents')
    
    # Constraints
    __table_args__ = (
        db.CheckConstraint("agent_type IN ('SoftwareAgent', 'Person', 'Organization')"),
    )
    
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    @classmethod
    def get_manual_agent(cls):
        """Get or create the default manual curation agent"""
        agent = cls.query.filter_by(
            agent_type='Person',
            algorithm_type='Manual_Curation'
        ).first()
        
        if not agent:
            agent = cls(
                agent_type='Person',
                name='Manual Curation',
                description='Human curator performing manual semantic analysis',
                algorithm_type='Manual_Curation',
                version='1.0'
            )
            db.session.add(agent)
            db.session.commit()
        
        return agent
    
    @classmethod
    def create_user_agent(cls, user):
        """Create a personal agent for a user"""
        agent = cls(
            agent_type='Person',
            name=f"{user.get_full_name()} (Manual Analysis)",
            description=f"Manual semantic analysis by {user.get_full_name()}",
            algorithm_type='Manual_Curation',
            expertise_domain=getattr(user, 'organization', 'General'),
            institutional_affiliation=getattr(user, 'organization', None),
            user_id=user.id,
            version='1.0'
        )
        db.session.add(agent)
        db.session.commit()
        return agent
    
    @classmethod
    def get_software_agents(cls):
        """Get all active software agents"""
        return cls.query.filter_by(agent_type='SoftwareAgent', is_active=True).all()
    
    @classmethod
    def get_human_agents(cls):
        """Get all active human agents"""
        return cls.query.filter_by(agent_type='Person', is_active=True).all()
    
    def get_activity_count(self):
        """Get number of activities performed by this agent"""
        return SemanticDriftActivity.query.filter_by(was_associated_with=self.id).count()
    
    def get_recent_activities(self, limit=10):
        """Get recent activities by this agent"""
        return SemanticDriftActivity.query.filter_by(
            was_associated_with=self.id
        ).order_by(
            SemanticDriftActivity.created_at.desc()
        ).limit(limit).all()
    
    def is_software_agent(self):
        """Check if this is a software agent"""
        return self.agent_type == 'SoftwareAgent'
    
    def is_human_agent(self):
        """Check if this is a human agent"""
        return self.agent_type == 'Person'
    
    def to_dict(self, include_activities=False):
        """Convert agent to dictionary for API responses"""
        result = {
            'id': str(self.id),
            'agent_type': self.agent_type,
            'name': self.name,
            'description': self.description,
            'version': self.version,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'activity_count': self.get_activity_count()
        }
        
        if self.is_software_agent():
            result.update({
                'algorithm_type': self.algorithm_type,
                'model_parameters': self.model_parameters,
                'training_data': self.training_data
            })
        
        if self.is_human_agent():
            result.update({
                'expertise_domain': self.expertise_domain,
                'institutional_affiliation': self.institutional_affiliation,
                'user_id': self.user_id
            })
        
        if include_activities:
            result['recent_activities'] = [
                activity.to_dict(include_metrics=False) 
                for activity in self.get_recent_activities()
            ]
        
        return result
    
    def __repr__(self):
        return f'<AnalysisAgent {self.name} ({self.agent_type})>'


class ProvenanceChain(db.Model):
    """Complex provenance relationships for detailed audit trails"""
    
    __tablename__ = 'provenance_chains'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_id = db.Column(UUID(as_uuid=True))  # Can reference various entity types
    entity_type = db.Column(db.String(30), nullable=False)
    
    # Qualified derivation details
    was_derived_from = db.Column(UUID(as_uuid=True))
    derivation_activity = db.Column(UUID(as_uuid=True), db.ForeignKey('semantic_drift_activities.id'))
    derivation_metadata = db.Column(JSON)
    
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    activity = db.relationship('SemanticDriftActivity', backref='provenance_chains')
    
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def to_dict(self):
        """Convert provenance chain to dictionary"""
        return {
            'id': str(self.id),
            'entity_id': str(self.entity_id),
            'entity_type': self.entity_type,
            'was_derived_from': str(self.was_derived_from) if self.was_derived_from else None,
            'derivation_activity': str(self.derivation_activity) if self.derivation_activity else None,
            'derivation_metadata': self.derivation_metadata,
            'created_at': self.created_at.isoformat()
        }
    
    @staticmethod
    def trace_provenance(entity_id, entity_type, max_depth=10):
        """Trace the complete provenance chain for an entity"""
        chain = []
        current_id = entity_id
        depth = 0
        
        while current_id and depth < max_depth:
            link = ProvenanceChain.query.filter_by(
                entity_id=current_id,
                entity_type=entity_type
            ).first()
            
            if link:
                chain.append(link.to_dict())
                current_id = link.was_derived_from
                depth += 1
            else:
                break
        
        return chain
    
    def __repr__(self):
        return f'<ProvenanceChain {self.entity_type}:{str(self.entity_id)[:8]}>'