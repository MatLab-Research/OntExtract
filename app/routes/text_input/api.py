"""
Text Input API Routes

This module handles API endpoints for document access.

Routes:
- GET /input/api/document/<id>/content - Get document content
- GET /input/api/documents             - List documents
"""

from flask import request, jsonify

from app.models.document import Document
from app.utils.auth_decorators import api_require_login_for_write

from . import text_input_bp


@text_input_bp.route('/api/document/<int:document_id>/content')
@api_require_login_for_write
def api_document_content(document_id):
    """API endpoint to get document content"""
    document = Document.query.filter_by(id=document_id).first_or_404()
    return jsonify(document.to_dict(include_content=True))


@text_input_bp.route('/api/documents')
@api_require_login_for_write
def api_document_list():
    """API endpoint to list user's documents"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    documents = Document.query\
        .order_by(Document.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'documents': [doc.to_dict() for doc in documents.items],
        'total': documents.total,
        'pages': documents.pages,
        'current_page': documents.page,
        'has_next': documents.has_next,
        'has_prev': documents.has_prev
    })
