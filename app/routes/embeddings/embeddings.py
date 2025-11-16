"""
Embeddings API Routes

This module handles API endpoints for embedding operations.

Routes (embeddings_bp):
- GET /api/embeddings/document/<id>        - Get embedding info
- GET /api/embeddings/document/<id>/sample - Get embedding sample
- GET /api/embeddings/document/<id>/verify - Verify embeddings
- GET /api/embeddings/jobs/<id>            - Get job details
"""

from flask import jsonify
from flask_login import current_user
from app.utils.auth_decorators import api_require_login_for_write
from app import db
from app.models import Document, ProcessingJob
import logging

from . import embeddings_bp

logger = logging.getLogger(__name__)


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
        estimated_size_mb = (dimensions * chunk_count * 4) / (1024 * 1024)

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
                chunk_size = 100

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
