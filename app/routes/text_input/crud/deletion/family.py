"""Document-family deletion routes."""

from flask import current_app, flash, jsonify, redirect, request, url_for

from app.services.document_deletion_service import DocumentDeletionService
from app.utils.auth_decorators import api_require_login_for_write

from ... import text_input_bp


@text_input_bp.route(
    '/document/<int:base_document_id>/delete-all-versions',
    methods=['POST'],
)
@api_require_login_for_write
def delete_all_versions(base_document_id):
    """Delete every version in a document family."""
    try:
        result = DocumentDeletionService.delete_family(
            base_document_id,
            current_app.logger,
        )
        if request.is_json:
            return jsonify({'success': True, **result})
        flash(
            f"Successfully deleted {result['deleted_count']} document versions",
            'success',
        )
        return redirect(url_for('text_input.document_list'))
    except Exception as exc:
        current_app.logger.error(
            f"Error deleting document family {base_document_id}: {exc}"
        )
        if request.is_json:
            return jsonify({'success': False, 'error': str(exc)}), 500
        flash('An error occurred while deleting the document family', 'error')
        return redirect(url_for('text_input.document_list'))
