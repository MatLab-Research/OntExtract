from sqlalchemy import text
from datetime import datetime
from app import db


class ProvenanceEntity(db.Model):
    """
    PROV-O Entity model representing first-class provenance entities
    Implements prov:Entity with OntExtract-specific extensions
    """
    
    __tablename__ = 'provenance_entities'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # PROV-O Core Properties
    prov_id = db.Column(db.String(255), unique=True, nullable=False, index=True)  # prov:Entity identifier
    prov_type = db.Column(db.String(100), nullable=False)  # ont:Document, ont:ProcessedDocument, etc.
    prov_label = db.Column(db.String(500))  # Human-readable label
    generated_at_time = db.Column(db.DateTime, default=datetime.utcnow)  # prov:generatedAtTime
    invalidated_at_time = db.Column(db.DateTime)  # prov:invalidatedAtTime
    
    # Attribution and Agency
    attributed_to_agent = db.Column(db.String(255))  # prov:wasAttributedTo
    
    # Derivation relationships
    derived_from_entity = db.Column(db.String(255), index=True)  # prov:wasDerivedFrom
    
    # Activity relationships  
    generated_by_activity = db.Column(db.String(255), index=True)  # prov:wasGeneratedBy
    
    # OntExtract-specific properties
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), index=True)
    experiment_id = db.Column(db.Integer, db.ForeignKey('experiments.id'), index=True)
    version_number = db.Column(db.Integer)
    version_type = db.Column(db.String(50))  # original, processed, experimental
    
    # JSON metadata for additional PROV-O properties
    prov_metadata = db.Column(db.JSON)  # Store additional prov properties
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    document = db.relationship('Document', backref='provenance_entities')
    experiment = db.relationship('Experiment', backref='provenance_entities')
    
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    @classmethod
    def create_for_document(cls, document, activity_type='upload', agent=None):
        """Create a provenance entity for a document"""
        prov_id = f"document_{document.id}"
        if hasattr(document, 'version_number') and document.version_number > 1:
            prov_id = f"document_{document.id}_v{document.version_number}"
            
        return cls(
            prov_id=prov_id,
            prov_type='ont:Document',
            prov_label=document.title,
            attributed_to_agent=agent or f"user_{document.user_id}",
            document_id=document.id,
            version_number=getattr(document, 'version_number', 1),
            version_type=getattr(document, 'version_type', 'original'),
            generated_by_activity=activity_type,
            prov_metadata={
                'content_type': document.content_type,
                'file_type': document.file_type,
                'language': document.detected_language,
                'word_count': document.word_count
            }
        )
    
    @classmethod
    def create_derivation(cls, source_document, derived_document, activity, agent=None):
        """Create a derivation relationship between documents"""
        derived_entity = cls.create_for_document(derived_document, activity, agent)
        derived_entity.derived_from_entity = f"document_{source_document.id}"
        
        if hasattr(derived_document, 'experiment_id') and derived_document.experiment_id:
            derived_entity.experiment_id = derived_document.experiment_id
            derived_entity.prov_type = 'ont:ExperimentalDocument'
            
        return derived_entity
    
    def get_prov_o_dict(self):
        """Return PROV-O dictionary representation"""
        prov_dict = {
            'prov:Entity': self.prov_id,
            'prov:type': self.prov_type,
            'prov:label': self.prov_label,
            'prov:generatedAtTime': self.generated_at_time.isoformat() if self.generated_at_time else None,
            'prov:wasAttributedTo': self.attributed_to_agent
        }
        
        if self.derived_from_entity:
            prov_dict['prov:wasDerivedFrom'] = self.derived_from_entity
            
        if self.generated_by_activity:
            prov_dict['prov:wasGeneratedBy'] = self.generated_by_activity
            
        if self.invalidated_at_time:
            prov_dict['prov:invalidatedAtTime'] = self.invalidated_at_time.isoformat()
            
        # Add OntExtract-specific properties
        if self.version_number:
            prov_dict['ont:versionNumber'] = self.version_number
        if self.version_type:
            prov_dict['ont:versionType'] = self.version_type
            
        # Merge additional metadata
        if self.prov_metadata:
            prov_dict.update(self.prov_metadata)
            
        return prov_dict
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'prov_id': self.prov_id,
            'prov_type': self.prov_type,
            'prov_label': self.prov_label,
            'generated_at_time': self.generated_at_time.isoformat() if self.generated_at_time else None,
            'attributed_to_agent': self.attributed_to_agent,
            'derived_from_entity': self.derived_from_entity,
            'generated_by_activity': self.generated_by_activity,
            'document_id': self.document_id,
            'experiment_id': self.experiment_id,
            'version_number': self.version_number,
            'version_type': self.version_type,
            'prov_metadata': self.prov_metadata,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<ProvenanceEntity {self.prov_id}: {self.prov_type}>'


class ProvenanceActivity(db.Model):
    """
    PROV-O Activity model representing processing activities
    Implements prov:Activity for document processing operations
    """
    
    __tablename__ = 'provenance_activities'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # PROV-O Core Properties
    prov_id = db.Column(db.String(255), unique=True, nullable=False, index=True)  # prov:Activity identifier
    prov_type = db.Column(db.String(100), nullable=False)  # ont:Processing, ont:Segmentation, etc.
    prov_label = db.Column(db.String(500))  # Human-readable label
    started_at_time = db.Column(db.DateTime, default=datetime.utcnow)  # prov:startedAtTime
    ended_at_time = db.Column(db.DateTime)  # prov:endedAtTime
    
    # Association with agents and plans
    was_associated_with = db.Column(db.String(255))  # prov:wasAssociatedWith (agent)
    used_plan = db.Column(db.String(255))  # prov:used (plan/protocol)
    
    # OntExtract-specific properties
    processing_job_id = db.Column(db.Integer, db.ForeignKey('processing_jobs.id'), index=True)
    experiment_id = db.Column(db.Integer, db.ForeignKey('experiments.id'), index=True)
    activity_type = db.Column(db.String(50))  # embeddings, segmentation, langextract, etc.
    
    # JSON metadata for parameters and results
    activity_metadata = db.Column(db.JSON)  # Store processing parameters and results
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    processing_job = db.relationship('ProcessingJob', backref='provenance_activity')
    experiment = db.relationship('Experiment', backref='provenance_activities')
    
    @classmethod
    def create_for_processing(cls, processing_job, agent=None):
        """Create a provenance activity for a processing job"""
        prov_id = f"activity_{processing_job.job_type}_{processing_job.id}"
        
        return cls(
            prov_id=prov_id,
            prov_type=f'ont:{processing_job.job_type.title()}Processing',
            prov_label=f"{processing_job.job_type} processing of document {processing_job.document_id}",
            was_associated_with=agent or f"user_{processing_job.user_id}",
            processing_job_id=processing_job.id,
            activity_type=processing_job.job_type,
            activity_metadata={
                'parameters': processing_job.get_parameters(),
                'status': processing_job.status,
                'processing_time': processing_job.processing_time
            }
        )
    
    def complete_activity(self, results=None):
        """Mark activity as completed with results"""
        self.ended_at_time = datetime.utcnow()
        if results:
            if not self.activity_metadata:
                self.activity_metadata = {}
            self.activity_metadata['results'] = results
    
    def get_prov_o_dict(self):
        """Return PROV-O dictionary representation"""
        prov_dict = {
            'prov:Activity': self.prov_id,
            'prov:type': self.prov_type,
            'prov:label': self.prov_label,
            'prov:startedAtTime': self.started_at_time.isoformat() if self.started_at_time else None,
            'prov:wasAssociatedWith': self.was_associated_with
        }
        
        if self.ended_at_time:
            prov_dict['prov:endedAtTime'] = self.ended_at_time.isoformat()
            
        if self.used_plan:
            prov_dict['prov:used'] = self.used_plan
            
        # Add OntExtract-specific properties
        if self.activity_type:
            prov_dict['ont:activityType'] = self.activity_type
            
        # Merge additional metadata
        if self.activity_metadata:
            prov_dict.update({'ont:' + k: v for k, v in self.activity_metadata.items()})
            
        return prov_dict
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'prov_id': self.prov_id,
            'prov_type': self.prov_type,
            'prov_label': self.prov_label,
            'started_at_time': self.started_at_time.isoformat() if self.started_at_time else None,
            'ended_at_time': self.ended_at_time.isoformat() if self.ended_at_time else None,
            'was_associated_with': self.was_associated_with,
            'used_plan': self.used_plan,
            'processing_job_id': self.processing_job_id,
            'experiment_id': self.experiment_id,
            'activity_type': self.activity_type,
            'activity_metadata': self.activity_metadata,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<ProvenanceActivity {self.prov_id}: {self.prov_type}>'