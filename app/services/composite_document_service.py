from datetime import datetime
from app import db
from app.models.document import Document
from app.models.composite_document import CompositeSource, DocumentProcessingSummary
from app.models.processing_job import ProcessingJob
from app.models.provenance import ProvenanceEntity, ProvenanceActivity


class CompositeDocumentService:
    """Service for managing composite documents and their processing aggregation"""
    
    @staticmethod
    def auto_create_or_update_composite(original_document):
        """
        Auto-create composite document after first processed version is created,
        or update existing composite when new processed versions are added.
        This creates a unified workflow where users always see their latest work.
        """
        # Find all processed versions of this document
        processed_versions = Document.query.filter(
            Document.source_document_id == original_document.id,
            Document.version_type == 'processed'
        ).all()
        
        # Check if composite already exists
        existing_composite = Document.query.filter(
            Document.source_document_id == original_document.id,
            Document.version_type == 'composite'
        ).first()
        
        if existing_composite:
            # Update existing composite
            return CompositeDocumentService.update_composite(existing_composite)
        elif len(processed_versions) >= 1:
            # Create composite after first processed version
            composite_title = f"{original_document.title} - Unified View"
            source_documents = [original_document] + processed_versions
            
            composite_doc = Document.create_composite(
                title=composite_title,
                source_documents=source_documents,
                strategy='all_processing',
                user_id=original_document.user_id
            )
            
            # Set provenance relationship
            CompositeDocumentService.create_composite_provenance(composite_doc, source_documents)
            
            return composite_doc
        else:
            # No processed versions yet, no composite needed
            return None

    @staticmethod
    def auto_create_composite(original_document):
        """
        Automatically create a composite document when an original has multiple processed versions
        This addresses the user's need for a unified processing interface
        """
        # Find all processed versions of this document
        processed_versions = Document.query.filter(
            Document.source_document_id == original_document.id,
            Document.version_type == 'processed'
        ).all()
        
        if len(processed_versions) <= 1:
            return None  # Not enough versions to warrant a composite
        
        # Check if composite already exists
        existing_composite = Document.query.filter(
            Document.source_document_id == original_document.id,
            Document.version_type == 'composite'
        ).first()
        
        if existing_composite:
            # Update existing composite
            return CompositeDocumentService.update_composite(existing_composite)
        
        # Create new composite document
        composite_title = f"{original_document.title} - All Processing"
        source_documents = [original_document] + processed_versions
        
        composite_doc = Document.create_composite(
            title=composite_title,
            source_documents=source_documents,
            strategy='all_processing',
            user_id=original_document.user_id
        )
        
        # Set provenance relationship
        CompositeDocumentService.create_composite_provenance(composite_doc, source_documents)
        
        return composite_doc
    
    @staticmethod
    def update_composite(composite_document):
        """Update an existing composite document with latest processing"""
        if not composite_document.is_composite():
            raise ValueError("Document is not a composite document")
        
        composite_document.update_composite_processing()
        composite_document.updated_at = datetime.utcnow()
        db.session.commit()
        
        return composite_document
    
    @staticmethod
    def create_composite_provenance(composite_document, source_documents):
        """Create PROV-O compliant provenance for composite document"""
        
        # Create provenance entity for the composite document
        composite_entity = ProvenanceEntity.create_for_document(
            document=composite_document,
            activity_type='composite_creation',
            agent=f"user_{composite_document.user_id}"
        )
        composite_entity.prov_type = 'ont:CompositeDocument'
        
        # Link to all source documents
        source_ids = []
        for source_doc in source_documents:
            source_prov_id = f"document_{source_doc.id}"
            if hasattr(source_doc, 'version_number') and source_doc.version_number > 1:
                source_prov_id = f"document_{source_doc.id}_v{source_doc.version_number}"
            source_ids.append(source_prov_id)
        
        # Set composite derivation metadata
        composite_entity.prov_metadata = {
            'composite_strategy': 'all_processing',
            'source_documents': source_ids,
            'aggregated_processing': list(composite_document.get_available_processing().keys()),
            'composite_type': 'unified_processing'
        }
        
        db.session.add(composite_entity)
        
        # Create provenance activity for composition
        composite_activity = ProvenanceActivity(
            prov_id=f"activity_composite_{composite_document.id}",
            prov_type='ont:CompositeCreation',
            prov_label=f"Creating composite document from {len(source_documents)} sources",
            was_associated_with=f"user_{composite_document.user_id}",
            activity_type='composite_creation',
            activity_metadata={
                'source_count': len(source_documents),
                'strategy': 'all_processing',
                'processing_types_aggregated': list(composite_document.get_available_processing().keys())
            }
        )
        composite_activity.complete_activity({
            'composite_document_id': composite_document.id,
            'success': True
        })
        
        db.session.add(composite_activity)
        db.session.commit()
    
    @staticmethod
    def get_processing_recommendations(document):
        """
        Analyze document processing state and recommend composite creation
        This helps users understand when composite documents would be beneficial
        """
        recommendations = []
        
        if document.version_type == 'original':
            # Check for processed versions
            processed_versions = Document.query.filter(
                Document.source_document_id == document.id,
                Document.version_type == 'processed'
            ).all()
            
            if len(processed_versions) > 1:
                # Get unique processing types
                processing_types = set()
                for version in processed_versions:
                    for job in version.processing_jobs.filter(ProcessingJob.status == 'completed'):
                        processing_types.add(job.job_type)
                
                if len(processing_types) > 1:
                    recommendations.append({
                        'type': 'composite_creation',
                        'title': 'Create Unified Processing Document',
                        'description': f'Combine {len(processing_types)} processing types ({", ".join(processing_types)}) into one document',
                        'action': 'create_composite',
                        'priority': 'high',
                        'benefit': 'Access all processing results simultaneously'
                    })
        
        elif document.version_type == 'processed':
            # Check if there's a composite available
            original_doc = document.source_document
            if original_doc:
                composite = Document.query.filter(
                    Document.source_document_id == original_doc.id,
                    Document.version_type == 'composite'
                ).first()
                
                if composite:
                    recommendations.append({
                        'type': 'composite_available',
                        'title': 'Unified Version Available',
                        'description': f'View all processing results in composite document',
                        'action': 'view_composite',
                        'document_id': composite.id,
                        'priority': 'medium',
                        'benefit': 'Access to all processing types simultaneously'
                    })
        
        return recommendations
    
    @staticmethod
    def ensure_processing_summary_updated():
        """
        Maintenance function to ensure all documents have up-to-date processing summaries
        This can be run as a background task or during system updates
        """
        # Update all composite documents
        composite_docs = Document.query.filter(Document.version_type == 'composite').all()
        
        updated_count = 0
        for composite in composite_docs:
            try:
                composite.update_composite_processing()
                updated_count += 1
            except Exception as e:
                print(f"Error updating composite document {composite.id}: {e}")
        
        return {
            'updated_composites': updated_count,
            'total_composites': len(composite_docs)
        }
    
    @staticmethod
    def get_document_processing_status(document):
        """
        Get comprehensive processing status for any document type
        This provides a unified interface for checking processing availability
        """
        if document.is_composite():
            # For composite documents, show aggregated status
            available_processing = document.get_available_processing()
            source_docs = document.get_composite_sources()
            
            return {
                'document_type': 'composite',
                'strategy': 'all_processing',
                'available_processing': list(available_processing.keys()),
                'source_count': len(source_docs),
                'processing_details': {
                    ptype: {
                        'source_document': document.get_processing_source(ptype).id if document.get_processing_source(ptype) else None,
                        'available': True
                    } for ptype in available_processing.keys()
                }
            }
        else:
            # For regular documents, show direct processing
            completed_jobs = document.processing_jobs.filter(ProcessingJob.status == 'completed').all()
            available_processing = [job.job_type for job in completed_jobs]
            
            return {
                'document_type': document.version_type,
                'available_processing': available_processing,
                'processing_count': len(available_processing),
                'processing_details': {
                    job.job_type: {
                        'job_id': job.id,
                        'completed_at': job.completed_at.isoformat() if job.completed_at else None,
                        'available': True
                    } for job in completed_jobs
                }
            }