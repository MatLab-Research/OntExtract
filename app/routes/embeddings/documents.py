"""Document embedding and segmentation artifact APIs."""

import logging

from flask import jsonify

from app.services.base_service import NotFoundError
from app.services.document_artifact_service import DocumentArtifactService
from app.utils.auth_decorators import api_require_login_for_write

from . import document_api_bp


logger = logging.getLogger(__name__)


@document_api_bp.route('/<int:document_id>/embeddings')
@api_require_login_for_write
def get_document_embeddings_new(document_id):
    """Return unified and legacy embeddings for a document family."""
    try:
        return jsonify(DocumentArtifactService.get_embeddings(document_id))
    except NotFoundError as exc:
        return jsonify({
            'success': False,
            'error': str(exc),
            'embeddings': [],
        }), 404
    except Exception as exc:
        logger.error(f'Error getting embeddings for document {document_id}: {exc}')
        return jsonify({
            'success': False,
            'error': str(exc),
            'embeddings': [],
        }), 500


@document_api_bp.route('/embedding/<embedding_id>/preview')
@api_require_login_for_write
def get_embedding_preview(embedding_id):
    """Return an artifact or legacy-job embedding preview."""
    try:
        return jsonify(DocumentArtifactService.get_embedding_preview(embedding_id))
    except NotFoundError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 404
    except Exception as exc:
        logger.error(f'Error getting embedding preview for {embedding_id}: {exc}')
        return jsonify({'success': False, 'error': str(exc)}), 500


@document_api_bp.route('/<int:document_id>/segments')
@api_require_login_for_write
def get_document_segments(document_id):
    """Return document-family segments grouped by segmentation method."""
    try:
        return jsonify(DocumentArtifactService.get_segments(document_id))
    except NotFoundError as exc:
        return jsonify({
            'success': False,
            'error': str(exc),
            'segmentation_methods': [],
        }), 404
    except Exception as exc:
        logger.error(f'Error getting segments for document {document_id}: {exc}')
        return jsonify({
            'success': False,
            'error': str(exc),
            'segmentation_methods': [],
        }), 500
