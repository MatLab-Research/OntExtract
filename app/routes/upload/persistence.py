"""Reviewed upload persistence and provenance routes."""

from datetime import datetime
import os

from flask import current_app, jsonify, request
from flask_login import current_user

from app import db
from app.models.document import Document
from app.utils.auth_decorators import api_require_login_for_write

from . import upload_bp


@upload_bp.route('/save_document', methods=['POST'])
@api_require_login_for_write
def save_document():
    """Save document after metadata review"""
    from app.services.upload_service import upload_service
    import json

    try:
        data = request.get_json()

        # Get metadata and provenance from request
        metadata = data.get('metadata', {})
        provenance = data.get('provenance', {})
        temp_path = data.get('temp_path')
        filename = data.get('filename')

        if not temp_path:
            return jsonify({'error': 'No document file to save'}), 400

        # Validate required fields
        if not metadata.get('title'):
            return jsonify({'error': 'Title is required'}), 400

        # Create upload directory
        upload_dir = current_app.config.get('UPLOAD_FOLDER', 'uploads')

        # Save permanently
        save_result = upload_service.save_permanent(temp_path, upload_dir, filename)
        if not save_result.success:
            return jsonify({'error': save_result.error}), 400

        final_path = save_result.file_path

        # Extract text content for the document
        content, error, extraction_method = upload_service.extract_text_content(final_path, filename)
        if error:
            return jsonify({'error': error}), 400

        # Parse publication date if provided (supports year, year-month, or full date)
        publication_date = None
        if metadata.get('publication_year'):
            from app.utils.date_parser import parse_flexible_date
            publication_date = parse_flexible_date(metadata.get('publication_year'))

        # Convert authors list to comma-separated string if needed
        authors = metadata.get('authors')
        if isinstance(authors, list):
            authors = ', '.join(authors) if authors else None

        # Helper function to convert empty strings to None
        def clean_metadata_value(value):
            """Convert empty strings to None for database nullable fields"""
            if value == '' or value is None:
                return None
            return value

        # Parse access_date if provided
        access_date = None
        if metadata.get('access_date'):
            from app.utils.date_parser import parse_flexible_date
            access_date = parse_flexible_date(metadata.get('access_date'))

        # Create document record with normalized columns
        document = Document(
            title=metadata.get('title', filename),
            content_type='file',
            file_type='pdf',
            original_filename=filename,
            file_path=final_path,
            file_size=os.path.getsize(final_path),
            content=content,
            # Normalized bibliographic columns
            authors=authors,  # Store as comma-separated string
            publication_date=publication_date,
            journal=clean_metadata_value(metadata.get('journal')),
            publisher=clean_metadata_value(metadata.get('publisher')),
            doi=clean_metadata_value(metadata.get('doi')),
            isbn=clean_metadata_value(metadata.get('isbn')),
            document_subtype=clean_metadata_value(metadata.get('type')),
            abstract=clean_metadata_value(metadata.get('abstract')),
            url=clean_metadata_value(metadata.get('url')),
            citation=clean_metadata_value(metadata.get('citation')),
            # Extended bibliographic columns (Zotero-aligned)
            editor=clean_metadata_value(metadata.get('editor')),
            edition=clean_metadata_value(metadata.get('edition')),
            volume=clean_metadata_value(metadata.get('volume')),
            issue=clean_metadata_value(metadata.get('issue')),
            pages=clean_metadata_value(metadata.get('pages')),
            issn=clean_metadata_value(metadata.get('issn')),
            container_title=clean_metadata_value(metadata.get('container_title')),
            place=clean_metadata_value(metadata.get('place')),
            series=clean_metadata_value(metadata.get('series')),
            entry_term=clean_metadata_value(metadata.get('entry_term')),
            access_date=access_date,
            notes=clean_metadata_value(metadata.get('notes')),
            # Legacy source_metadata for custom fields only
            source_metadata={'extraction_source': 'enhanced_upload'},
            metadata_provenance=provenance,
            status='uploaded',
            user_id=current_user.id
        )

        db.session.add(document)
        db.session.flush()  # Get document ID

        # Create temporal metadata if publication_year is provided
        if metadata.get('publication_year'):
            from app.models import DocumentTemporalMetadata

            temporal_metadata = DocumentTemporalMetadata(
                document_id=document.id,
                publication_year=metadata.get('publication_year'),
                discipline=metadata.get('discipline'),  # If provided in form
                key_definition=metadata.get('abstract'),  # Use abstract as key definition if available
                created_at=datetime.utcnow()
            )
            db.session.add(temporal_metadata)

        db.session.commit()

        # Track document lifecycle with PROV-O (granular tracking)
        try:
            from app.services.provenance_service import provenance_service

            # 1. Track initial file upload
            provenance_service.track_document_upload(document, current_user)

            # 2. Track text extraction
            provenance_service.track_text_extraction(
                document,
                current_user,
                source_format='pdf',
                extraction_method=extraction_method or 'unknown'
            )

            # 3. Track PDF identifier extraction if DOI was found
            if provenance and provenance.get('extracted_doi'):
                extracted_identifiers = {
                    'doi': provenance['extracted_doi'].get('raw_value', '')
                }
                if provenance.get('extracted_title'):
                    extracted_identifiers['title'] = provenance['extracted_title'].get('raw_value', '')

                provenance_service.track_metadata_extraction_pdf(
                    document,
                    current_user,
                    extracted_identifiers=extracted_identifiers
                )

            # 4. Track metadata extraction for all sources
            if provenance:
                # Collect fields by source
                source_fields = {
                    'crossref': {},
                    'semanticscholar': {},
                    'zotero': {},
                    'pdf_analysis': {},
                    'user': {},
                    'manual': {}
                }

                for field_name, prov_data in provenance.items():
                    if isinstance(prov_data, dict):
                        source = prov_data.get('source', '')
                        raw_value = prov_data.get('raw_value')

                        # Map source names to our tracking categories
                        if source in ['crossref', 'crossref_auto']:
                            source_fields['crossref'][field_name] = raw_value
                        elif source == 'semanticscholar':
                            source_fields['semanticscholar'][field_name] = raw_value
                        elif source == 'zotero':
                            source_fields['zotero'][field_name] = raw_value
                        elif source in ['pdf_analysis', 'file']:
                            source_fields['pdf_analysis'][field_name] = raw_value
                        elif source == 'user':
                            source_fields['user'][field_name] = raw_value
                        elif source == 'manual':
                            source_fields['manual'][field_name] = raw_value

                # Track CrossRef extraction
                if source_fields['crossref']:
                    confidence = provenance.get('match_score', {}).get('raw_value', 0.9) if 'match_score' in provenance else 0.9
                    provenance_service.track_metadata_extraction(
                        document, current_user, 'crossref', source_fields['crossref'], confidence
                    )

                # Track Semantic Scholar extraction
                if source_fields['semanticscholar']:
                    confidence = provenance.get('match_score', {}).get('raw_value', 0.9) if 'match_score' in provenance else 0.9
                    provenance_service.track_metadata_extraction(
                        document, current_user, 'semanticscholar', source_fields['semanticscholar'], confidence
                    )

                # Track Zotero extraction
                if source_fields['zotero']:
                    provenance_service.track_metadata_extraction(
                        document, current_user, 'zotero', source_fields['zotero'], 0.95
                    )

                # Track PDF analysis extraction
                if source_fields['pdf_analysis']:
                    provenance_service.track_metadata_extraction(
                        document, current_user, 'pdf_analysis', source_fields['pdf_analysis'], 0.7
                    )

                # Track user-provided metadata (entered during initial upload)
                if source_fields['user']:
                    provenance_service.track_metadata_extraction(
                        document, current_user, 'user', source_fields['user'], 1.0
                    )

                # Track manual entries (added to supplement auto-extracted data)
                if source_fields['manual']:
                    provenance_service.track_metadata_extraction(
                        document, current_user, 'manual', source_fields['manual'], 1.0
                    )

            # 5. Track document save to database
            provenance_service.track_document_save(document, current_user)

        except Exception as e:
            import traceback
            current_app.logger.error(f"Failed to track document provenance: {str(e)}")
            current_app.logger.error(traceback.format_exc())

        return jsonify({
            'success': True,
            'message': 'Document saved successfully',
            'document_id': document.id,
            'document_uuid': str(document.uuid)
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error saving document: {str(e)}")

        # Check for duplicate DOI error
        error_str = str(e)
        if 'ix_documents_doi' in error_str or 'duplicate key' in error_str.lower():
            # Extract DOI from error message if possible
            import re
            doi_match = re.search(r'\(doi\)=\(([^)]+)\)', error_str)
            doi_value = doi_match.group(1) if doi_match else 'this DOI'
            return jsonify({
                'error': f'A document with DOI {doi_value} already exists in the database. '
                         'Please check the Documents page for the existing document.'
            }), 409  # 409 Conflict

        return jsonify({'error': str(e)}), 500
