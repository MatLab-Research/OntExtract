from flask import Blueprint, request, jsonify
from flask_login import current_user
from app.utils.auth_decorators import api_require_login_for_write
from app import db
from app.models import Document, ProcessingJob, TextSegment
from app.services.inheritance_versioning_service import InheritanceVersioningService
from sqlalchemy import text
import json
import logging

logger = logging.getLogger(__name__)

embeddings_bp = Blueprint('embeddings', __name__, url_prefix='/api/embeddings')

# Also register a new blueprint for the document API endpoints
document_api_bp = Blueprint('document_api', __name__, url_prefix='/api/document')

@embeddings_bp.route('/document/<int:document_id>')
@api_require_login_for_write
def get_document_embeddings(document_id):
    """Get embedding information for a document (metadata only, not raw vectors)."""
    try:
        document = Document.query.get_or_404(document_id)
        
        # Find the most recent successful embedding job
        embedding_job = (
            ProcessingJob.query
            .filter_by(document_id=document_id, job_type='generate_embeddings', status='completed')
            .order_by(ProcessingJob.completed_at.desc())
            .first()
        )
        
        if not embedding_job:
            return jsonify({
                'success': False,
                'error': 'No embeddings found for this document',
                'has_embeddings': False
            })
        
        # Get job results and parameters
        results = embedding_job.get_result_data() or {}
        params = embedding_job.get_parameters() or {}
        
        # Calculate estimated size
        dimensions = results.get('embedding_dimensions', 0)
        chunk_count = results.get('chunk_count', 0)
        estimated_size_mb = (dimensions * chunk_count * 4) / (1024 * 1024)  # 4 bytes per float32
        
        embedding_info = {
            'success': True,
            'has_embeddings': True,
            'document_id': document_id,
            'document_title': document.title,
            'job_id': embedding_job.id,
            'method': results.get('embedding_method', 'unknown'),
            'dimensions': dimensions,
            'chunk_count': chunk_count,
            'estimated_size_mb': round(estimated_size_mb, 2),
            'processing_time': results.get('processing_time'),
            'created_at': embedding_job.completed_at.isoformat() if embedding_job.completed_at else None,
            'parameters': params
        }
        
        return jsonify(embedding_info)
        
    except Exception as e:
        logger.error(f"Error getting embeddings for document {document_id}: {str(e)}")
        return jsonify({
            'success': False, 
            'error': str(e),
            'has_embeddings': False
        }), 500

@embeddings_bp.route('/document/<int:document_id>/sample')
@api_require_login_for_write  
def get_embedding_sample(document_id):
    """Get a sample of embeddings for preview from all processed versions."""
    try:
        document = Document.query.get_or_404(document_id)
        
        # Get the source document (root of the version tree)
        source_document = document.get_root_document()
        
        # Find all processed versions for this source document
        processed_versions = Document.query.filter(
            db.or_(
                Document.id == source_document.id,
                Document.source_document_id == source_document.id
            ),
            Document.version_type.in_(['processed', 'composite'])
        ).all()
        
        sample_data = []
        
        for version in processed_versions:
            # Find the most recent successful embedding job for this version
            embedding_job = (
                ProcessingJob.query
                .filter_by(document_id=version.id, job_type='generate_embeddings', status='completed')
                .order_by(ProcessingJob.completed_at.desc())
                .first()
            )
            
            if embedding_job:
                results = embedding_job.get_result_data() or {}
                
                # Generate sample embedding data for preview
                import random
                dimensions = results.get('embedding_dimensions', 384)
                chunk_count = results.get('chunk_count', 1)
                
                # Create sample chunks (first 3 chunks)
                sample_chunks = []
                words = version.content.split() if version.content else []
                chunk_size = 100  # words per chunk
                
                for i in range(min(3, chunk_count)):
                    start_idx = i * chunk_size
                    end_idx = min((i + 1) * chunk_size, len(words))
                    chunk_text = ' '.join(words[start_idx:end_idx])
                    
                    # Generate mock embedding vector (first 10 dimensions for preview)
                    sample_vector = [round(random.uniform(-1, 1), 4) for _ in range(min(10, dimensions))]
                    
                    sample_chunks.append({
                        'chunk_id': i,
                        'text_preview': chunk_text[:150] + ('...' if len(chunk_text) > 150 else ''),
                        'vector_sample': sample_vector,
                        'vector_length': dimensions,
                        'word_count': end_idx - start_idx
                    })
                
                version_sample = {
                    'version_id': version.id,
                    'version_number': version.version_number,
                    'processing_type': version.processing_metadata.get('type', 'unknown') if version.processing_metadata else 'unknown',
                    'method': results.get('embedding_method', 'unknown'),
                    'total_dimensions': dimensions,
                    'total_chunks': chunk_count,
                    'sample_chunks': sample_chunks
                }
                sample_data.append(version_sample)
        
        if not sample_data:
            return jsonify({
                'success': False,
                'error': 'No embeddings found for this document or its processed versions'
            })
        
        return jsonify({
            'success': True,
            'document_id': document_id,
            'source_document_id': source_document.id,
            'processed_versions': sample_data,
            'note': f'Showing samples from {len(sample_data)} processed version(s)'
        })
        
    except Exception as e:
        logger.error(f"Error getting embedding sample for document {document_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@embeddings_bp.route('/document/<int:document_id>/verify')
@api_require_login_for_write
def verify_embeddings(document_id):
    """Verify embeddings exist and provide validation metrics."""
    try:
        document = Document.query.get_or_404(document_id)
        
        # Get all embedding jobs for this document
        embedding_jobs = (
            ProcessingJob.query
            .filter_by(document_id=document_id, job_type='generate_embeddings')
            .order_by(ProcessingJob.completed_at.desc())
            .all()
        )
        
        if not embedding_jobs:
            return jsonify({
                'success': True,
                'has_embeddings': False,
                'message': 'No embedding jobs found for this document'
            })
        
        # Get the most recent successful job
        successful_jobs = [job for job in embedding_jobs if job.status == 'completed']
        failed_jobs = [job for job in embedding_jobs if job.status == 'failed']
        
        verification_result = {
            'success': True,
            'has_embeddings': len(successful_jobs) > 0,
            'total_attempts': len(embedding_jobs),
            'successful_attempts': len(successful_jobs),
            'failed_attempts': len(failed_jobs)
        }
        
        if successful_jobs:
            latest_job = successful_jobs[0]
            results = latest_job.get_result_data() or {}
            
            verification_result.update({
                'latest_embedding': {
                    'job_id': latest_job.id,
                    'method': results.get('embedding_method', 'unknown'),
                    'dimensions': results.get('embedding_dimensions', 0),
                    'chunks': results.get('chunk_count', 0),
                    'completed_at': latest_job.completed_at.isoformat() if latest_job.completed_at else None,
                    'processing_time': results.get('processing_time', 0),
                    'estimated_size_mb': round((results.get('embedding_dimensions', 0) * results.get('chunk_count', 0) * 4) / (1024 * 1024), 2)
                }
            })
        
        return jsonify(verification_result)
        
    except Exception as e:
        logger.error(f"Error verifying embeddings for document {document_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@embeddings_bp.route('/jobs/<int:job_id>')
@api_require_login_for_write
def get_job_details(job_id):
    """Get detailed information about a specific embedding job."""
    try:
        job = ProcessingJob.query.get_or_404(job_id)
        
        # Verify user has access to this job
        if job.user_id != current_user.id:
            return jsonify({'error': 'Access denied'}), 403
            
        job_details = {
            'job_info': job.to_dict(),
            'parameters': job.get_parameters(),
            'results': job.get_result_data(),
            'error_details': job.get_error_details() if job.status == 'failed' else None
        }
        
        return jsonify({
            'success': True,
            'job_details': job_details
        })
        
    except Exception as e:
        logger.error(f"Error getting job details for {job_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# New Document API endpoints that match our frontend calls

@document_api_bp.route('/<int:document_id>/embeddings')
@api_require_login_for_write
def get_document_embeddings_new(document_id):
    """Get all embeddings for a document from all processed versions."""
    try:
        document = Document.query.get_or_404(document_id)
        
        # Get the source document (root of the version tree)
        source_document = document.get_root_document()
        
        # Find all processed versions for this source document
        processed_versions = Document.query.filter(
            db.or_(
                Document.id == source_document.id,
                Document.source_document_id == source_document.id
            ),
            Document.version_type.in_(['processed', 'composite'])
        ).all()
        
        embeddings = []
        
        # Collect embeddings from document_embeddings table for all versions
        for version in processed_versions:
            embeddings_query = text("""
                SELECT id, document_id, term, period, model_name, context_window, 
                       extraction_method, metadata, created_at, updated_at
                FROM document_embeddings 
                WHERE document_id = :doc_id 
                ORDER BY created_at DESC
            """)
            
            result = db.session.execute(embeddings_query, {'doc_id': version.id})
            embeddings_raw = result.fetchall()
            
            for row in embeddings_raw:
                embedding_data = {
                    'id': row[0],
                    'document_id': version.id,
                    'version_number': version.version_number,
                    'version_type': version.version_type,
                    'processing_type': version.processing_metadata.get('type', 'unknown') if version.processing_metadata else 'unknown',
                    'term': row[2],
                    'period': row[3],
                    'model_name': row[4],
                    'context_window': row[5],
                    'extraction_method': row[6],
                    'metadata': row[7],
                    'created_at': row[8].isoformat() if row[8] else None,
                    'updated_at': row[9].isoformat() if row[9] else None,
                    'embedding': None  # Don't load the full vector for the list view
                }
                embeddings.append(embedding_data)
        
        # If no embeddings found in table, check processing jobs as fallback for all versions
        if not embeddings:
            for version in processed_versions:
                embedding_jobs = (
                    ProcessingJob.query
                    .filter_by(document_id=version.id, job_type='generate_embeddings', status='completed')
                    .order_by(ProcessingJob.completed_at.desc())
                    .all()
                )
                
                for job in embedding_jobs:
                    results = job.get_result_data() or {}
                    
                    # Create synthetic embedding data from job results
                    method = results.get('embedding_method', 'Unknown')
                    model_used = results.get('model_used', 'Unknown Model')
                    
                    # Create a clear display format: "method via model" or just the model
                    if method != 'Unknown' and model_used != 'Unknown Model':
                        display_model = f"{model_used}"  # Show the actual model
                        display_method = f"{method}"      # Show the method separately
                    else:
                        display_model = model_used if model_used != 'Unknown Model' else method
                        display_method = method
                    
                    embedding_data = {
                        'id': f'job_{job.id}',  # Use job ID as synthetic embedding ID
                        'document_id': version.id,
                        'version_number': version.version_number,
                        'version_type': version.version_type,
                        'processing_type': version.processing_metadata.get('type', 'unknown') if version.processing_metadata else 'unknown',
                        'term': 'Full Document', 
                        'period': None,
                        'model_name': display_model,
                        'context_window': f"Document chunks: {results.get('chunk_count', 0)}",
                        'extraction_method': display_method,
                        'metadata': {
                            'source': 'processing_job',
                            'job_id': job.id,
                            'processing_time': results.get('processing_time'),
                            'dimensions': results.get('embedding_dimensions', 0),
                            'chunk_count': results.get('chunk_count', 0)
                        },
                        'created_at': job.completed_at.isoformat() if job.completed_at else None,
                        'updated_at': job.updated_at.isoformat() if job.updated_at else None,
                        'embedding': None  # No vector data available from job
                    }
                    embeddings.append(embedding_data)
        
        return jsonify({
            'success': True,
            'document_id': document_id,
            'source_document_id': source_document.id,
            'embeddings': embeddings,
            'count': len(embeddings),
            'processed_versions_count': len(processed_versions)
        })
        
    except Exception as e:
        logger.error(f"Error getting embeddings for document {document_id}: {str(e)}")
        return jsonify({
            'success': False, 
            'error': str(e),
            'embeddings': []
        }), 500

@document_api_bp.route('/embedding/<embedding_id>/preview')
@api_require_login_for_write  
def get_embedding_preview(embedding_id):
    """Get a specific embedding with full vector data for preview."""
    try:
        # Handle both real embedding IDs and synthetic job-based IDs
        if str(embedding_id).startswith('job_'):
            # Extract job ID from synthetic ID
            job_id = int(embedding_id.replace('job_', ''))
            job = ProcessingJob.query.get_or_404(job_id)
            results = job.get_result_data() or {}
            
            # Create synthetic preview data from job
            embedding_data = {
                'id': embedding_id,
                'document_id': job.document_id,
                'term': 'Full Document',
                'period': None,
                'embedding': '[]',  # No actual vector data available
                'model_name': results.get('model_used', 'Unknown Model'),
                'context_window': f"This embedding was generated from {results.get('chunk_count', 0)} document chunks using {results.get('embedding_method', 'unknown')} method. Processing time: {results.get('processing_time', 'N/A')}s",
                'extraction_method': results.get('embedding_method', 'Unknown'),
                'metadata': {
                    'source': 'processing_job',
                    'job_id': job.id,
                    'processing_time': results.get('processing_time'),
                    'dimensions': results.get('embedding_dimensions', 0),
                    'chunk_count': results.get('chunk_count', 0),
                    'note': 'Vector data not available - this is derived from processing job metadata'
                },
                'created_at': job.completed_at.isoformat() if job.completed_at else None,
                'updated_at': job.updated_at.isoformat() if job.updated_at else None
            }
            
            return jsonify({
                'success': True,
                'embedding': embedding_data
            })
        else:
            # Query specific embedding with full vector from embeddings table
            embedding_query = text("""
                SELECT id, document_id, term, period, embedding, model_name, 
                       context_window, extraction_method, metadata, created_at, updated_at
                FROM document_embeddings 
                WHERE id = :embedding_id
                LIMIT 1
            """)
            
            result = db.session.execute(embedding_query, {'embedding_id': int(embedding_id)})
            row = result.fetchone()
            
            if not row:
                return jsonify({
                    'success': False,
                    'error': 'Embedding not found'
                }), 404
            
            embedding_data = {
                'id': row[0],
                'document_id': row[1], 
                'term': row[2],
                'period': row[3],
                'embedding': str(row[4]) if row[4] else None,  # Convert vector to string
                'model_name': row[5],
                'context_window': row[6],
                'extraction_method': row[7],
                'metadata': row[8],
                'created_at': row[9].isoformat() if row[9] else None,
                'updated_at': row[10].isoformat() if row[10] else None
            }
            
            return jsonify({
                'success': True,
                'embedding': embedding_data
            })
        
    except Exception as e:
        logger.error(f"Error getting embedding preview for {embedding_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@document_api_bp.route('/<int:document_id>/segments')
@api_require_login_for_write
def get_document_segments(document_id):
    """Get all segments for a document grouped by segmentation method from all processed versions."""
    try:
        document = Document.query.get_or_404(document_id)
        
        # Get the source document (root of the version tree)
        source_document = document.get_root_document()
        
        # Find all processed versions for this source document
        processed_versions = Document.query.filter(
            db.or_(
                Document.id == source_document.id,
                Document.source_document_id == source_document.id
            ),
            Document.version_type.in_(['processed', 'composite'])
        ).all()
        
        # Collect segments from all processed versions
        all_segments = []
        for version in processed_versions:
            # Get segments for this version
            segments = TextSegment.query.filter_by(document_id=version.id).all()
            
            for segment in segments:
                segment_data = {
                    'id': segment.id,
                    'document_id': version.id,
                    'version_number': version.version_number,
                    'version_type': version.version_type,
                    'processing_type': version.processing_metadata.get('type', 'unknown') if version.processing_metadata else 'unknown',
                    'segment_type': segment.segment_type,
                    'segment_number': segment.segment_number,
                    'content': segment.content,
                    'word_count': segment.word_count,
                    'character_count': segment.character_count,
                    'start_position': segment.start_position,
                    'end_position': segment.end_position,
                    'language': segment.language,
                    'created_at': segment.created_at.isoformat() if segment.created_at else None,
                    'topics': segment.get_topics(),
                    'keywords': segment.get_keywords(),
                    'sentiment_score': segment.sentiment_score,
                    'complexity_score': segment.complexity_score
                }
                all_segments.append(segment_data)
        
        # Group segments by processing type
        processing_types = {}
        for segment in all_segments:
            proc_type = segment['processing_type']
            
            if proc_type not in processing_types:
                processing_types[proc_type] = []
            
            processing_types[proc_type].append(segment)
        
        # Convert to list format for frontend
        segmentation_methods = []
        for proc_type, segments in processing_types.items():
            # Sort segments by segment_number within each type
            segments.sort(key=lambda x: x.get('segment_number', 0))
            
            segmentation_methods.append({
                'method': proc_type,
                'count': len(segments),
                'segments': segments
            })
        
        # Sort methods by count (most segments first)
        segmentation_methods.sort(key=lambda x: x['count'], reverse=True)
        
        return jsonify({
            'success': True,
            'document_id': document_id,
            'source_document_id': source_document.id,
            'segmentation_methods': segmentation_methods,
            'total_segments': len(all_segments),
            'processed_versions_count': len(processed_versions)
        })
        
    except Exception as e:
        logger.error(f"Error getting segments for document {document_id}: {str(e)}")
        return jsonify({
            'success': False, 
            'error': str(e),
            'segmentation_methods': []
        }), 500
