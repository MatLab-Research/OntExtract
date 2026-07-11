"""HTTP adapters for document segmentation workflows."""

from flask import current_app, jsonify, request
from flask_login import current_user

from app.services.base_service import (
    NotFoundError,
    PermissionError,
    ServiceError,
    ValidationError,
)
from app.services.document_segmentation_service import DocumentSegmentationService
from app.utils.auth_decorators import api_require_login_for_write

from .. import processing_bp
from .langextract import run_langextract_segmentation
from .traditional import run_traditional_segmentation
from .versioning import get_segmentation_version


def _service():
    return DocumentSegmentationService(
        get_segmentation_version,
        run_traditional_segmentation,
        run_langextract_segmentation,
        current_app.logger,
    )


def _error(message, status):
    return jsonify({'success': False, 'error': str(message)}), status


@processing_bp.route('/document/<string:document_uuid>/segment', methods=['POST'])
@api_require_login_for_write
def segment_document(document_uuid):
    try:
        payload, status = _service().segment(
            document_uuid,
            request.get_json(silent=True),
            current_user.id,
        )
        return jsonify(payload), status
    except NotFoundError as exc:
        return _error(exc, 404)
    except PermissionError as exc:
        return _error(exc, 403)
    except ValidationError as exc:
        return _error(exc, 400)
    except ServiceError as exc:
        current_app.logger.error(str(exc), exc_info=True)
        return _error('Document segmentation failed', 500)


@processing_bp.route('/document/<int:document_id>/segments', methods=['DELETE'])
@api_require_login_for_write
def delete_document_segments(document_id):
    try:
        return jsonify(DocumentSegmentationService.delete_segments(
            document_id,
            current_user.id,
        ))
    except NotFoundError as exc:
        return _error(exc, 404)
    except PermissionError as exc:
        return _error(exc, 403)
    except ValidationError as exc:
        return _error(exc, 400)
    except ServiceError as exc:
        current_app.logger.error(str(exc), exc_info=True)
        return _error('Failed to delete document segments', 500)
