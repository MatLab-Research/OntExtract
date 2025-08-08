from sqlalchemy import text
from datetime import datetime
from app import db

# Association table for many-to-many relationship between experiments and documents
experiment_documents = db.Table('experiment_documents',
    db.Column('experiment_id', db.Integer, db.ForeignKey('experiments.id'), primary_key=True),
    db.Column('document_id', db.Integer, db.ForeignKey('documents.id'), primary_key=True),
    db.Column('added_at', db.DateTime, default=datetime.utcnow)
)

class Experiment(db.Model):
    """Model for storing experiment configurations and results"""
    
    __tablename__ = 'experiments'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Experiment metadata
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    
    # Experiment type
    experiment_type = db.Column(db.String(50), nullable=False)
    # Types: 'temporal_evolution', 'domain_comparison'
    
    # Configuration (JSON stored as string)
    configuration = db.Column(db.Text)  # JSON for storing experiment-specific settings
    
    # Processing status
    status = db.Column(db.String(20), default='draft', nullable=False)
    # Status values: 'draft', 'running', 'completed', 'error'
    
    # Results storage
    results = db.Column(db.Text)  # JSON for storing analysis results
    results_summary = db.Column(db.Text)  # Human-readable summary
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    
    # Foreign keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Relationships
    documents = db.relationship('Document', secondary=experiment_documents, 
                              backref=db.backref('experiments', lazy='dynamic'),
                              lazy='dynamic')
    
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def add_document(self, document):
        """Add a document to the experiment"""
        if not self.is_document_in_experiment(document):
            self.documents.append(document)
    
    def remove_document(self, document):
        """Remove a document from the experiment"""
        if self.is_document_in_experiment(document):
            self.documents.remove(document)
    
    def is_document_in_experiment(self, document):
        """Check if a document is already in the experiment"""
        return self.documents.filter(experiment_documents.c.document_id == document.id).count() > 0
    
    def get_document_count(self):
        """Get the number of documents in the experiment"""
        return self.documents.count()
    
    def get_total_word_count(self):
        """Get total word count across all documents"""
        total = 0
        for doc in self.documents:
            if doc.word_count:
                total += doc.word_count
        return total
    
    def can_run(self):
        """Check if experiment can be run"""
        return self.get_document_count() > 0 and self.status in ['draft', 'completed', 'error']
    
    def to_dict(self, include_documents=False):
        """Convert experiment to dictionary for API responses"""
        result = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'experiment_type': self.experiment_type,
            'status': self.status,
            'document_count': self.get_document_count(),
            'total_word_count': self.get_total_word_count(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'can_run': self.can_run()
        }
        
        if include_documents:
            result['documents'] = [doc.to_dict() for doc in self.documents]
        
        if self.results_summary:
            result['results_summary'] = self.results_summary
        
        return result
    
    def __repr__(self):
        return f'<Experiment {self.id}: {self.name}>'
