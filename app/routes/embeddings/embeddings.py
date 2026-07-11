"""Embedding diagnostics API routes."""

import logging

from flask import jsonify
from flask_login import current_user

from app.services.base_service import NotFoundError, PermissionError
from app.services.embedding_diagnostics_service import EmbeddingDiagnosticsService
from app.utils.auth_decorators import api_require_login_for_write

from . import embeddings_bp


logger = logging.getLogger(__name__)


def _document_diagnostic(method, document_id):
    try:
        return jsonify(method(document_id))
    except NotFoundError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 404
    except Exception as exc:
        logger.error(
            f'Embedding diagnostic failed for document {document_id}: {exc}',
            exc_info=True,
        )
        return jsonify({'success': False, 'error': str(exc)}), 500


@embeddings_bp.route('/document/<int:document_id>')
@api_require_login_for_write
def get_document_embeddings(document_id):
    """Return embedding metadata for a document family."""
    return _document_diagnostic(
        EmbeddingDiagnosticsService.get_document_info,
        document_id,
    )


@embeddings_bp.route('/document/<int:document_id>/sample')
@api_require_login_for_write
def get_embedding_sample(document_id):
    """Return real stored vector samples or honest legacy metadata."""
    return _document_diagnostic(
        EmbeddingDiagnosticsService.get_sample,
        document_id,
    )


@embeddings_bp.route('/document/<int:document_id>/verify')
@api_require_login_for_write
def verify_embeddings(document_id):
    """Return family-wide embedding validation metrics."""
    return _document_diagnostic(
        EmbeddingDiagnosticsService.verify,
        document_id,
    )


@embeddings_bp.route('/jobs/<int:job_id>')
@api_require_login_for_write
def get_job_details(job_id):
    """Return an embedding job visible to the current user."""
    try:
        return jsonify(EmbeddingDiagnosticsService.get_job_details(
            job_id,
            current_user.id,
        ))
    except NotFoundError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 404
    except PermissionError as exc:
        return jsonify({'error': str(exc)}), 403
    except Exception as exc:
        logger.error(
            f'Error getting embedding job details for {job_id}: {exc}',
            exc_info=True,
        )
        return jsonify({'success': False, 'error': str(exc)}), 500
