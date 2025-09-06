from datetime import datetime
from app import db
import json

class ExperimentDocument(db.Model):
    """Model for storing experiment-specific document processing data"""
    
    __tablename__ = 'experiment_documents_v2'  # Avoid conflicts with association table
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Foreign keys
    experiment_id = db.Column(db.Integer, db.ForeignKey('experiments.id'), nullable=False, index=True)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=False, index=True)
    
    # Experiment-specific processing status
    processing_status = db.Column(db.String(50), default='pending', nullable=False)
    # Status: 'pending', 'processing', 'completed', 'error'
    
    # Experiment-specific embedding configuration
    embedding_model = db.Column(db.String(100))  # e.g., 'bert-base-uncased', 'sentence-transformers/all-MiniLM-L6-v2'
    embedding_dimension = db.Column(db.Integer)
    embeddings_applied = db.Column(db.Boolean, default=False)
    embedding_metadata = db.Column(db.Text)  # JSON with embedding config and stats
    
    # Experiment-specific segmentation
    segmentation_method = db.Column(db.String(50))  # e.g., 'sentence', 'paragraph', 'semantic_chunk'
    segment_size = db.Column(db.Integer)  # Characters or tokens per segment
    segments_created = db.Column(db.Boolean, default=False)
    segmentation_metadata = db.Column(db.Text)  # JSON with segmentation stats
    
    # NLP processing status
    nlp_analysis_completed = db.Column(db.Boolean, default=False)
    nlp_tools_used = db.Column(db.Text)  # JSON array of tools: ['spacy', 'nltk', 'embeddings']
    
    # Processing timestamps
    processing_started_at = db.Column(db.DateTime)
    processing_completed_at = db.Column(db.DateTime)
    embeddings_generated_at = db.Column(db.DateTime)
    segmentation_completed_at = db.Column(db.DateTime)
    
    # Association metadata
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    experiment = db.relationship('Experiment', backref='experiment_documents_v2')
    document = db.relationship('Document', backref='experiment_versions')
    
    # Unique constraint to prevent duplicates
    __table_args__ = (
        db.UniqueConstraint('experiment_id', 'document_id', name='unique_exp_doc'),
    )
    
    @property
    def processing_progress(self):
        """Calculate processing progress as percentage"""
        total_steps = 3  # embeddings, segmentation, nlp_analysis
        completed_steps = sum([
            bool(self.embeddings_applied),
            bool(self.segments_created),
            bool(self.nlp_analysis_completed)
        ])
        return int((completed_steps / total_steps) * 100)
    
    def mark_embeddings_applied(self, embedding_info):
        """Mark embeddings as applied with metadata"""
        self.embeddings_applied = True
        self.embeddings_generated_at = datetime.utcnow()
        self.embedding_model = embedding_info.get('model', 'unknown')
        self.embedding_dimension = embedding_info.get('dimension')
        
        # Store full metadata as JSON
        self.embedding_metadata = json.dumps(embedding_info)
        
        # Update processing status
        if self.processing_status == 'pending':
            self.processing_status = 'processing'
            self.processing_started_at = datetime.utcnow()
        
        self.updated_at = datetime.utcnow()
    
    def mark_segmentation_completed(self, segmentation_info):
        """Mark segmentation as completed with metadata"""
        self.segments_created = True
        self.segmentation_completed_at = datetime.utcnow()
        self.segmentation_method = segmentation_info.get('method', 'unknown')
        self.segment_size = segmentation_info.get('segment_size')
        
        # Store full metadata as JSON
        self.segmentation_metadata = json.dumps(segmentation_info)
        self.updated_at = datetime.utcnow()
    
    def mark_nlp_analysis_completed(self, nlp_tools):
        """Mark NLP analysis as completed"""
        self.nlp_analysis_completed = True
        self.nlp_tools_used = json.dumps(nlp_tools)
        
        # Check if all processing is complete
        if self.embeddings_applied and self.segments_created:
            self.processing_status = 'completed'
            self.processing_completed_at = datetime.utcnow()
        
        self.updated_at = datetime.utcnow()
    
    def get_embedding_metadata(self):
        """Get embedding metadata as dict"""
        if self.embedding_metadata:
            try:
                return json.loads(self.embedding_metadata)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def get_segmentation_metadata(self):
        """Get segmentation metadata as dict"""
        if self.segmentation_metadata:
            try:
                return json.loads(self.segmentation_metadata)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def get_nlp_tools(self):
        """Get NLP tools as list"""
        if self.nlp_tools_used:
            try:
                return json.loads(self.nlp_tools_used)
            except json.JSONDecodeError:
                return []
        return []
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'experiment_id': self.experiment_id,
            'document_id': self.document_id,
            'processing_status': self.processing_status,
            'processing_progress': self.processing_progress,
            'embedding_model': self.embedding_model,
            'embeddings_applied': self.embeddings_applied,
            'segments_created': self.segments_created,
            'nlp_analysis_completed': self.nlp_analysis_completed,
            'segmentation_method': self.segmentation_method,
            'nlp_tools_used': self.get_nlp_tools(),
            'added_at': self.added_at.isoformat() if self.added_at else None,
            'processing_started_at': self.processing_started_at.isoformat() if self.processing_started_at else None,
            'processing_completed_at': self.processing_completed_at.isoformat() if self.processing_completed_at else None
        }
    
    def __repr__(self):
        return f'<ExperimentDocument exp:{self.experiment_id} doc:{self.document_id} status:{self.processing_status}>'