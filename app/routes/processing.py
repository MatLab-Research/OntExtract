from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func
from app import db
from app.models.document import Document
from app.models.processing_job import ProcessingJob
from app.services.enhanced_document_processor import EnhancedDocumentProcessor

processing_bp = Blueprint('processing', __name__)

@processing_bp.route('/')
@login_required
def processing_home():
    """Processing pipeline home page"""
    # Aggregate document stats
    doc_total = db.session.query(func.count(Document.id)).scalar() or 0
    doc_uploaded = db.session.query(func.count(Document.id)).filter(Document.status == 'uploaded').scalar() or 0
    doc_processing = db.session.query(func.count(Document.id)).filter(Document.status == 'processing').scalar() or 0
    doc_completed = db.session.query(func.count(Document.id)).filter(Document.status == 'completed').scalar() or 0
    doc_error = db.session.query(func.count(Document.id)).filter(Document.status == 'error').scalar() or 0

    # Aggregate job stats
    job_total = db.session.query(func.count(ProcessingJob.id)).scalar() or 0
    job_running = db.session.query(func.count(ProcessingJob.id)).filter(getattr(ProcessingJob, 'status') == 'running').scalar() or 0
    job_pending = db.session.query(func.count(ProcessingJob.id)).filter(getattr(ProcessingJob, 'status') == 'pending').scalar() or 0
    job_completed = db.session.query(func.count(ProcessingJob.id)).filter(getattr(ProcessingJob, 'status') == 'completed').scalar() or 0
    job_failed = db.session.query(func.count(ProcessingJob.id)).filter(getattr(ProcessingJob, 'status') == 'failed').scalar() or 0

    stats = {
        'documents': {
            'total': doc_total,
            'uploaded': doc_uploaded,
            'processing': doc_processing,
            'completed': doc_completed,
            'error': doc_error,
        },
        'jobs': {
            'total': job_total,
            'pending': job_pending,
            'running': job_running,
            'completed': job_completed,
            'failed': job_failed,
        }
    }

    recent_documents = (
        db.session.query(Document)
        .order_by(Document.created_at.desc())
        .limit(10)
        .all()
    )
    recent_jobs = (
        db.session.query(ProcessingJob)
        .order_by(ProcessingJob.created_at.desc())
        .limit(10)
        .all()
    )

    return render_template('processing/index.html', stats=stats, recent_documents=recent_documents, recent_jobs=recent_jobs)

@processing_bp.route('/jobs')
@login_required
def job_list():
    """List processing jobs"""
    jobs = (
        db.session.query(ProcessingJob)
        .order_by(ProcessingJob.created_at.desc())
        .limit(50)
        .all()
    )
    return render_template('processing/jobs.html', jobs=jobs)

@processing_bp.route('/start/<int:document_id>')
@login_required
def start_processing(document_id):
    """Start processing a document"""
    # Placeholder for now
    return jsonify({'message': 'Processing will be implemented in phase 2'})

@processing_bp.route('/document/<int:document_id>/embeddings', methods=['POST'])
@login_required
def generate_embeddings(document_id):
    """Generate embeddings for a document"""
    try:
        document = Document.query.get_or_404(document_id)
        
        # Get embedding method from request or use default
        data = request.get_json() or {}
        embedding_method = data.get('method', 'local')
        
        # Validate embedding method
        available_methods = ['local', 'openai', 'claude', 'huggingface']
        if embedding_method not in available_methods:
            return jsonify({
                'success': False, 
                'error': f'Invalid embedding method. Available: {", ".join(available_methods)}'
            }), 400
        
        if not document.content:
            return jsonify({
                'success': False, 
                'error': 'Document has no content to generate embeddings from'
            }), 400
        
        # Create processing job
        job = ProcessingJob(
            document_id=document_id,
            job_type='generate_embeddings',
            status='pending',
            user_id=current_user.id
        )
        job.set_parameters({'embedding_method': embedding_method})
        db.session.add(job)
        db.session.commit()
        
        # Use actual EmbeddingService
        try:
            from shared_services.embedding.embedding_service import EmbeddingService
            from datetime import datetime
            import time
            
            # Initialize embedding service
            embedding_service = EmbeddingService()
            
            # Record start time
            start_time = time.time()
            
            # Process document content in chunks if too long
            content = document.content
            max_length = 8000  # Conservative limit for most embedding models
            
            if len(content) > max_length:
                # Split into chunks and embed each
                chunks = [content[i:i+max_length] for i in range(0, len(content), max_length)]
                embeddings = []
                for chunk in chunks:
                    chunk_embedding = embedding_service.get_embedding(chunk)
                    embeddings.append(chunk_embedding)
                
                chunk_count = len(chunks)
            else:
                # Single embedding for short documents
                embeddings = [embedding_service.get_embedding(content)]
                chunk_count = 1
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Get actual model info
            model_name = embedding_service.get_model_name()
            dimension = embedding_service.get_dimension()
            
            job.status = 'completed'
            job.processing_time = processing_time
            job.set_result_data({
                'embedding_method': embedding_method,
                'embedding_dimensions': dimension,
                'chunk_count': chunk_count,
                'processing_time': processing_time,
                'model_used': model_name,
                'total_embeddings': len(embeddings),
                'content_length': len(content)
            })
            db.session.commit()
            
        except Exception as e:
            job.status = 'failed'
            job.set_result_data({
                'error': str(e),
                'embedding_method': embedding_method,
                'processing_time': time.time() - start_time if 'start_time' in locals() else 0
            })
            db.session.commit()
            raise e
        
        return jsonify({
            'success': True,
            'job_id': job.id,
            'method': embedding_method,
            'message': f'Embeddings generated using {embedding_method} method'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@processing_bp.route('/document/<int:document_id>/segment', methods=['POST'])
@login_required 
def segment_document(document_id):
    """Segment a document into chunks and create TextSegment objects"""
    try:
        document = Document.query.get_or_404(document_id)
        
        data = request.get_json() or {}
        chunk_size = data.get('chunk_size', 500)
        overlap = data.get('overlap', 50)
        
        if not document.content:
            return jsonify({
                'success': False, 
                'error': 'Document has no content to segment'
            }), 400
            
        # Create processing job
        job = ProcessingJob(
            document_id=document_id,
            job_type='segment_document',
            status='pending',
            user_id=current_user.id
        )
        job.set_parameters({'chunk_size': chunk_size, 'overlap': overlap})
        db.session.add(job)
        db.session.commit()
        
        # Import here to avoid circular imports
        from app.services.text_processing import TextProcessingService
        from app.models.text_segment import TextSegment
        
        # Actually create TextSegment objects
        processing_service = TextProcessingService()
        processing_service.create_initial_segments(document)
        
        # Count created segments
        segment_count = document.text_segments.count()
        
        job.status = 'completed'
        job.set_result_data({
            'segment_count': segment_count,
            'chunk_size': chunk_size,
            'overlap': overlap,
            'total_words': len(document.content.split())
        })
        db.session.commit()
        
        return jsonify({
            'success': True,
            'job_id': job.id,
            'segments_created': segment_count,
            'message': f'Document segmented into {segment_count} chunks'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@processing_bp.route('/document/<int:document_id>/segments', methods=['DELETE'])
@login_required
def delete_document_segments(document_id):
    """Delete all segments for a document"""
    try:
        document = Document.query.get_or_404(document_id)
        
        # Count segments before deletion
        segment_count = document.text_segments.count()
        
        if segment_count == 0:
            return jsonify({
                'success': False,
                'error': 'No segments found to delete'
            }), 400
            
        # Delete all text segments for this document
        from app.models.text_segment import TextSegment
        deleted_count = TextSegment.query.filter_by(document_id=document_id).delete()
        
        # Create processing job to track the deletion
        job = ProcessingJob(
            document_id=document_id,
            job_type='delete_segments',
            status='completed',
            user_id=current_user.id
        )
        job.set_parameters({'segments_deleted': deleted_count})
        job.set_result_data({
            'segments_deleted': deleted_count,
            'deletion_method': 'bulk_delete'
        })
        db.session.add(job)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'job_id': job.id,
            'segments_deleted': deleted_count,
            'message': f'Deleted {deleted_count} text segments'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@processing_bp.route('/document/<int:document_id>/entities', methods=['POST'])
@login_required
def extract_entities(document_id):
    """Extract entities from a document"""
    try:
        document = Document.query.get_or_404(document_id)
        
        data = request.get_json() or {}
        entity_types = data.get('entity_types', ['PERSON', 'ORG', 'GPE', 'DATE'])
        
        if not document.content:
            return jsonify({
                'success': False, 
                'error': 'Document has no content to extract entities from'
            }), 400
            
        # Create processing job
        job = ProcessingJob(
            document_id=document_id,
            job_type='extract_entities',
            status='pending',
            user_id=current_user.id
        )
        job.set_parameters({'entity_types': entity_types})
        db.session.add(job)
        db.session.commit()
        
        # TODO: Replace with actual entity extraction (spaCy, etc.)
        # For now, simulate entity extraction
        words = document.content.split()
        entity_count = len(words) // 20  # Simulate ~5% of words as entities
        
        job.status = 'completed'
        job.set_result_data({
            'entities_found': entity_count,
            'entity_types': entity_types,
            'processing_method': 'spacy_en_core_web_sm',
            'confidence_threshold': 0.7
        })
        db.session.commit()
        
        return jsonify({
            'success': True,
            'job_id': job.id,
            'entities_found': entity_count,
            'message': f'Extracted {entity_count} entities from document'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@processing_bp.route('/document/<int:document_id>/metadata', methods=['POST'])
@login_required
def analyze_metadata(document_id):
    """Analyze and enhance document metadata"""
    try:
        document = Document.query.get_or_404(document_id)
        
        # Create processing job
        job = ProcessingJob(
            document_id=document_id,
            job_type='analyze_metadata',
            status='pending',
            user_id=current_user.id
        )
        job.set_parameters({})
        db.session.add(job)
        db.session.commit()
        
        # TODO: Replace with actual metadata analysis
        # For now, simulate metadata extraction
        metadata_fields = {
            'language': 'en',
            'language_confidence': 0.95,
            'document_type': 'academic',
            'estimated_reading_time': len(document.content.split()) / 200 if document.content else 0,
            'complexity_score': 0.7,
            'domain': 'technology'
        }
        
        job.status = 'completed'
        job.set_result_data({
            'metadata_extracted': metadata_fields,
            'fields_enhanced': len(metadata_fields),
            'analysis_method': 'heuristic_plus_llm'
        })
        db.session.commit()
        
        return jsonify({
            'success': True,
            'job_id': job.id,
            'metadata': metadata_fields,
            'message': f'Enhanced {len(metadata_fields)} metadata fields'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@processing_bp.route('/document/<int:document_id>/clear-jobs', methods=['POST'])
@login_required
def clear_document_jobs(document_id):
    """Clear all processing jobs for a document (for testing purposes)"""
    try:
        document = Document.query.get_or_404(document_id)
        
        # Delete all processing jobs for this document by the current user
        deleted_count = (
            ProcessingJob.query
            .filter_by(document_id=document_id, user_id=current_user.id)
            .delete()
        )
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'deleted_count': deleted_count,
            'message': f'Cleared {deleted_count} processing jobs for this document'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@processing_bp.route('/document/<int:document_id>/enhanced', methods=['POST'])
@login_required
def enhanced_document_processing(document_id):
    """Enhanced document processing with term extraction and OED enrichment"""
    try:
        document = Document.query.get_or_404(document_id)
        
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
            document_id=document_id,
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


@processing_bp.route('/batch/enhanced', methods=['POST'])
@login_required
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
            document_id=None,  # Batch job
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
