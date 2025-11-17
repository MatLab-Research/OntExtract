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
        Creates a new, isolated "Processed Version" of a document for a specific analysis type.
        This version links back to the source document but does NOT inherit any prior processing.
        
        Args:
            original_document: The document being processed.
            processing_type: A string describing the analysis (e.g., 'sentence_segmentation', 'paragraph_segmentation').
            processing_metadata: Additional metadata about the processing run.
            
        Returns:
            new_document: The new, isolated Processed Version document.
        """
        try:
            # 1. Find the absolute root document (the original source).
            source_document = original_document.get_root_document()
            
            # 2. Determine the next version number in the family.
            latest_version_in_family = InheritanceVersioningService._get_latest_version(source_document.id)
            new_version_number = (latest_version_in_family.version_number if latest_version_in_family else 0) + 1
            
            # 3. Create the new document object. It's based on the SOURCE content.
            # IMPORTANT: Keep the original title - display version info via badges, not in title
            new_document = Document(
                title=source_document.title,  # Keep original title clean
                content_type=source_document.content_type,
                document_type=source_document.document_type,
                reference_subtype=source_document.reference_subtype,
                file_type=source_document.file_type,
                content=source_document.content,  # CRITICAL: Always use original content
                content_preview=source_document.content_preview,
                detected_language=source_document.detected_language,
                language_confidence=source_document.language_confidence,
                status='active',
                word_count=source_document.word_count,
                character_count=source_document.character_count,
                user_id=source_document.user_id,
                version_number=new_version_number,
                version_type='processed', # This is a processed version
                source_document_id=source_document.id, # CRITICAL: Link back to the root
                processing_metadata=processing_metadata or {'type': processing_type}
            )
            
            db.session.add(new_document)
            db.session.flush()  # Get the ID

            # Copy metadata from source document
            if source_document.source_metadata:
                new_document.source_metadata = source_document.source_metadata

            # Copy temporal metadata from source document
            from app.models import DocumentTemporalMetadata
            source_temporal = DocumentTemporalMetadata.query.filter_by(
                document_id=source_document.id
            ).first()

            if source_temporal:
                new_temporal = DocumentTemporalMetadata(
                    document_id=new_document.id,
                    publication_year=source_temporal.publication_year,
                    discipline=source_temporal.discipline,
                    key_definition=source_temporal.key_definition,
                    created_at=datetime.utcnow()
                )
                db.session.add(new_temporal)
                logger.info(f"Copied temporal metadata from document {source_document.id} to {new_document.id}")

            # CRITICAL CHANGE: Do NOT inherit processing data from the previous version.
            # Each processed version is clean and only contains its own analysis.
            
            # Record what's being added in this version
            InheritanceVersioningService._record_version_change(
                new_document.id,
                new_version_number,
                processing_type,
                f"Created isolated processed version with {processing_type}",
                source_document.version_number,
                source_document.user_id,
                processing_metadata
            )
            
            db.session.commit()
            
            logger.info(f"Created new ISOLATED document version {new_version_number} (ID: {new_document.id}) "
                       f"from source {source_document.id} for processing: {processing_type}")
            
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