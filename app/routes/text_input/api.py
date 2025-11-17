"""
Text Input API Routes

This module handles API endpoints for document access.

Routes:
- GET /input/api/document/<id>/content - Get document content
- GET /input/api/documents             - List documents
- GET /input/document/<uuid>/metadata  - Get document metadata (public)
- PUT /input/document/<uuid>/metadata  - Update document metadata (requires auth)

Metadata Architecture:
- source_metadata (JSONB on Document): Canonical bibliographic metadata
  - User-editable via this API
  - Displayed in document views
  - Fields: title, authors, publication_date, journal, publisher, type, doi, isbn, url, abstract, citation

- DocumentTemporalMetadata (separate table): Experiment-specific temporal analysis
  - Only used for semantic drift experiments
  - NOT editable via this API
  - Fields: publication_year, discipline, key_definition, temporal_period, etc.
  - Edited separately in experiment context
"""

from flask import request, jsonify
from flask_login import current_user

from app import db
from app.models.document import Document
from app.utils.auth_decorators import api_require_login_for_write, write_login_required

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


@text_input_bp.route('/document/<uuid:document_uuid>/metadata', methods=['GET'])
def get_document_metadata(document_uuid):
    """Get document metadata - public access for viewing

    Returns ONLY source_metadata (canonical bibliographic metadata).
    DocumentTemporalMetadata is kept completely separate for experiment-specific analysis.
    """
    try:
        document = Document.query.filter_by(uuid=document_uuid).first_or_404()

        # Return source_metadata only - no mixing with temporal data
        metadata = document.source_metadata if document.source_metadata else {}

        return jsonify({
            'success': True,
            'metadata': metadata
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@text_input_bp.route('/document/<uuid:document_uuid>/metadata', methods=['PUT'])
@write_login_required
def update_document_metadata(document_uuid):
    """Update document metadata - requires authentication"""
    try:
        document = Document.query.filter_by(uuid=document_uuid).first_or_404()

        # Check permission - only owner or admin can update
        if not current_user.can_edit_resource(document):
            return jsonify({'success': False, 'error': 'Permission denied'}), 403

        # Get metadata from request
        metadata = request.get_json()

        if not metadata:
            return jsonify({'success': False, 'error': 'No metadata provided'}), 400

        # Initialize source_metadata if it doesn't exist
        if not document.source_metadata:
            document.source_metadata = {}

        # Update source_metadata with provided fields
        for field in ['title', 'authors', 'publication_date', 'journal', 'publisher',
                      'type', 'doi', 'isbn', 'url', 'abstract', 'citation']:
            if field in metadata and metadata[field]:
                document.source_metadata[field] = metadata[field]

        # Mark the change for SQLAlchemy
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(document, 'source_metadata')

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Metadata updated successfully',
            'metadata': document.source_metadata
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
