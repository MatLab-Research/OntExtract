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

    For version documents, returns the root document's metadata since
    metadata is inherited and displayed from the root.
    """
    try:
        document = Document.query.filter_by(uuid=document_uuid).first_or_404()

        # For version documents, get metadata from root document
        root_doc = document.get_root_document()
        is_version = (root_doc.id != document.id)

        # Use root document for metadata if this is a version
        metadata_doc = root_doc if is_version else document

        # Build metadata from normalized columns
        metadata = {
            'title': metadata_doc.title,
            'authors': metadata_doc.display_authors,  # Use display_authors for proper formatting
            'publication_date': metadata_doc.publication_date.isoformat() if metadata_doc.publication_date else None,
            'journal': metadata_doc.journal,
            'publisher': metadata_doc.publisher,
            'doi': metadata_doc.doi,
            'isbn': metadata_doc.isbn,
            'type': metadata_doc.document_subtype,
            'abstract': metadata_doc.abstract,
            'url': metadata_doc.url,
            'citation': metadata_doc.citation,
            # Extended bibliographic fields
            'editor': metadata_doc.editor,
            'edition': metadata_doc.edition,
            'volume': metadata_doc.volume,
            'issue': metadata_doc.issue,
            'pages': metadata_doc.pages,
            'series': metadata_doc.series,
            'container_title': metadata_doc.container_title,
            'place': metadata_doc.place,
            'issn': metadata_doc.issn,
            'access_date': metadata_doc.access_date.isoformat() if metadata_doc.access_date else None,
            'entry_term': metadata_doc.entry_term,
            'notes': metadata_doc.notes
        }

        # Add custom fields from source_metadata JSONB (if any)
        if metadata_doc.source_metadata:
            for key, value in metadata_doc.source_metadata.items():
                if key not in metadata:  # Don't override standard fields
                    metadata[key] = value

        # Remove None values for cleaner response
        metadata = {k: v for k, v in metadata.items() if v is not None}

        return jsonify({
            'success': True,
            'metadata': metadata,
            'is_version': is_version,
            'root_uuid': root_doc.uuid if is_version else None
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
            'doi', 'isbn', 'type', 'abstract', 'url', 'citation',
            # Extended bibliographic fields
            'editor', 'edition', 'volume', 'issue', 'pages', 'series',
            'container_title', 'place', 'issn', 'access_date', 'entry_term', 'notes'
        }

        # Track changes for provenance
        changes = {}

        # Update normalized column fields and track changes
        if 'title' in metadata and metadata['title']:
            new_value = str(metadata['title'])[:200]
            if document.title != new_value:
                changes['title'] = {'old': document.title, 'new': new_value}
                document.title = new_value

        if 'authors' in metadata and metadata['authors']:
            new_value = str(metadata['authors'])
            if document.authors != new_value:
                changes['authors'] = {'old': document.authors, 'new': new_value}
                document.authors = new_value

        if 'publication_date' in metadata and metadata['publication_date']:
            try:
                # Parse date string to date object
                parsed_date = date_parser.parse(metadata['publication_date'])
                new_value = parsed_date.date()
                if document.publication_date != new_value:
                    changes['publication_date'] = {
                        'old': document.publication_date.isoformat() if document.publication_date else None,
                        'new': new_value.isoformat()
                    }
                    document.publication_date = new_value
            except:
                pass  # Skip invalid dates

        if 'journal' in metadata and metadata['journal']:
            new_value = str(metadata['journal'])[:200]
            if document.journal != new_value:
                changes['journal'] = {'old': document.journal, 'new': new_value}
                document.journal = new_value

        if 'publisher' in metadata and metadata['publisher']:
            new_value = str(metadata['publisher'])[:200]
            if document.publisher != new_value:
                changes['publisher'] = {'old': document.publisher, 'new': new_value}
                document.publisher = new_value

        if 'doi' in metadata and metadata['doi']:
            new_value = str(metadata['doi'])[:100]
            if document.doi != new_value:
                changes['doi'] = {'old': document.doi, 'new': new_value}
                document.doi = new_value

        if 'isbn' in metadata and metadata['isbn']:
            new_value = str(metadata['isbn'])[:20]
            if document.isbn != new_value:
                changes['isbn'] = {'old': document.isbn, 'new': new_value}
                document.isbn = new_value

        if 'type' in metadata and metadata['type']:
            new_value = str(metadata['type'])[:50]
            if document.document_subtype != new_value:
                changes['type'] = {'old': document.document_subtype, 'new': new_value}
                document.document_subtype = new_value

        if 'abstract' in metadata and metadata['abstract']:
            new_value = str(metadata['abstract'])
            if document.abstract != new_value:
                changes['abstract'] = {'old': document.abstract, 'new': new_value}
                document.abstract = new_value

        if 'url' in metadata and metadata['url']:
            new_value = str(metadata['url'])[:500]
            if document.url != new_value:
                changes['url'] = {'old': document.url, 'new': new_value}
                document.url = new_value

        if 'citation' in metadata and metadata['citation']:
            new_value = str(metadata['citation'])
            if document.citation != new_value:
                changes['citation'] = {'old': document.citation, 'new': new_value}
                document.citation = new_value

        # Extended bibliographic fields
        if 'editor' in metadata:
            new_value = str(metadata['editor']) if metadata['editor'] else None
            if document.editor != new_value:
                changes['editor'] = {'old': document.editor, 'new': new_value}
                document.editor = new_value

        if 'edition' in metadata:
            new_value = str(metadata['edition'])[:50] if metadata['edition'] else None
            if document.edition != new_value:
                changes['edition'] = {'old': document.edition, 'new': new_value}
                document.edition = new_value

        if 'volume' in metadata:
            new_value = str(metadata['volume'])[:20] if metadata['volume'] else None
            if document.volume != new_value:
                changes['volume'] = {'old': document.volume, 'new': new_value}
                document.volume = new_value

        if 'issue' in metadata:
            new_value = str(metadata['issue'])[:20] if metadata['issue'] else None
            if document.issue != new_value:
                changes['issue'] = {'old': document.issue, 'new': new_value}
                document.issue = new_value

        if 'pages' in metadata:
            new_value = str(metadata['pages'])[:50] if metadata['pages'] else None
            if document.pages != new_value:
                changes['pages'] = {'old': document.pages, 'new': new_value}
                document.pages = new_value

        if 'series' in metadata:
            new_value = str(metadata['series'])[:200] if metadata['series'] else None
            if document.series != new_value:
                changes['series'] = {'old': document.series, 'new': new_value}
                document.series = new_value

        if 'container_title' in metadata:
            new_value = str(metadata['container_title'])[:300] if metadata['container_title'] else None
            if document.container_title != new_value:
                changes['container_title'] = {'old': document.container_title, 'new': new_value}
                document.container_title = new_value

        if 'place' in metadata:
            new_value = str(metadata['place'])[:100] if metadata['place'] else None
            if document.place != new_value:
                changes['place'] = {'old': document.place, 'new': new_value}
                document.place = new_value

        if 'issn' in metadata:
            new_value = str(metadata['issn'])[:20] if metadata['issn'] else None
            if document.issn != new_value:
                changes['issn'] = {'old': document.issn, 'new': new_value}
                document.issn = new_value

        if 'access_date' in metadata and metadata['access_date']:
            try:
                parsed_date = date_parser.parse(metadata['access_date'])
                new_value = parsed_date.date()
                if document.access_date != new_value:
                    changes['access_date'] = {
                        'old': document.access_date.isoformat() if document.access_date else None,
                        'new': new_value.isoformat()
                    }
                    document.access_date = new_value
            except:
                pass  # Skip invalid dates

        if 'entry_term' in metadata:
            new_value = str(metadata['entry_term'])[:200] if metadata['entry_term'] else None
            if document.entry_term != new_value:
                changes['entry_term'] = {'old': document.entry_term, 'new': new_value}
                document.entry_term = new_value

        if 'notes' in metadata:
            new_value = str(metadata['notes']) if metadata['notes'] else None
            if document.notes != new_value:
                changes['notes'] = {'old': document.notes, 'new': new_value}
                document.notes = new_value

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

        # Track metadata update in provenance if there were changes
        if changes:
            try:
                from app.services.provenance_service import provenance_service
                provenance_service.track_metadata_update(document, current_user, changes)
            except Exception as e:
                # Log but don't fail the request if provenance tracking fails
                from flask import current_app
                current_app.logger.warning(f"Failed to track metadata update provenance: {str(e)}")

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
            'citation': document.citation,
            # Extended bibliographic fields
            'editor': document.editor,
            'edition': document.edition,
            'volume': document.volume,
            'issue': document.issue,
            'pages': document.pages,
            'series': document.series,
            'container_title': document.container_title,
            'place': document.place,
            'issn': document.issn,
            'access_date': document.access_date.isoformat() if document.access_date else None,
            'entry_term': document.entry_term,
            'notes': document.notes
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
