"""
Processing Batch Operations Routes

This module handles batch processing operations for multiple documents.

Routes:
- POST /processing/batch/enhanced - Batch enhanced processing with OED enrichment
"""

from flask import request, jsonify
from flask_login import current_user
from app.utils.auth_decorators import api_require_login_for_write
from app import db
from app.models.document import Document
from app.models.processing_job import ProcessingJob
from app.services.enhanced_document_processor import EnhancedDocumentProcessor

from . import processing_bp


@processing_bp.route('/batch/enhanced', methods=['POST'])
@api_require_login_for_write
def batch_enhanced_processing():
    """Process multiple documents with enhanced processing and OED enrichment"""
    try:
        data = request.get_json()
        if not data or not data.get('document_ids'):
            return jsonify({
                'success': False,
                'error': 'document_ids array is required'
            }), 400

        document_ids = data['document_ids']
        extract_terms = data.get('extract_terms', True)
        enrich_with_oed = data.get('enrich_with_oed', False)

        # Validate document IDs
        valid_documents = Document.query.filter(Document.id.in_(document_ids)).all()
        valid_ids = [doc.id for doc in valid_documents]

        if len(valid_ids) != len(document_ids):
            invalid_ids = set(document_ids) - set(valid_ids)
            return jsonify({
                'success': False,
                'error': f'Invalid document IDs: {list(invalid_ids)}'
            }), 400

        # Create batch processing job
        job = ProcessingJob(
            document_id=None,
            job_type='batch_enhanced_processing',
            status='pending',
            user_id=current_user.id
        )
        job.set_parameters({
            'document_ids': document_ids,
            'extract_terms': extract_terms,
            'enrich_with_oed': enrich_with_oed,
            'document_count': len(document_ids)
        })
        db.session.add(job)
        db.session.commit()

        # Perform batch processing
        processor = EnhancedDocumentProcessor()
        batch_result = processor.process_document_batch_with_enrichment(
            document_ids,
            extract_terms=extract_terms,
            enrich_with_oed=enrich_with_oed
        )

        # Update job with results
        job.status = 'completed' if batch_result['success'] else 'failed'
        job.set_result_data({
            'documents_processed': batch_result['documents_processed'],
            'total_terms_extracted': batch_result['total_terms_extracted'],
            'total_terms_enriched': batch_result['total_terms_enriched'],
            'document_results': [
                {
                    'document_id': r['document_id'],
                    'document_title': r['document_title'],
                    'success': r['result']['success'],
                    'terms_extracted': r['result']['terms_extracted'],
                    'terms_enriched': r['result']['terms_enriched']
                }
                for r in batch_result['document_results']
            ],
            'processing_errors': batch_result['errors']
        })
        db.session.commit()

        return jsonify({
            'success': batch_result['success'],
            'job_id': job.id,
            'documents_processed': batch_result['documents_processed'],
            'total_terms_extracted': batch_result['total_terms_extracted'],
            'total_terms_enriched': batch_result['total_terms_enriched'],
            'document_results': batch_result['document_results'],
            'message': (
                f'Batch processing completed. '
                f'Processed {batch_result["documents_processed"]} documents, '
                f'extracted {batch_result["total_terms_extracted"]} terms, '
                f'enriched {batch_result["total_terms_enriched"]} with OED data.'
            ),
            'errors': batch_result['errors']
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
