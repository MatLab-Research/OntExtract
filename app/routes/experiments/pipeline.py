"""
Experiments Document Processing Pipeline Routes

This module handles document processing pipeline operations for experiments.

Routes:
- GET  /experiments/<id>/document_pipeline                   - Pipeline overview
- GET  /experiments/<id>/process_document/<doc_id>           - Process specific document
- POST /experiments/<id>/document/<doc_id>/apply_embeddings  - Apply embeddings
- POST /api/experiment-processing/start                       - Start processing operation
- GET  /api/experiment-document/<id>/processing-status        - Get processing status
- GET  /api/processing/<id>/artifacts                         - Get processing artifacts

REFACTORED: Now uses PipelineService with DTO validation
"""

from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import current_user
from app.utils.auth_decorators import api_require_login_for_write
from app.services.pipeline_service import get_pipeline_service
from app.services.base_service import ServiceError, ValidationError, NotFoundError
from app.dto.pipeline_dto import StartProcessingDTO
from pydantic import ValidationError as PydanticValidationError
import logging

from . import experiments_bp

logger = logging.getLogger(__name__)
pipeline_service = get_pipeline_service()


@experiments_bp.route('/<int:experiment_id>/document_pipeline')
def document_pipeline(experiment_id):
    """
    Step 2: Document Processing Pipeline Overview

    REFACTORED: Now uses PipelineService
    """
    try:
        # Get pipeline overview data from service
        data = pipeline_service.get_pipeline_overview(experiment_id)

        return render_template(
            'experiments/document_pipeline.html',
            experiment=data['experiment'],
            documents=data['documents'],
            total_count=data['total_count'],
            completed_count=data['completed_count'],
            progress_percentage=data['progress_percentage']
        )

    except NotFoundError as e:
        logger.warning(f"Experiment {experiment_id} not found: {e}")
        from flask import abort
        abort(404)

    except ServiceError as e:
        logger.error(f"Service error getting pipeline overview: {e}", exc_info=True)
        from flask import abort
        abort(500)


@experiments_bp.route('/<int:experiment_id>/process_document/<int:document_id>')
def process_document(experiment_id, document_id):
    """
    Process a specific document with experiment-specific context

    REFACTORED: Now uses PipelineService
    """
    try:
        # Get process document data from service
        data = pipeline_service.get_process_document_data(experiment_id, document_id)

        return render_template(
            'experiments/process_document.html',
            experiment=data['experiment'],
            document=data['document'],
            experiment_document=data['experiment_document'],
            processing_operations=data['processing_operations'],
            processing_progress=data['processing_progress'],
            doc_index=data['doc_index'],
            total_docs=data['total_docs'],
            has_previous=data['has_previous'],
            has_next=data['has_next'],
            previous_doc_id=data['previous_doc_id'],
            next_doc_id=data['next_doc_id']
        )

    except ValidationError as e:
        flash(str(e), 'error')
        return redirect(url_for('experiments.document_pipeline', experiment_id=experiment_id))

    except NotFoundError as e:
        logger.warning(f"Document {document_id} not found in experiment {experiment_id}: {e}")
        from flask import abort
        abort(404)

    except ServiceError as e:
        logger.error(f"Service error getting process document data: {e}", exc_info=True)
        from flask import abort
        abort(500)


@experiments_bp.route('/<int:experiment_id>/document/<int:document_id>/apply_embeddings', methods=['POST'])
@api_require_login_for_write
def apply_embeddings_to_experiment_document(experiment_id, document_id):
    """
    Apply embeddings to a document for a specific experiment

    REFACTORED: Now uses PipelineService
    """
    try:
        # Call service to apply embeddings
        result = pipeline_service.apply_embeddings(experiment_id, document_id)

        return jsonify({
            'success': True,
            'message': 'Embeddings applied successfully for this experiment',
            'embedding_info': result['embedding_info'],
            'processing_progress': result['processing_progress']
        }), 200

    except ValidationError as e:
        logger.warning(f"Validation error applying embeddings: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

    except NotFoundError as e:
        logger.warning(f"Document {document_id} not found in experiment {experiment_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Document not found'
        }), 404

    except ServiceError as e:
        logger.error(f"Service error applying embeddings: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

    except Exception as e:
        logger.error(f"Unexpected error applying embeddings: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'An error occurred while applying embeddings'
        }), 500


@experiments_bp.route('/api/experiment-processing/start', methods=['POST'])
@api_require_login_for_write
def start_experiment_processing():
    """
    Start a new processing operation for an experiment document

    REFACTORED: Now uses PipelineService with DTO validation
    """
    try:
        # Validate request data using DTO
        data = StartProcessingDTO(**request.get_json())

        # Call service to start processing
        result = pipeline_service.start_processing(
            experiment_document_id=data.experiment_document_id,
            processing_type=data.processing_type,
            processing_method=data.processing_method,
            user_id=current_user.id
        )

        # Check if processing failed
        if 'error' in result:
            return jsonify({
                'success': False,
                'error': result['error'],
                'processing_id': result['processing_id']
            }), 400

        return jsonify({
            'success': True,
            'message': f'{data.processing_type} processing started successfully',
            'processing_id': result['processing_id'],
            'status': result['status']
        }), 200

    except PydanticValidationError as e:
        logger.warning(f"Validation error starting processing: {e}")
        return jsonify({
            'success': False,
            'error': 'Validation failed',
            'details': e.errors()
        }), 400

    except ValidationError as e:
        logger.warning(f"Business validation error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

    except NotFoundError as e:
        logger.warning(f"Resource not found: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 404

    except ServiceError as e:
        logger.error(f"Service error starting processing: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to start processing'
        }), 500

    except Exception as e:
        logger.error(f"Unexpected error starting processing: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@experiments_bp.route('/api/experiment-document/<int:exp_doc_id>/processing-status')
def get_experiment_document_processing_status(exp_doc_id):
    """
    Get processing status for an experiment document

    REFACTORED: Now uses PipelineService
    """
    try:
        # Get processing status from service
        result = pipeline_service.get_processing_status(exp_doc_id)

        return jsonify({
            'success': True,
            'experiment_document_id': result['experiment_document_id'],
            'processing_operations': result['processing_operations']
        }), 200

    except NotFoundError as e:
        logger.warning(f"Experiment document {exp_doc_id} not found: {e}")
        return jsonify({
            'success': False,
            'error': 'Experiment document not found'
        }), 404

    except ServiceError as e:
        logger.error(f"Service error getting processing status: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to get processing status'
        }), 500

    except Exception as e:
        logger.error(f"Unexpected error getting processing status: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@experiments_bp.route('/api/processing/<uuid:processing_id>/artifacts')
def get_processing_artifacts(processing_id):
    """
    Get artifacts for a specific processing operation

    REFACTORED: Now uses PipelineService
    """
    try:
        # Get processing artifacts from service
        result = pipeline_service.get_processing_artifacts(processing_id)

        return jsonify({
            'success': True,
            'processing_id': result['processing_id'],
            'processing_type': result['processing_type'],
            'processing_method': result['processing_method'],
            'artifacts': result['artifacts']
        }), 200

    except NotFoundError as e:
        logger.warning(f"Processing {processing_id} not found: {e}")
        return jsonify({
            'success': False,
            'error': 'Processing operation not found'
        }), 404

    except ServiceError as e:
        logger.error(f"Service error getting processing artifacts: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to get processing artifacts'
        }), 500

    except Exception as e:
        logger.error(f"Unexpected error getting processing artifacts: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
