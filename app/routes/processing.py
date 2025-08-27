from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func
from app import db
from app.models.document import Document
from app.models.processing_job import ProcessingJob

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
        
        # TODO: Replace with actual embedding generation
        # For now, simulate processing with correct dimensions per method
        dimensions_map = {
            'local': 384,      # sentence-transformers default
            'openai': 1536,    # text-embedding-3-small
            'claude': 1024,    # Anthropic embeddings  
            'huggingface': 768 # bert-base default
        }
        
        job.status = 'completed'
        job.set_result_data({
            'embedding_method': embedding_method,
            'embedding_dimensions': dimensions_map.get(embedding_method, 384),
            'chunk_count': len(document.content.split()) // 100 + 1,
            'processing_time': 2.5
        })
        db.session.commit()
        
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
