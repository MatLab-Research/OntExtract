"""Administrative all-document purge route."""

from flask import current_app, jsonify
from flask_login import current_user

from app.services.document_purge_service import DocumentPurgeService
from app.utils.auth_decorators import write_login_required

from ... import text_input_bp


@text_input_bp.route('/documents/delete-all', methods=['POST'])
@write_login_required
def delete_all_documents():
    """Delete every document and dependent record; administrators only."""
    if not current_user.is_admin:
        current_app.logger.warning(
            f"Non-admin user {current_user.id} attempted to delete all documents"
        )
        return jsonify({
            'success': False,
            'error': 'Admin access required'
        }), 403

    try:
        result = DocumentPurgeService.purge_all(
            current_user.id,
            current_app.logger,
        )
        if not result['success']:
            return jsonify(result), result['status']
        return jsonify({
            'success': True,
            'message': (
                f"Successfully deleted {result['details']['documents']} documents "
                'and all related data'
            ),
            'details': result['details'],
        })
    except Exception as exc:
        DocumentPurgeService.rollback()
        current_app.logger.error(
            f"Error during delete all documents: {exc}",
            exc_info=True,
        )
        return jsonify({
            'success': False,
            'error': f'An error occurred while deleting documents: {exc}'
        }), 500
