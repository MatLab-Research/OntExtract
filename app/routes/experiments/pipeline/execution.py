"""Experiment pipeline execution endpoints."""

import logging

from flask import jsonify, request
from flask_login import current_user
from pydantic import ValidationError as PydanticValidationError

from app.dto.pipeline_dto import StartProcessingDTO
from app.services.base_service import (
    NotFoundError,
    PermissionError,
    ServiceError,
    ValidationError,
)
from app.utils.auth_decorators import api_require_login_for_write

from .. import experiments_bp
from . import pipeline_service


logger = logging.getLogger(__name__)


@experiments_bp.route(
    '/<int:experiment_id>/document/<int:document_id>/apply_embeddings',
    methods=['POST'],
)
@api_require_login_for_write
def apply_embeddings_to_experiment_document(experiment_id, document_id):
    """Apply embeddings to a document in an experiment."""
    try:
        result = pipeline_service.apply_embeddings(
            experiment_id,
            document_id,
            current_user.id,
        )
        return jsonify({
            'success': True,
            'message': 'Embeddings applied successfully for this experiment',
            'embedding_info': result['embedding_info'],
            'processing_progress': result['processing_progress'],
        }), 200
    except ValidationError as exc:
        logger.warning(f"Validation error applying embeddings: {exc}")
        return jsonify({'success': False, 'error': str(exc)}), 400
    except NotFoundError as exc:
        logger.warning(
            f"Document {document_id} not found in experiment {experiment_id}: {exc}"
        )
        return jsonify({'success': False, 'error': 'Document not found'}), 404
    except PermissionError:
        return jsonify({'success': False, 'error': 'Permission denied'}), 403
    except ServiceError as exc:
        logger.error(
            f"Service error applying embeddings: {exc}",
            exc_info=True,
        )
        return jsonify({
            'success': False,
            'error': 'Failed to apply embeddings',
        }), 500
    except Exception as exc:
        logger.error(
            f"Unexpected error applying embeddings: {exc}",
            exc_info=True,
        )
        return jsonify({
            'success': False,
            'error': 'An error occurred while applying embeddings',
        }), 500


@experiments_bp.route('/api/experiment-processing/start', methods=['POST'])
@api_require_login_for_write
def start_experiment_processing():
    """Start a validated processing operation for an experiment document."""
    try:
        data = StartProcessingDTO(**(request.get_json(silent=True) or {}))
        result = pipeline_service.start_processing(
            experiment_document_id=data.experiment_document_id,
            processing_type=data.processing_type,
            processing_method=data.processing_method,
            user_id=current_user.id,
        )
        if 'error' in result:
            return jsonify({
                'success': False,
                'error': 'Processing operation failed',
                'processing_id': result['processing_id'],
            }), 400
        return jsonify({
            'success': True,
            'message': f'{data.processing_type} processing started successfully',
            'processing_id': result['processing_id'],
            'status': result['status'],
        }), 200
    except PydanticValidationError as exc:
        logger.warning(f"Validation error starting processing: {exc}")
        return jsonify({
            'success': False,
            'error': 'Validation failed',
            'details': exc.errors(include_context=False),
        }), 400
    except ValidationError as exc:
        logger.warning(f"Business validation error: {exc}")
        return jsonify({'success': False, 'error': str(exc)}), 400
    except NotFoundError as exc:
        logger.warning(f"Resource not found: {exc}")
        return jsonify({'success': False, 'error': str(exc)}), 404
    except PermissionError:
        return jsonify({'success': False, 'error': 'Permission denied'}), 403
    except ServiceError as exc:
        logger.error(
            f"Service error starting processing: {exc}",
            exc_info=True,
        )
        return jsonify({
            'success': False,
            'error': 'Failed to start processing',
        }), 500
    except Exception as exc:
        logger.error(
            f"Unexpected error starting processing: {exc}",
            exc_info=True,
        )
        return jsonify({
            'success': False,
            'error': 'Failed to start processing',
        }), 500
