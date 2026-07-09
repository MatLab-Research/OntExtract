"""Synchronous document metadata extraction routes."""

from datetime import datetime

from flask import current_app, jsonify, request

from app.utils.auth_decorators import api_require_login_for_write

from . import upload_bp


@upload_bp.route('/extract_metadata', methods=['POST'])
@api_require_login_for_write
def extract_metadata():
    """Extract metadata from uploaded document or DOI"""
    from app.services.upload_service import upload_service
    import json

    try:
        extraction_source = request.form.get('source_type')

        if extraction_source == 'doi':
            # Extract from DOI using shared service
            doi = request.form.get('doi')
            if not doi:
                return jsonify({'error': 'DOI is required'}), 400

            # Get bibliographic metadata from CrossRef
            metadata_result = upload_service.extract_metadata_from_doi(doi)

            if not metadata_result.success:
                return jsonify({'error': metadata_result.error}), 404

            # Build provenance tracking
            provenance = {}
            for key, value in metadata_result.metadata.items():
                if value is not None:
                    provenance[key] = {
                        'source': 'crossref',
                        'confidence': 0.95,
                        'timestamp': datetime.utcnow().isoformat(),
                        'raw_value': value
                    }

            # Return metadata for review (no file yet - user must upload)
            return jsonify({
                'success': True,
                'metadata': metadata_result.metadata,
                'provenance': provenance,
                'needs_file': True,
                'message': 'Bibliographic metadata retrieved. Please upload the document file.'
            })

        elif extraction_source == 'file':
            # Process uploaded file
            if 'document_file' not in request.files:
                return jsonify({'error': 'No file uploaded'}), 400

            file = request.files['document_file']

            # Save to temporary location
            upload_result = upload_service.save_to_temp(file)
            if not upload_result.success:
                return jsonify({'error': upload_result.error}), 400

            try:
                # Get user inputs
                title = request.form.get('title', '').strip()
                enable_crossref = request.form.get('enable_crossref', 'true').lower() == 'true'
                crossref_metadata = {}
                crossref_provenance = {}
                extraction_method = None

                # Track any metadata extracted directly from PDF (even if CrossRef fails)
                pdf_extracted_title = None
                pdf_extracted_metadata = {}
                progress_messages = []

                # If CrossRef is enabled, try multi-step extraction
                if enable_crossref:
                    current_app.logger.info(f"CrossRef enabled - attempting automatic extraction from PDF")

                    # Step 1: Try extracting from PDF (arXiv ID, DOI, or title)
                    pdf_result = upload_service.extract_metadata_from_pdf(upload_result.temp_path)

                    # Capture progress messages
                    current_app.logger.info(f"PDF result type: {type(pdf_result)}")
                    current_app.logger.info(f"Has progress attr: {hasattr(pdf_result, 'progress')}")
                    current_app.logger.info(f"Progress value: {getattr(pdf_result, 'progress', None)}")
                    if hasattr(pdf_result, 'progress') and pdf_result.progress:
                        progress_messages = pdf_result.progress
                        current_app.logger.info(f"Captured {len(progress_messages)} progress messages")
                    if pdf_result.success:
                        crossref_metadata = pdf_result.metadata
                        extraction_method = pdf_result.metadata.get('extraction_method', 'pdf_analysis')
                        source_name = pdf_result.source  # 'semanticscholar', 'crossref', or 'pdf_analysis'
                        current_app.logger.info(f"PDF extraction successful via {source_name} using {extraction_method}")

                        # Capture PDF-extracted title even when CrossRef succeeds (for low-confidence fallback)
                        if crossref_metadata.get('extracted_title'):
                            pdf_extracted_title = crossref_metadata['extracted_title']
                            pdf_extracted_metadata = {'title': pdf_extracted_title}
                            if crossref_metadata.get('extracted_authors'):
                                pdf_extracted_metadata['authors'] = crossref_metadata['extracted_authors']
                            current_app.logger.info(f"Captured PDF-extracted title for fallback: {pdf_extracted_title}")

                        # Track provenance (Semantic Scholar or CrossRef)
                        for key, value in crossref_metadata.items():
                            if value is not None:
                                # Set confidence based on extraction method
                                if 'arxiv' in extraction_method:
                                    confidence = 0.95  # arXiv ID matching is very reliable
                                elif 'doi' in extraction_method:
                                    confidence = 0.9  # DOI matching is very reliable
                                else:
                                    confidence = 0.85  # Title matching is less reliable

                                crossref_provenance[key] = {
                                    'source': source_name,
                                    'confidence': confidence,
                                    'timestamp': datetime.utcnow().isoformat(),
                                    'raw_value': value,
                                    'extraction_method': extraction_method
                                }
                    else:
                        # CrossRef lookup failed, but check if we extracted anything from PDF
                        pdf_extracted_metadata = pdf_result.metadata or {}
                        if pdf_extracted_metadata.get('title'):
                            pdf_extracted_title = pdf_extracted_metadata['title']
                            current_app.logger.info(f"Extracted title from PDF: {pdf_extracted_title}")

                        # Step 2: Try user-provided title
                        current_app.logger.info(f"PDF extraction failed, trying user-provided title: {title}")
                        if title:
                            metadata_result = upload_service.extract_metadata_from_title(title)
                            if metadata_result.success:
                                crossref_metadata = metadata_result.metadata
                                extraction_method = 'title_from_user'
                                current_app.logger.info(f"CrossRef match found for user-provided title")

                                # Track CrossRef provenance
                                for key, value in crossref_metadata.items():
                                    if value is not None:
                                        crossref_provenance[key] = {
                                            'source': 'crossref',
                                            'confidence': metadata_result.metadata.get('match_score', 0.85),
                                            'timestamp': datetime.utcnow().isoformat(),
                                            'raw_value': value,
                                            'extraction_method': extraction_method
                                        }
                            else:
                                current_app.logger.info(f"No CrossRef match found for: {title}")
                elif title:
                    current_app.logger.info(f"CrossRef disabled - using provided metadata only")

                # Parse user-provided metadata
                user_metadata = {}
                user_provenance = {}

                if title:
                    user_metadata['title'] = title
                    user_provenance['title'] = {
                        'source': 'user',
                        'confidence': 1.0,
                        'timestamp': datetime.utcnow().isoformat(),
                        'raw_value': title
                    }

                pub_year = request.form.get('publication_year', '').strip()
                if pub_year:
                    user_metadata['publication_year'] = pub_year  # Keep as string for flexible date parsing
                    user_provenance['publication_year'] = {
                        'source': 'user',
                        'confidence': 1.0,
                        'timestamp': datetime.utcnow().isoformat(),
                        'raw_value': pub_year
                    }

                authors_str = request.form.get('authors', '').strip()
                if authors_str:
                    authors = [a.strip() for a in authors_str.split(',')]
                    # Store as comma-separated string for database column
                    user_metadata['authors'] = ', '.join(authors)
                    user_provenance['authors'] = {
                        'source': 'user',
                        'confidence': 1.0,
                        'timestamp': datetime.utcnow().isoformat(),
                        'raw_value': authors,
                        'previous_source': 'user'
                    }

                # Additional metadata fields (shown when auto-extraction is disabled)
                journal = request.form.get('journal', '').strip()
                if journal:
                    user_metadata['journal'] = journal
                    user_provenance['journal'] = {
                        'source': 'user',
                        'confidence': 1.0,
                        'timestamp': datetime.utcnow().isoformat(),
                        'raw_value': journal
                    }

                publisher = request.form.get('publisher', '').strip()
                if publisher:
                    user_metadata['publisher'] = publisher
                    user_provenance['publisher'] = {
                        'source': 'user',
                        'confidence': 1.0,
                        'timestamp': datetime.utcnow().isoformat(),
                        'raw_value': publisher
                    }

                doi = request.form.get('doi', '').strip()
                if doi:
                    user_metadata['doi'] = doi
                    user_provenance['doi'] = {
                        'source': 'user',
                        'confidence': 1.0,
                        'timestamp': datetime.utcnow().isoformat(),
                        'raw_value': doi
                    }

                url = request.form.get('url', '').strip()
                if url:
                    user_metadata['url'] = url
                    user_provenance['url'] = {
                        'source': 'user',
                        'confidence': 1.0,
                        'timestamp': datetime.utcnow().isoformat(),
                        'raw_value': url
                    }

                abstract = request.form.get('abstract', '').strip()
                if abstract:
                    user_metadata['abstract'] = abstract
                    user_provenance['abstract'] = {
                        'source': 'user',
                        'confidence': 1.0,
                        'timestamp': datetime.utcnow().isoformat(),
                        'raw_value': abstract
                    }

                doc_type = request.form.get('type', '').strip()
                if doc_type:
                    user_metadata['type'] = doc_type
                    user_provenance['type'] = {
                        'source': 'user',
                        'confidence': 1.0,
                        'timestamp': datetime.utcnow().isoformat(),
                        'raw_value': doc_type
                    }

                isbn = request.form.get('isbn', '').strip()
                if isbn:
                    user_metadata['isbn'] = isbn
                    user_provenance['isbn'] = {
                        'source': 'user',
                        'confidence': 1.0,
                        'timestamp': datetime.utcnow().isoformat(),
                        'raw_value': isbn
                    }

                # Extended bibliographic fields (Zotero-aligned)
                extended_fields = [
                    'editor', 'edition', 'volume', 'issue', 'pages', 'series',
                    'container_title', 'place', 'issn', 'access_date', 'entry_term', 'notes'
                ]
                for field in extended_fields:
                    value = request.form.get(field, '').strip()
                    if value:
                        user_metadata[field] = value
                        user_provenance[field] = {
                            'source': 'user',
                            'confidence': 1.0,
                            'timestamp': datetime.utcnow().isoformat(),
                            'raw_value': value
                        }

                # If we have PDF-extracted metadata but no CrossRef, use it with lower confidence
                pdf_provenance = {}
                if pdf_extracted_title and not crossref_metadata:
                    pdf_provenance['title'] = {
                        'source': 'file',
                        'confidence': 0.7,
                        'timestamp': datetime.utcnow().isoformat(),
                        'raw_value': pdf_extracted_title,
                        'extraction_method': 'pdf_embedded_metadata'
                    }

                # Merge metadata (precedence: user > crossref > pdf > filename)
                merged_metadata = upload_service.merge_metadata(
                    {'title': pdf_extracted_title} if pdf_extracted_title else {},
                    crossref_metadata,
                    user_metadata,
                    {'filename': file.filename}
                )

                # Merge provenance (user takes precedence over crossref, crossref over pdf)
                merged_provenance = {**pdf_provenance, **crossref_provenance, **user_provenance}

                # Add filename provenance
                merged_provenance['filename'] = {
                    'source': 'file',
                    'confidence': 1.0,
                    'timestamp': datetime.utcnow().isoformat(),
                    'raw_value': file.filename
                }

                # Check if we have any metadata at all
                has_metadata = bool(crossref_metadata or user_metadata)

                # Build user message based on CrossRef results and extraction method
                if enable_crossref and crossref_metadata:
                    confidence_level = crossref_metadata.get('confidence_level', 'high')
                    match_score = crossref_metadata.get('match_score', 0)

                    # Base message based on extraction method
                    if extraction_method == 'doi_from_pdf':
                        base_message = 'CrossRef match found using DOI from PDF!'
                    elif extraction_method == 'title_from_pdf':
                        base_message = 'CrossRef match found using title from PDF!'
                    elif extraction_method == 'title_from_user':
                        base_message = 'CrossRef match found using your provided title!'
                    else:
                        base_message = 'CrossRef match found!'

                    # Add confidence warning if needed
                    if confidence_level == 'low':
                        message = f'{base_message} LOW CONFIDENCE (score: {match_score:.1f}/100). Please verify this is the correct document before saving.'
                    else:
                        message = f'{base_message} Please review the auto-filled metadata.'
                elif enable_crossref and not crossref_metadata and pdf_extracted_title:
                    # We found a title in PDF but no CrossRef match
                    message = f'Extracted title from PDF: "{pdf_extracted_title}". No CrossRef match found. You can use this title or enter a different one below.'
                elif enable_crossref and not crossref_metadata and not title and not pdf_extracted_title:
                    # PDF extraction failed and no title provided - show empty form
                    message = 'Could not extract metadata from PDF. Please fill in the required fields below.'
                elif enable_crossref and not crossref_metadata and title:
                    message = 'No CrossRef match found for your title. Please enter metadata manually.'
                elif not enable_crossref and not title:
                    # CrossRef disabled but no title - validation error
                    upload_service.cleanup_temp(upload_result.temp_path)
                    return jsonify({
                        'success': False,
                        'error': 'Title is required when CrossRef lookup is disabled.'
                    }), 400
                else:
                    message = 'Document uploaded. Please review metadata before saving.'

                current_app.logger.info(f"About to return JSON with {len(progress_messages)} progress messages")
                current_app.logger.info(f"Progress messages: {progress_messages}")

                return jsonify({
                    'success': True,
                    'metadata': merged_metadata,
                    'provenance': merged_provenance,
                    'temp_path': upload_result.temp_path,
                    'needs_file': False,
                    'message': message,
                    'crossref_enabled': enable_crossref,
                    'crossref_found': bool(crossref_metadata),
                    'extraction_method': extraction_method,
                    'confidence_level': confidence_level if crossref_metadata else None,
                    'match_score': match_score if crossref_metadata else None,
                    'progress': progress_messages,
                    'pdf_extracted_title': pdf_extracted_title,
                    'pdf_extracted_metadata': pdf_extracted_metadata
                })

            except Exception as e:
                # Clean up temp file
                upload_service.cleanup_temp(upload_result.temp_path)
                raise e

        else:
            return jsonify({'error': 'Invalid source type'}), 400

    except Exception as e:
        current_app.logger.error(f"Error extracting metadata: {str(e)}")
        return jsonify({'error': str(e)}), 500
