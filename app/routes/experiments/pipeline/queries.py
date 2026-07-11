"""Experiment pipeline status and artifact query endpoints."""

import logging

from flask import jsonify
from flask_login import current_user, login_required

from app.services.base_service import NotFoundError, PermissionError, ServiceError

from .. import experiments_bp
from . import pipeline_service


logger = logging.getLogger(__name__)


@experiments_bp.route('/api/experiment-document/<int:exp_doc_id>/processing-status')
@login_required
def get_experiment_document_processing_status(exp_doc_id):
    """Return processing status for an experiment document."""
    try:
        result = pipeline_service.get_processing_status(
            exp_doc_id,
            current_user.id,
        )
        return jsonify({
            'success': True,
            'experiment_document_id': result['experiment_document_id'],
            'processing_operations': result['processing_operations'],
        }), 200
    except NotFoundError as exc:
        logger.warning(f"Experiment document {exp_doc_id} not found: {exc}")
        return jsonify({
            'success': False,
            'error': 'Experiment document not found',
        }), 404
    except PermissionError:
        return jsonify({'success': False, 'error': 'Permission denied'}), 403
    except ServiceError as exc:
        logger.error(
            f"Service error getting processing status: {exc}",
            exc_info=True,
        )
        return jsonify({
            'success': False,
            'error': 'Failed to get processing status',
        }), 500
    except Exception as exc:
        logger.error(
            f"Unexpected error getting processing status: {exc}",
            exc_info=True,
        )
        return jsonify({
            'success': False,
            'error': 'Failed to get processing status',
        }), 500


@experiments_bp.route('/api/processing/<uuid:processing_id>/artifacts')
@login_required
def get_processing_artifacts(processing_id):
    """Return artifacts for a processing operation."""
    try:
        result = pipeline_service.get_processing_artifacts(
            processing_id,
            current_user.id,
        )
        return jsonify({
            'success': True,
            'processing_id': result['processing_id'],
            'processing_type': result['processing_type'],
            'processing_method': result['processing_method'],
            'artifacts': result['artifacts'],
        }), 200
    except NotFoundError as exc:
        logger.warning(f"Processing {processing_id} not found: {exc}")
        return jsonify({
            'success': False,
            'error': 'Processing operation not found',
        }), 404
    except PermissionError:
        return jsonify({'success': False, 'error': 'Permission denied'}), 403
    except ServiceError as exc:
        logger.error(
            f"Service error getting processing artifacts: {exc}",
            exc_info=True,
        )
        return jsonify({
            'success': False,
            'error': 'Failed to get processing artifacts',
        }), 500
    except Exception as exc:
        logger.error(
            f"Unexpected error getting processing artifacts: {exc}",
            exc_info=True,
        )
        return jsonify({
            'success': False,
            'error': 'Failed to get processing artifacts',
        }), 500
