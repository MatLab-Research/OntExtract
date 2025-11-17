"""
Text Input API Routes

This module handles API endpoints for document access.

Routes:
- GET /input/api/document/<id>/content - Get document content
- GET /input/api/documents             - List documents
- GET /input/document/<uuid>/metadata  - Get document metadata (public)
- PUT /input/document/<uuid>/metadata  - Update document metadata (requires auth)

Metadata Architecture (Hybrid Normalized + JSONB):

- Normalized Columns (Standard Bibliographic Fields):
  - title, authors, publication_date, journal, publisher, doi, isbn
  - document_subtype, abstract, url, citation
  - Stored as database columns for better performance and validation
  - User-editable via this API
  - Displayed in document views

- source_metadata (JSONB): Custom/non-standard metadata only
  - Reserved for domain-specific or unusual metadata fields
  - Examples: conference_location, dataset_doi, presentation_type
  - Flexible storage for fields not covered by standard bibliographic schema

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

    Returns normalized bibliographic fields from database columns,
    plus any custom fields from source_metadata JSONB.
    """
    try:
        document = Document.query.filter_by(uuid=document_uuid).first_or_404()

        # Build metadata from normalized columns
        metadata = {
            'title': document.title,
            'authors': document.authors,
            'publication_date': document.publication_date.isoformat() if document.publication_date else None,
            'journal': document.journal,
            'publisher': document.publisher,
            'doi': document.doi,
            'isbn': document.isbn,
            'type': document.document_subtype,
            'abstract': document.abstract,
            'url': document.url,
            'citation': document.citation
        }

        # Add custom fields from source_metadata JSONB (if any)
        if document.source_metadata:
            for key, value in document.source_metadata.items():
                if key not in metadata:  # Don't override standard fields
                    metadata[key] = value

        # Remove None values for cleaner response
        metadata = {k: v for k, v in metadata.items() if v is not None}

        return jsonify({
            'success': True,
            'metadata': metadata
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@text_input_bp.route('/document/<uuid:document_uuid>/metadata', methods=['PUT'])
@write_login_required
def update_document_metadata(document_uuid):
    """Update document metadata - requires authentication

    Updates normalized bibliographic fields in database columns.
    Any non-standard fields are stored in source_metadata JSONB.
    """
    try:
        from datetime import datetime
        from dateutil import parser as date_parser

        document = Document.query.filter_by(uuid=document_uuid).first_or_404()

        # Check permission - only owner or admin can update
        if not current_user.can_edit_resource(document):
            return jsonify({'success': False, 'error': 'Permission denied'}), 403

        # Get metadata from request
        metadata = request.get_json()

        if not metadata:
            return jsonify({'success': False, 'error': 'No metadata provided'}), 400

        # Standard fields that map to database columns
        standard_fields = {
            'title', 'authors', 'publication_date', 'journal', 'publisher',
            'doi', 'isbn', 'type', 'abstract', 'url', 'citation'
        }

        # Update normalized column fields
        if 'title' in metadata and metadata['title']:
            document.title = str(metadata['title'])[:200]

        if 'authors' in metadata and metadata['authors']:
            document.authors = str(metadata['authors'])

        if 'publication_date' in metadata and metadata['publication_date']:
            try:
                # Parse date string to date object
                parsed_date = date_parser.parse(metadata['publication_date'])
                document.publication_date = parsed_date.date()
            except:
                pass  # Skip invalid dates

        if 'journal' in metadata and metadata['journal']:
            document.journal = str(metadata['journal'])[:200]

        if 'publisher' in metadata and metadata['publisher']:
            document.publisher = str(metadata['publisher'])[:200]

        if 'doi' in metadata and metadata['doi']:
            document.doi = str(metadata['doi'])[:100]

        if 'isbn' in metadata and metadata['isbn']:
            document.isbn = str(metadata['isbn'])[:20]

        if 'type' in metadata and metadata['type']:
            document.document_subtype = str(metadata['type'])[:50]

        if 'abstract' in metadata and metadata['abstract']:
            document.abstract = str(metadata['abstract'])

        if 'url' in metadata and metadata['url']:
            document.url = str(metadata['url'])[:500]

        if 'citation' in metadata and metadata['citation']:
            document.citation = str(metadata['citation'])

        # Handle custom (non-standard) fields in source_metadata JSONB
        custom_fields = {k: v for k, v in metadata.items() if k not in standard_fields}

        if custom_fields:
            # Initialize source_metadata if needed
            if not document.source_metadata:
                document.source_metadata = {}

            # Add custom fields
            document.source_metadata.update(custom_fields)

            # Mark JSONB field as modified
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(document, 'source_metadata')

        db.session.commit()

        # Return complete metadata (columns + JSONB)
        response_metadata = {
            'title': document.title,
            'authors': document.authors,
            'publication_date': document.publication_date.isoformat() if document.publication_date else None,
            'journal': document.journal,
            'publisher': document.publisher,
            'doi': document.doi,
            'isbn': document.isbn,
            'type': document.document_subtype,
            'abstract': document.abstract,
            'url': document.url,
            'citation': document.citation
        }

        # Add custom fields
        if document.source_metadata:
            response_metadata.update(document.source_metadata)

        # Remove None values
        response_metadata = {k: v for k, v in response_metadata.items() if v is not None}

        return jsonify({
            'success': True,
            'message': 'Metadata updated successfully',
            'metadata': response_metadata
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
