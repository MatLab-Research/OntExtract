"""
Processing Validation and Testing Routes

This module handles validation and testing utilities for processing operations.

Routes:
- POST /processing/document/<id>/clear-jobs - Clear processing jobs (testing utility)
"""

from flask import jsonify
from flask_login import current_user
from app.utils.auth_decorators import api_require_login_for_write
from app import db
from app.models.document import Document
from app.models.processing_job import ProcessingJob

from . import processing_bp


@processing_bp.route('/document/<int:document_id>/clear-jobs', methods=['POST'])
@api_require_login_for_write
def clear_document_jobs(document_id):
    """Clear all processing jobs for a document (for testing purposes)"""
    try:
        document = Document.query.get_or_404(document_id)

        # Delete all processing jobs for this document by the current user
        deleted_count = (
            ProcessingJob.query
            .filter_by(document_id=document_id, user_id=current_user.id)
            .delete()
        )

        db.session.commit()

        return jsonify({
            'success': True,
            'deleted_count': deleted_count,
            'message': f'Cleared {deleted_count} processing jobs for this document'
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
