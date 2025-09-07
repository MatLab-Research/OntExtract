from datetime import datetime
from sqlalchemy import text, and_
from app import db
from app.models.document import Document
from app.models.processing_job import ProcessingJob


class CompositeSource(db.Model):
    """Links composite documents to their constituent source documents"""
    
    __tablename__ = 'composite_sources'
    
    id = db.Column(db.Integer, primary_key=True)
    composite_document_id = db.Column(db.Integer, db.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False)
    source_document_id = db.Column(db.Integer, db.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False)
    processing_priority = db.Column(db.Integer, default=1)
    included_processing_types = db.Column(db.JSON)  # List of processing types to include from this source
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    composite_document = db.relationship('Document', foreign_keys=[composite_document_id], backref='composite_sources')
    source_document = db.relationship('Document', foreign_keys=[source_document_id], backref='used_in_composites')


class DocumentProcessingSummary(db.Model):
    """Efficient summary of processing capabilities available per document"""
    
    __tablename__ = 'document_processing_summary'
    
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False)
    processing_type = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='available')  # 'available', 'processing', 'failed'
    source_document_id = db.Column(db.Integer, db.ForeignKey('documents.id'))
    job_id = db.Column(db.Integer, db.ForeignKey('processing_jobs.id'))
    priority = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    document = db.relationship('Document', foreign_keys=[document_id], backref='processing_summary')
    source_document = db.relationship('Document', foreign_keys=[source_document_id])
    processing_job = db.relationship('ProcessingJob', backref='summary_entries')


class CompositeDocumentMixin:
    """Mixin to add composite document capabilities to Document model"""
    
    def is_composite(self):
        """Check if this document is a composite document"""
        return hasattr(self, 'version_type') and self.version_type == 'composite'
    
    def get_composite_sources(self):
        """Get all source documents that contribute to this composite"""
        if not self.is_composite():
            return []
        
        return db.session.query(Document)\
            .join(CompositeSource, CompositeSource.source_document_id == Document.id)\
            .filter(CompositeSource.composite_document_id == self.id)\
            .order_by(CompositeSource.processing_priority.desc())\
            .all()
    
    def get_available_processing(self):
        """Get all processing types available on this document (direct or via composite sources)"""
        if self.is_composite():
            # For composite documents, aggregate from all sources
            summary_entries = DocumentProcessingSummary.query\
                .filter(DocumentProcessingSummary.document_id == self.id)\
                .filter(DocumentProcessingSummary.status == 'available')\
                .all()
            return {entry.processing_type: entry for entry in summary_entries}
        else:
            # For regular documents, get from processing jobs
            processing_types = {}
            for job in self.processing_jobs.filter(ProcessingJob.status == 'completed'):
                processing_types[job.job_type] = job
            return processing_types
    
    def has_processing(self, processing_type):
        """Check if a specific processing type is available"""
        return processing_type in self.get_available_processing()
    
    def get_processing_source(self, processing_type):
        """Get the source document that provides a specific processing type"""
        if self.is_composite():
            summary = DocumentProcessingSummary.query\
                .filter(and_(
                    DocumentProcessingSummary.document_id == self.id,
                    DocumentProcessingSummary.processing_type == processing_type,
                    DocumentProcessingSummary.status == 'available'
                ))\
                .order_by(DocumentProcessingSummary.priority.desc())\
                .first()
            
            return summary.source_document if summary else None
        else:
            return self if self.has_processing(processing_type) else None
    
    @classmethod
    def create_composite(cls, title, source_documents, strategy='all_processing', user_id=None):
        """Create a new composite document from multiple source documents"""
        
        # Create the composite document
        composite_doc = Document(
            title=f"{title} (Composite)",
            content_type='text',
            content="", # Composite documents don't have their own content
            version_type='composite',
            status='completed',
            user_id=user_id or source_documents[0].user_id,
            processing_notes=f"Composite document created from {len(source_documents)} source documents with {strategy} strategy"
        )
        
        db.session.add(composite_doc)
        db.session.flush()  # Get the ID
        
        # Link source documents
        all_processing_types = set()
        for i, source_doc in enumerate(source_documents, 1):
            # Create composite source relationship
            composite_source = CompositeSource(
                composite_document_id=composite_doc.id,
                source_document_id=source_doc.id,
                processing_priority=len(source_documents) - i  # Later documents have higher priority
            )
            db.session.add(composite_source)
            
            # Add processing summary entries
            for job in source_doc.processing_jobs.filter(ProcessingJob.status == 'completed'):
                if strategy == 'all_processing' or job.job_type not in all_processing_types:
                    summary = DocumentProcessingSummary(
                        document_id=composite_doc.id,
                        processing_type=job.job_type,
                        status='available',
                        source_document_id=source_doc.id,
                        job_id=job.id,
                        priority=composite_source.processing_priority
                    )
                    db.session.add(summary)
                    all_processing_types.add(job.job_type)
        
        db.session.commit()
        return composite_doc
    
    def update_composite_processing(self):
        """Update the processing summary for this composite document"""
        if not self.is_composite():
            return
        
        # Clear existing processing summary
        DocumentProcessingSummary.query.filter(
            DocumentProcessingSummary.document_id == self.id
        ).delete()
        
        # Rebuild from current source documents
        sources = self.get_composite_sources()
        all_processing_types = set()
        
        for source_doc in sources:
            for job in source_doc.processing_jobs.filter(ProcessingJob.status == 'completed'):
                if job.job_type not in all_processing_types:
                    # Find the composite source for priority
                    composite_source = CompositeSource.query.filter(and_(
                        CompositeSource.composite_document_id == self.id,
                        CompositeSource.source_document_id == source_doc.id
                    )).first()
                    
                    summary = DocumentProcessingSummary(
                        document_id=self.id,
                        processing_type=job.job_type,
                        status='available',
                        source_document_id=source_doc.id,
                        job_id=job.id,
                        priority=composite_source.processing_priority if composite_source else 1
                    )
                    db.session.add(summary)
                    all_processing_types.add(job.job_type)
        
        db.session.commit()


# Extend the Document model with composite capabilities
# This would be mixed into the Document class
Document.is_composite = CompositeDocumentMixin.is_composite
Document.get_composite_sources = CompositeDocumentMixin.get_composite_sources
Document.get_available_processing = CompositeDocumentMixin.get_available_processing
Document.has_processing = CompositeDocumentMixin.has_processing
Document.get_processing_source = CompositeDocumentMixin.get_processing_source
Document.create_composite = CompositeDocumentMixin.create_composite
Document.update_composite_processing = CompositeDocumentMixin.update_composite_processing