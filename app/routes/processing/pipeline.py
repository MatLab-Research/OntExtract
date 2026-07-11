"""Processing entry-point compatibility routes."""

from flask import jsonify

from app import db
from app.models.document import Document
from app.utils.auth_decorators import require_login_for_write

from . import processing_bp


@processing_bp.route('/processing/start/<int:document_id>')
@processing_bp.route('/start/<int:document_id>')
@require_login_for_write
def start_processing(document_id):
    """Return a clear unsupported response for the start-processing endpoint."""
    document = db.session.get(Document, document_id)
    if document is None:
        return jsonify({
            'error': 'Document not found',
            'message': f'No document exists with id {document_id}.'
        }), 404

    return jsonify({
        'error': 'Processing startup is not implemented',
        'message': 'The processing workflow is not implemented yet. Use the existing manual processing actions in the UI.',
        'document_id': document.id,
        'document_title': document.title
    }), 501
