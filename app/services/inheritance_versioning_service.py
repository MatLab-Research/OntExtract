"""
Inheritance-Based Versioning Service

Replaces the composite document approach with true version inheritance.
Each document version inherits all processing from previous versions and adds new processing.
"""

from app import db
from app.models import Document, TextSegment
from sqlalchemy import text
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

class InheritanceVersioningService:
    """Service for managing document versions with processing inheritance"""
    
    @staticmethod
    def create_new_version(original_document, processing_type, processing_metadata=None):
        """
        Create a new version of a document that inherits all processing from the latest version.
        
        Args:
            original_document: The base document (can be any version)
            processing_type: Type of processing being added (e.g., 'embeddings', 'segments')
            processing_metadata: Additional metadata for this version
            
        Returns:
            new_document: The new document version with inherited processing
        """
        try:
            # Find the base document ID (original document)
            base_document_id = InheritanceVersioningService._get_base_document_id(original_document)
            
            # Find the latest version to inherit from  
            latest_version_doc = InheritanceVersioningService._get_latest_version(base_document_id)
            latest_version_number = latest_version_doc.version_number if latest_version_doc else 0
            
            # Create new document version
            new_version_number = latest_version_number + 1
            new_document = Document(
                title=f"{InheritanceVersioningService._get_base_title(base_document_id)} (v{new_version_number})",
                content_type=original_document.content_type,
                document_type=original_document.document_type,
                reference_subtype=original_document.reference_subtype,
                file_type=original_document.file_type,
                content=original_document.content,  # Always inherit original content
                content_preview=original_document.content_preview,
                detected_language=original_document.detected_language,
                language_confidence=original_document.language_confidence,
                status='active',
                word_count=original_document.word_count,
                character_count=original_document.character_count,
                user_id=original_document.user_id,
                version_number=new_version_number,
                version_type='processed',
                source_document_id=base_document_id,
                processing_metadata=processing_metadata or {}
            )
            
            db.session.add(new_document)
            db.session.flush()  # Get the ID
            
            # Inherit all processing from the latest version if it exists
            if latest_version_doc:
                InheritanceVersioningService._inherit_processing_data(
                    latest_version_doc.id, 
                    new_document.id
                )
            
            # Record what's being added in this version
            InheritanceVersioningService._record_version_change(
                new_document.id,
                new_version_number,
                processing_type,
                f"Added {processing_type} processing to version {new_version_number}",
                latest_version_number if latest_version_doc else None,
                original_document.user_id,
                processing_metadata
            )
            
            db.session.commit()
            
            logger.info(f"Created new document version {new_version_number} (ID: {new_document.id}) "
                       f"inheriting from version {latest_version_number}")
            
            return new_document
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to create new version: {str(e)}")
            raise
    
    @staticmethod
    def _get_base_document_id(document):
        """Get the original base document ID"""
        return document.source_document_id if document.source_document_id else document.id
    
    @staticmethod
    def _get_base_title(base_document_id):
        """Get the title of the base document"""
        base_doc = Document.query.get(base_document_id)
        return base_doc.title if base_doc else "Unknown Document"
    
    @staticmethod
    def _get_latest_version(base_document_id):
        """Get the latest version of a document"""
        return Document.query.filter(
            db.or_(
                Document.id == base_document_id,
                Document.source_document_id == base_document_id
            )
        ).order_by(Document.version_number.desc()).first()
    
    @staticmethod  
    def _inherit_processing_data(source_document_id, target_document_id):
        """Inherit all processing data from source to target document using SQL function"""
        try:
            # Use the SQL function we created in the migration
            db.session.execute(
                text("SELECT inherit_processing_data(:source_id, :target_id)"),
                {
                    'source_id': source_document_id,
                    'target_id': target_document_id
                }
            )
            logger.info(f"Inherited processing data from document {source_document_id} to {target_document_id}")
        except Exception as e:
            logger.error(f"Failed to inherit processing data: {str(e)}")
            raise
    
    @staticmethod
    def _record_version_change(document_id, version_number, change_type, description, 
                              previous_version, user_id, processing_metadata):
        """Record what changed in this version"""
        try:
            db.session.execute(
                text("""
                    INSERT INTO version_changelog 
                    (document_id, version_number, change_type, change_description, 
                     previous_version, created_by, processing_metadata)
                    VALUES (:doc_id, :version, :change_type, :description, 
                            :prev_version, :user_id, :metadata)
                """),
                {
                    'doc_id': document_id,
                    'version': version_number,
                    'change_type': change_type,
                    'description': description,
                    'prev_version': previous_version,
                    'user_id': user_id,
                    'metadata': json.dumps(processing_metadata) if processing_metadata else None
                }
            )
        except Exception as e:
            logger.error(f"Failed to record version change: {str(e)}")
            # Don't raise - this is just logging
    
    @staticmethod
    def get_document_version_history(document_id):
        """Get complete version history for a document"""
        base_document_id = InheritanceVersioningService._get_base_document_id(
            Document.query.get(document_id)
        )
        
        result = db.session.execute(
            text("""
                SELECT * FROM document_version_history 
                WHERE base_document_id = :base_id
                ORDER BY version_number
            """),
            {'base_id': base_document_id}
        )
        
        return [dict(row._mapping) for row in result]
    
    @staticmethod
    def get_version_changes(document_id, version_number):
        """Get what changed in a specific version"""
        result = db.session.execute(
            text("""
                SELECT change_type, change_description, processing_metadata, created_at
                FROM version_changelog 
                WHERE document_id = :doc_id AND version_number = :version
                ORDER BY created_at
            """),
            {'doc_id': document_id, 'version': version_number}
        )
        
        return [dict(row._mapping) for row in result]
    
    @staticmethod
    def redirect_to_latest_version(base_document_id):
        """Get the URL to redirect to the latest version of a document"""
        latest_doc = InheritanceVersioningService._get_latest_version(base_document_id)
        if latest_doc:
            return f'/input/document/{latest_doc.id}'
        else:
            return f'/input/document/{base_document_id}'