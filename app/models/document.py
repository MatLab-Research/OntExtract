from sqlalchemy import text
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import os
import uuid as uuid_lib
from app import db

class Document(db.Model):
    """Model for storing uploaded files and pasted text content"""

    __tablename__ = 'documents'

    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid_lib.uuid4, index=True)

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
    processing_metadata = db.Column(db.JSON)  # General metadata for processing info, embeddings, etc.
    metadata_provenance = db.Column(db.JSON)  # Tracks source/confidence for each metadata field
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    processed_at = db.Column(db.DateTime)
    
    # Versioning fields for unified processing interface
    # Note: These will fail until migration is run, but methods below provide fallbacks
    version_number = db.Column(db.Integer, default=1, nullable=False)
    version_type = db.Column(db.String(20), default='original', nullable=False)  # 'original', 'processed', 'experimental', 'composite'
    source_document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), index=True)  # Original document this version derives from
    experiment_id = db.Column(db.Integer, db.ForeignKey('experiments.id'), index=True)  # Associated experiment (for experimental versions)
    processing_notes = db.Column(db.Text)  # Notes about processing operations that created this version
    
    # Composite versioning fields
    composite_sources = db.Column(db.JSON)  # List of document IDs that contribute to this composite
    composite_metadata = db.Column(db.JSON)  # Metadata about how the composite was created

    # Foreign keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    # Parent document (used for grouping sense-level dictionary entries under a master headword)
    parent_document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), index=True)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('user_documents', overlaps="owner"), overlaps="documents,owner")
    processing_jobs = db.relationship('ProcessingJob', backref='document', lazy='dynamic', cascade='all, delete-orphan')
    
    # Document versioning relationships
    versions = db.relationship('Document', 
                              foreign_keys=[source_document_id],
                              backref=db.backref('source_document', remote_side=[id]), 
                              lazy='dynamic', 
                              cascade='all')
    experiment = db.relationship('Experiment', backref='experimental_documents')
    
    # Child documents (e.g., individual OED senses) - separate from versioning
    children = db.relationship('Document', 
                              foreign_keys=[parent_document_id],
                              backref=db.backref('parent', remote_side=[id]), 
                              lazy='dynamic', 
                              cascade='all')
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

    def get_bibliographic_metadata(self):
        """
        Get bibliographic metadata (source_metadata) for this document.

        For versioned documents, retrieves metadata from the root document
        since bibliographic information belongs to the scholarly work, not the version.

        Returns:
            dict: source_metadata from root document, or this document's metadata if it's the root
        """
        root_doc = self.get_root_document()
        return root_doc.source_metadata if root_doc.source_metadata else {}

    def get_metadata_provenance(self):
        """
        Get metadata provenance for this document.

        Like bibliographic metadata, provenance is stored on the root document.

        Returns:
            dict: metadata_provenance from root document
        """
        root_doc = self.get_root_document()
        return root_doc.metadata_provenance if root_doc.metadata_provenance else {}

    def get_all_experiment_associations(self):
        """
        Get all experiments associated with any version in this document family.

        Returns experiments linked to any document in the version chain, since
        experiments typically analyze the document as a whole, not just one version.

        Returns:
            list: List of (ExperimentDocument, Experiment) tuples
        """
        from app.models.experiment_document import ExperimentDocument
        from app.models.experiment import Experiment

        # Get all document IDs in this family
        root_doc = self.get_root_document()
        all_versions = self.get_all_versions()
        all_doc_ids = [v.id for v in all_versions]

        # Find all experiment associations for any version
        exp_docs = ExperimentDocument.query.filter(
            ExperimentDocument.document_id.in_(all_doc_ids)
        ).all()

        # Return unique experiments (may be linked to multiple versions)
        seen_exp_ids = set()
        unique_exp_docs = []
        for exp_doc in exp_docs:
            if exp_doc.experiment_id not in seen_exp_ids:
                seen_exp_ids.add(exp_doc.experiment_id)
                unique_exp_docs.append(exp_doc)

        return unique_exp_docs

    # Document versioning methods
    
    def create_version(self, version_type='processed', experiment_id=None, processing_notes=None, **kwargs):
        """Create a new version of this document with PROV-O compliant provenance tracking"""
        from datetime import datetime
        import uuid
        
        # Determine the root document
        root_doc = self.get_root_document()
        
        # Get the next version number for this document family
        max_version = db.session.query(db.func.max(Document.version_number))\
            .filter(db.or_(
                Document.source_document_id == root_doc.id,
                Document.id == root_doc.id
            )).scalar() or 0
        
        # Generate PROV-O compliant version identifier
        version_number = max_version + 1
        prov_version_id = f"document_{root_doc.id}_v{version_number}"
        
        # Create PROV-O compliant processing notes with derivation information
        prov_notes = {
            'prov_type': f'prov:Derivation',
            'prov_derived_from': f'document_{self.id}',
            'prov_generated_at': datetime.utcnow().isoformat(),
            'prov_activity': f'{version_type}_processing',
            'prov_agent': f'user_{self.user_id}',
            'processing_method': version_type,
            'original_notes': processing_notes
        }
        
        if experiment_id:
            prov_notes['prov_experiment'] = f'experiment_{experiment_id}'
            prov_notes['prov_plan'] = f'experiment_{experiment_id}_protocol'
        
        # Create new version with PROV-O metadata
        version_data = {
            'title': f"{root_doc.title} (v{version_number})",
            'content_type': self.content_type,
            'content': self.content,
            'detected_language': self.detected_language,
            'language_confidence': self.language_confidence,
            'user_id': self.user_id,
            'source_document_id': root_doc.id,
            'version_number': version_number,
            'version_type': version_type,
            'experiment_id': experiment_id,
            'processing_notes': str(prov_notes),  # Store as JSON string
            'status': 'processing'
        }
        
        # Add PROV-O metadata to processing_metadata
        if not version_data.get('processing_metadata'):
            version_data['processing_metadata'] = {}
        
        version_data['processing_metadata'] = {
            **version_data.get('processing_metadata', {}),
            'prov_o': {
                'entity_id': prov_version_id,
                'derived_from': f'document_{self.id}',
                'generation_time': datetime.utcnow().isoformat(),
                'derivation_type': version_type,
                'responsible_agent': f'user_{self.user_id}',
                'provenance_chain': self._build_provenance_chain()
            }
        }
        
        # Override with any provided kwargs
        version_data.update(kwargs)
        
        new_version = Document(**version_data)
        db.session.add(new_version)
        db.session.flush()  # Get the ID without committing
        
        return new_version
    
    def _build_provenance_chain(self):
        """Build PROV-O compliant provenance chain for this document"""
        chain = []
        current = self
        
        while current:
            chain.append({
                'entity': f'document_{current.id}',
                'version': getattr(current, 'version_number', 1),
                'type': getattr(current, 'version_type', 'original'),
                'created_at': current.created_at.isoformat() if current.created_at else None,
                'agent': f'user_{current.user_id}'
            })
            
            # Navigate to source document
            if hasattr(current, 'source_document_id') and current.source_document_id:
                current = current.source_document
            else:
                break
                
        return list(reversed(chain))  # Return in chronological order
    
    def get_prov_o_metadata(self):
        """Get PROV-O metadata for this document"""
        base_metadata = {
            'prov:Entity': f'document_{self.id}',
            'prov:type': 'ont:Document',
            'prov:label': self.title,
            'prov:generatedAtTime': self.created_at.isoformat() if self.created_at else None,
            'prov:wasAttributedTo': f'user_{self.user_id}'
        }
        
        # Add versioning information if available
        if hasattr(self, 'version_type') and self.version_type:
            base_metadata['ont:versionType'] = self.version_type
            base_metadata['ont:versionNumber'] = getattr(self, 'version_number', 1)
            
        # Add derivation information for non-original documents
        if hasattr(self, 'source_document_id') and self.source_document_id:
            base_metadata['prov:wasDerivedFrom'] = f'document_{self.source_document_id}'
            
        # Add experiment association for experimental versions
        if hasattr(self, 'experiment_id') and self.experiment_id:
            base_metadata['prov:wasGeneratedBy'] = f'experiment_{self.experiment_id}'
            base_metadata['ont:experimentalVersion'] = True
            
        return base_metadata
    
    def get_root_document(self):
        """Get the root document for this version chain"""
        if self.source_document_id:
            return self.source_document
        return self
    
    def get_all_versions(self):
        """Get all versions in this document family"""
        root_doc = self.get_root_document()
        return db.session.query(Document)\
            .filter(db.or_(
                Document.source_document_id == root_doc.id,
                Document.id == root_doc.id
            ))\
            .order_by(Document.version_number)\
            .all()
    
    def get_latest_version(self):
        """Get the latest version in this document family"""
        versions = self.get_all_versions()
        return versions[-1] if versions else self
    
    def is_original(self):
        """Check if this is the original document"""
        return self.version_type == 'original' and self.source_document_id is None
    
    def is_experimental(self):
        """Check if this is an experimental version"""
        return self.version_type == 'experimental' and self.experiment_id is not None
    
    def get_version_display_name(self):
        """Get display name including version information"""
        if self.is_original():
            return self.get_display_name()
        
        version_info = f"v{self.version_number}"
        if self.version_type == 'experimental' and self.experiment:
            version_info += f" ({self.experiment.name})"
        elif self.version_type == 'processed':
            version_info += " (processed)"
        elif self.version_type == 'composite':
            version_info += " (composite)"
            
        return f"{self.get_display_name()} - {version_info}"
    
    # Composite versioning methods
    
    def create_composite_version(self, source_versions, composite_metadata=None):
        """Create a composite version that combines multiple source versions"""
        from datetime import datetime
        
        root_doc = self.get_root_document()
        
        # Get next version number
        max_version = db.session.query(db.func.max(Document.version_number))\
            .filter(db.or_(
                Document.source_document_id == root_doc.id,
                Document.id == root_doc.id
            )).scalar() or 0
        
        version_number = max_version + 1
        
        # Create composite document
        composite_doc = Document(
            title=f"{root_doc.title} (Composite v{version_number})",
            content_type=root_doc.content_type,
            content=root_doc.content,  # Start with original content
            detected_language=root_doc.detected_language,
            language_confidence=root_doc.language_confidence,
            user_id=root_doc.user_id,
            source_document_id=root_doc.id,
            version_number=version_number,
            version_type='composite',
            composite_sources=[v.id for v in source_versions],
            composite_metadata=composite_metadata or {
                'created_at': datetime.utcnow().isoformat(),
                'source_version_ids': [v.id for v in source_versions],
                'source_version_types': [v.version_type for v in source_versions],
                'processing_summary': f"Composite of {len(source_versions)} versions"
            },
            processing_notes=f"Composite version combining {len(source_versions)} processing approaches",
            status='active'
        )
        
        db.session.add(composite_doc)
        db.session.flush()
        
        return composite_doc
    
    def get_composite_sources(self):
        """Get the source documents that contribute to this composite"""
        if not self.composite_sources:
            return []
        
        return db.session.query(Document)\
            .filter(Document.id.in_(self.composite_sources))\
            .all()
    
    def is_composite(self):
        """Check if this is a composite version"""
        return self.version_type == 'composite'
    
    @property
    def has_embeddings(self):
        """Check if document has embeddings applied"""
        if not self.processing_metadata:
            return False
        
        processing_info = self.processing_metadata.get('processing_info', {})
        return processing_info.get('embeddings_applied', False)
    
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
