"""Enhanced single-document processing routes."""

from flask import jsonify, request
from flask_login import current_user

from app import db
from app.models.document import Document
from app.models.processing_job import ProcessingJob
from app.services.enhanced_document_processor import EnhancedDocumentProcessor
from app.utils.auth_decorators import api_require_login_for_write

from . import processing_bp


@processing_bp.route('/document/<string:document_uuid>/enhanced', methods=['POST'])
@api_require_login_for_write
def enhanced_document_processing(document_uuid):
    """Enhanced document processing with term extraction and OED enrichment"""
    try:
        document = Document.query.filter_by(uuid=document_uuid).first_or_404()
        
        if not document.content:
            return jsonify({
                'success': False, 
                'error': 'Document has no content to process'
            }), 400
        
        data = request.get_json() or {}
        extract_terms = data.get('extract_terms', True)
        enrich_with_oed = data.get('enrich_with_oed', False)
        min_term_frequency = data.get('min_term_frequency', 2)
        
        # Create processing job
        job = ProcessingJob(
            document_id=document.id,
            job_type='enhanced_processing',
            status='pending',
            user_id=current_user.id
        )
        job.set_parameters({
            'extract_terms': extract_terms,
            'enrich_with_oed': enrich_with_oed,
            'min_term_frequency': min_term_frequency
        })
        db.session.add(job)
        db.session.commit()
        
        # Perform enhanced processing
        processor = EnhancedDocumentProcessor()
        result = processor.process_document_with_enrichment(
            document,
            extract_terms=extract_terms,
            enrich_with_oed=enrich_with_oed,
            min_term_frequency=min_term_frequency
        )
        
        # Update job with results
        job.status = 'completed' if result['success'] else 'failed'
        job.set_result_data({
            'document_processed': result['document_processed'],
            'terms_extracted': result['terms_extracted'],
            'terms_enriched': result['terms_enriched'],
            'extracted_terms': [t['term_text'] for t in result['extracted_terms']],
            'enrichment_success_rate': (
                result['terms_enriched'] / result['terms_extracted'] 
                if result['terms_extracted'] > 0 else 0
            ),
            'processing_errors': result['errors']
        })
        db.session.commit()
        
        return jsonify({
            'success': result['success'],
            'job_id': job.id,
            'document_processed': result['document_processed'],
            'terms_extracted': result['terms_extracted'],
            'terms_enriched': result['terms_enriched'],
            'extracted_terms': result['extracted_terms'][:10],  # Return first 10 terms
            'message': (
                f'Enhanced processing completed. '
                f'Extracted {result["terms_extracted"]} terms, '
                f'enriched {result["terms_enriched"]} with OED data.'
            ),
            'errors': result['errors']
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
