from sqlalchemy import text
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from app import db
from app.models.document import Document

# Association table for many-to-many relationship between experiments and documents
experiment_documents = db.Table('experiment_documents',
    db.Column('experiment_id', db.Integer, db.ForeignKey('experiments.id'), primary_key=True),
    db.Column('document_id', db.Integer, db.ForeignKey('documents.id'), primary_key=True),
    db.Column('added_at', db.DateTime, default=datetime.utcnow)
)

# Association table for many-to-many relationship between experiments and references
experiment_references = db.Table('experiment_references',
    db.Column('experiment_id', db.Integer, db.ForeignKey('experiments.id'), primary_key=True),
    db.Column('reference_id', db.Integer, db.ForeignKey('documents.id'), primary_key=True),
    db.Column('include_in_analysis', db.Boolean, default=False),
    db.Column('added_at', db.DateTime, default=datetime.utcnow),
    db.Column('notes', db.Text)
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
    # Valid types: 'entity_extraction', 'temporal_analysis', 'temporal_evolution', 'semantic_drift', 'domain_comparison'
    
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
    term_id = db.Column(UUID(as_uuid=True), db.ForeignKey('terms.id'), nullable=True, index=True)  # Required for new experiments
    
    # Relationships
    user = db.relationship('User', backref='user_experiments')
    term = db.relationship('Term', backref='experiments')
    documents = db.relationship('Document', secondary=experiment_documents,
                              backref=db.backref('experiments', lazy='dynamic'),
                              lazy='dynamic')
    
    references = db.relationship('Document', secondary=experiment_references,
                                backref=db.backref('referenced_by_experiments', lazy='dynamic'),
                                lazy='dynamic',
                                primaryjoin='Experiment.id==experiment_references.c.experiment_id',
                                secondaryjoin='and_(Document.id==experiment_references.c.reference_id, Document.document_type=="reference")')
    
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def add_document(self, document):
        """Add a document to the experiment with versioned processing support"""
        if not self.is_document_in_experiment(document):
            # Add to the traditional many-to-many relationship
            self.documents.append(document)
            
            # Also create an ExperimentDocument for processing tracking
            from app.models.experiment_document import ExperimentDocument
            exp_doc = ExperimentDocument(
                experiment_id=self.id,
                document_id=document.id,
                processing_status='pending'
            )
            db.session.add(exp_doc)
    
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
    
    def add_reference(self, reference, include_in_analysis=False, notes=None):
        """Add a reference to the experiment"""
        if not self.is_reference_in_experiment(reference):
            # Use raw SQL to insert with additional fields
            stmt = experiment_references.insert().values(
                experiment_id=self.id,
                reference_id=reference.id,
                include_in_analysis=include_in_analysis,
                notes=notes
            )
            db.session.execute(stmt)
            db.session.commit()
    
    def remove_reference(self, reference):
        """Remove a reference from the experiment"""
        if self.is_reference_in_experiment(reference):
            stmt = experiment_references.delete().where(
                (experiment_references.c.experiment_id == self.id) &
                (experiment_references.c.reference_id == reference.id)
            )
            db.session.execute(stmt)
            db.session.commit()
    
    def is_reference_in_experiment(self, reference):
        """Check if a reference is already in the experiment"""
        return self.references.filter(experiment_references.c.reference_id == reference.id).count() > 0
    
    def get_reference_count(self):
        """Get the number of references in the experiment"""
        return self.references.count()
    
    def get_included_references(self):
        """Get references that are included in analysis"""
        stmt = db.select(experiment_references).where(
            (experiment_references.c.experiment_id == self.id) &
            (experiment_references.c.include_in_analysis == True)
        )
        result = db.session.execute(stmt)
        reference_ids = [row.reference_id for row in result]
        return Document.query.filter(Document.id.in_(reference_ids)).all() if reference_ids else []
    
    def update_reference_inclusion(self, reference_id, include_in_analysis):
        """Update whether a reference is included in analysis"""
        stmt = experiment_references.update().where(
            (experiment_references.c.experiment_id == self.id) &
            (experiment_references.c.reference_id == reference_id)
        ).values(include_in_analysis=include_in_analysis)
        db.session.execute(stmt)
        db.session.commit()
    
    def can_run(self):
        """Check if experiment can be run"""
        if self.status not in ['draft', 'completed', 'error']:
            return False
        # For domain comparison, allow running if there are references
        if self.experiment_type == 'domain_comparison':
            return self.get_reference_count() > 0
        # Default: require documents
        return self.get_document_count() > 0
    
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
