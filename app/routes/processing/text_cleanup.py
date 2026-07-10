"""Asynchronous text cleanup and reviewed-text persistence routes."""

from flask import current_app, jsonify, request
from flask_login import current_user

from app.services.base_service import NotFoundError, ValidationError
from app.services.document_cleanup_workflow import DocumentCleanupWorkflow
from app.utils.auth_decorators import api_require_login_for_write

from . import processing_bp


cleanup_workflow = DocumentCleanupWorkflow()


@processing_bp.route('/document/<string:document_uuid>/clean-text', methods=['POST'])
@api_require_login_for_write
def clean_text(document_uuid):
    """Start asynchronous LLM cleanup for a document."""
    try:
        document = cleanup_workflow.get_document(document_uuid)
        result = cleanup_workflow.start_cleanup(
            document,
            current_user.id,
            current_app._get_current_object(),
        )
        return jsonify(result)
    except NotFoundError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 404
    except ValidationError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    except Exception as exc:
        return jsonify({'success': False, 'error': str(exc)}), 500


@processing_bp.route(
    '/document/<string:document_uuid>/save-cleaned-text',
    methods=['POST'],
)
@api_require_login_for_write
def save_cleaned_text(document_uuid):
    """Persist reviewed text as a canonical cleaned document version."""
    try:
        document = cleanup_workflow.get_document(document_uuid)
        result = cleanup_workflow.save_reviewed_cleanup(
            document,
            request.get_json(),
            current_user.id,
        )
        return jsonify(result)
    except NotFoundError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 404
    except ValidationError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    except Exception as exc:
        return jsonify({'success': False, 'error': str(exc)}), 500
