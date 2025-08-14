from sqlalchemy import text
from datetime import datetime
import os
from app import db

class Document(db.Model):
    """Model for storing uploaded files and pasted text content"""
    
    __tablename__ = 'documents'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Document metadata
    title = db.Column(db.String(200), nullable=False)
    content_type = db.Column(db.String(20), nullable=False)  # 'file' or 'text'
    document_type = db.Column(db.String(20), default='document', nullable=False)  # 'document' or 'reference'
    reference_subtype = db.Column(db.String(30))  # For references: 'academic', 'standard', 'book', 'patent', etc.
    file_type = db.Column(db.String(10))  # 'txt', 'pdf', 'docx', etc. (for files)
    original_filename = db.Column(db.String(255))
    file_path = db.Column(db.String(500))  # Path to stored file
    file_size = db.Column(db.Integer)  # Size in bytes
    
    # Source metadata for references (JSON field)
    source_metadata = db.Column(db.JSON)
    # Expected fields in source_metadata:
    # - authors: list of author names
    # - publication_date: date of publication
    # - journal: journal or publisher name
    # - doi: Digital Object Identifier
    # - isbn: ISBN for books
    # - url: source URL
    # - abstract: paper abstract
    # - citation: formatted citation
    
    # Text content (for pasted text or extracted from files)
    content = db.Column(db.Text)
    content_preview = db.Column(db.Text)  # First 500 characters for display
    
    # Language detection
    detected_language = db.Column(db.String(10))
    language_confidence = db.Column(db.Float)
    
    # Processing status
    status = db.Column(db.String(20), default='uploaded', nullable=False)
    # Status values: 'uploaded', 'processing', 'completed', 'error'
    
    # Metadata
    word_count = db.Column(db.Integer)
    character_count = db.Column(db.Integer)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    processed_at = db.Column(db.DateTime)
    
    # Foreign keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    # Parent document (used for grouping sense-level dictionary entries under a master headword)
    parent_document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), index=True)
    
    # Relationships
    processing_jobs = db.relationship('ProcessingJob', backref='document', lazy='dynamic', cascade='all, delete-orphan')
    # Child documents (e.g., individual OED senses)
    children = db.relationship('Document', backref=db.backref('parent', remote_side=[id]), lazy='dynamic', cascade='all')
    text_segments = db.relationship('TextSegment', backref='document', lazy='dynamic', cascade='all, delete-orphan')
    
    # Embedding storage for RAG
    embedding = db.Column(db.String)  # JSON serialized embedding vector
    
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        
        # Auto-generate content preview
        if self.content and not self.content_preview:
            self.content_preview = self.content[:500] + ('...' if len(self.content) > 500 else '')
        
        # Calculate word and character counts
        if self.content:
            self.character_count = len(self.content)
            self.word_count = len(self.content.split())
    
    def get_file_extension(self):
        """Get file extension from original filename"""
        if self.original_filename:
            return os.path.splitext(self.original_filename)[1].lower().lstrip('.')
        return None
    
    def is_text_file(self):
        """Check if document is a text file (not binary)"""
        text_extensions = {'txt', 'md', 'html', 'htm', 'json', 'xml', 'csv'}
        return self.get_file_extension() in text_extensions
    
    def get_display_name(self):
        """Get display name for the document"""
        if self.content_type == 'file' and self.original_filename:
            return self.original_filename
        return self.title
    
    def delete_file(self):
        """Delete the associated file from disk"""
        if self.file_path and os.path.exists(self.file_path):
            try:
                os.remove(self.file_path)
                return True
            except OSError:
                return False
        return True
    
    def get_content_summary(self):
        """Get a brief summary of the content"""
        if not self.content:
            return "No content available"
        
        lines = self.content.split('\n')
        non_empty_lines = [line.strip() for line in lines if line.strip()]
        
        if not non_empty_lines:
            return "Empty document"
        
        if len(non_empty_lines) == 1:
            return non_empty_lines[0][:100] + ('...' if len(non_empty_lines[0]) > 100 else '')
        
        return f"First line: {non_empty_lines[0][:80]}..." if len(non_empty_lines[0]) > 80 else non_empty_lines[0]
    
    def is_reference(self):
        """Check if this document is a reference"""
        return self.document_type == 'reference'
    
    def get_reference_subtype_display(self):
        """Get human-readable reference subtype"""
        subtype_map = {
            'academic': 'Academic Paper',
            'standard': 'Standard/Specification',
            'book': 'Book',
            'patent': 'Patent',
            'conference': 'Conference Proceeding',
            'technical': 'Technical Report',
            'whitepaper': 'White Paper',
            'website': 'Web Resource',
            'dictionary_oed': 'OED Dictionary Entry',
            'dictionary_general': 'Dictionary Entry',
            'glossary': 'Glossary/Terminology',
            'encyclopedia': 'Encyclopedia Entry',
            'other': 'Other Reference'
        }
        return subtype_map.get(self.reference_subtype, 'Reference')
    
    def get_source_info(self):
        """Get formatted source information for references"""
        if not self.source_metadata:
            return None
        
        meta = self.source_metadata
        parts = []
        
        if meta.get('authors'):
            authors = meta['authors']
            if isinstance(authors, list):
                authors_str = ', '.join(authors[:3])
                if len(authors) > 3:
                    authors_str += ' et al.'
                parts.append(authors_str)
        
        if meta.get('publication_date'):
            parts.append(f"({meta['publication_date']})")
        
        if meta.get('journal'):
            parts.append(meta['journal'])
        
        return ' '.join(parts) if parts else None
    
    def get_citation(self):
        """Get formatted citation for references"""
        if self.source_metadata and self.source_metadata.get('citation'):
            return self.source_metadata['citation']
        
        # Generate basic citation if not provided
        source_info = self.get_source_info()
        if source_info:
            return f"{source_info}. {self.title}"
        return self.title
    
    def to_dict(self, include_content=False):
        """Convert document to dictionary for API responses"""
        result = {
            'id': self.id,
            'title': self.title,
            'content_type': self.content_type,
            'document_type': self.document_type,
            'reference_subtype': self.reference_subtype,
            'file_type': self.file_type,
            'original_filename': self.original_filename,
            'file_size': self.file_size,
            'detected_language': self.detected_language,
            'language_confidence': self.language_confidence,
            'status': self.status,
            'word_count': self.word_count,
            'character_count': self.character_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
            'content_preview': self.content_preview,
            'display_name': self.get_display_name(),
            'content_summary': self.get_content_summary()
        }
        
        # Add reference-specific fields
        if self.document_type == 'reference':
            result['source_metadata'] = self.source_metadata
            result['source_info'] = self.get_source_info()
            result['citation'] = self.get_citation()
            result['reference_subtype_display'] = self.get_reference_subtype_display()
        
        if include_content:
            result['content'] = self.content
        
        return result
    
    def __repr__(self):
        return f'<Document {self.id}: {self.get_display_name()}>'
