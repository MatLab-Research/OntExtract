"""
Unified upload route for all content types.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, Response
from flask_login import current_user, login_required
from app.utils.auth_decorators import require_login_for_write, api_require_login_for_write
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import uuid
from app import db
from app.models.experiment import Experiment
from app.models.document import Document
from app.services.text_processing import TextProcessingService
from app.utils.file_handler import FileHandler

upload_bp = Blueprint('upload', __name__, url_prefix='/upload')

@upload_bp.route('/')
@require_login_for_write
def unified():
    """
    Enhanced upload interface with CrossRef metadata extraction and provenance tracking.
    """
    return render_template('text_input/upload_enhanced.html')

@upload_bp.route('/document', methods=['POST'])
@api_require_login_for_write
def upload_document():
    """
    Unified document upload handler that processes all document types
    with full feature set including Zotero metadata extraction.
    """
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            flash('No file provided', 'error')
            return redirect(url_for('upload.unified'))
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(url_for('upload.unified'))
        
        # Get form data
        title = request.form.get('title', '').strip()
        prov_type = request.form.get('prov_type', 'prov:Entity')
        
        # Processing options
        check_zotero = request.form.get('check_zotero') == 'on'
        auto_detect_language = request.form.get('auto_detect_language') == 'on'
        create_segments = request.form.get('create_segments') == 'on'
        extract_entities = request.form.get('extract_entities') == 'on'
        temporal_analysis = request.form.get('temporal_analysis') == 'on'
        
        # Optional metadata
        from app.utils.date_parser import parse_flexible_date

        authors_str = request.form.get('authors', '').strip()
        authors = authors_str if authors_str else None

        pub_date_str = request.form.get('publication_date', '').strip()
        publication_date = parse_flexible_date(pub_date_str) if pub_date_str else None

        journal = request.form.get('journal', '').strip() or None
        doi = request.form.get('doi', '').strip() or None
        isbn = request.form.get('isbn', '').strip() or None
        url = request.form.get('url', '').strip() or None
        abstract = request.form.get('abstract', '').strip() or None
        citation = request.form.get('citation', '').strip() or None

        # Extended bibliographic fields
        editor = request.form.get('editor', '').strip() or None
        edition = request.form.get('edition', '').strip() or None
        volume = request.form.get('volume', '').strip() or None
        issue = request.form.get('issue', '').strip() or None
        pages = request.form.get('pages', '').strip() or None
        issn = request.form.get('issn', '').strip() or None
        container_title = request.form.get('container_title', '').strip() or None
        place = request.form.get('place', '').strip() or None
        series = request.form.get('series', '').strip() or None
        entry_term = request.form.get('entry_term', '').strip() or None
        notes = request.form.get('notes', '').strip() or None
        publisher = request.form.get('publisher', '').strip() or None

        access_date_str = request.form.get('access_date', '').strip()
        access_date = parse_flexible_date(access_date_str) if access_date_str else None

        # Experiment linking (optional)
        experiment_id = request.form.get('experiment_id')

        # Save file
        file_handler = FileHandler()
        saved_path, file_size = file_handler.save_file(
            file, 
            upload_folder=current_app.config.get('UPLOAD_FOLDER')
        )
        
        if not saved_path:
            flash('Failed to save file', 'error')
            return redirect(url_for('upload.unified'))
        
        # Extract text content
        original_filename = file.filename or ''
        content = file_handler.extract_text_from_file(saved_path, original_filename)
        
        # Detect language if requested
        detected_language = None
        language_confidence = 0.0
        if auto_detect_language and content:
            try:
                from langdetect import detect
                detected_language = detect(content)
                language_confidence = 0.9
            except:
                detected_language = 'en'
                language_confidence = 0.5
        
        # Create base metadata with PROV-O classification (for custom fields only)
        source_metadata = {
            'prov_type': prov_type,  # PROV-O classification
        }

        # Determine document type based on PROV-O classification
        # Map PROV-O types to internal document_type for backward compatibility
        if 'Reference' in prov_type or 'Academic' in prov_type or 'Standard' in prov_type:
            document_type = 'reference'
            reference_subtype = 'academic' if 'Academic' in prov_type else 'standard' if 'Standard' in prov_type else 'other'
        else:
            document_type = 'document'
            reference_subtype = None

        # Create document record with normalized columns
        document = Document(
            title=title or secure_filename(original_filename),
            content_type='file',
            document_type=document_type,
            reference_subtype=reference_subtype,
            file_type=file_handler.get_file_extension(original_filename),
            original_filename=original_filename,
            file_path=saved_path,
            file_size=file_size,
            content=content,
            detected_language=detected_language,
            language_confidence=language_confidence,
            # Normalized bibliographic columns
            authors=authors,
            publication_date=publication_date,
            journal=journal,
            publisher=publisher,
            doi=doi,
            isbn=isbn,
            abstract=abstract,
            url=url,
            citation=citation,
            # Extended bibliographic columns
            editor=editor,
            edition=edition,
            volume=volume,
            issue=issue,
            pages=pages,
            issn=issn,
            container_title=container_title,
            place=place,
            series=series,
            entry_term=entry_term,
            access_date=access_date,
            notes=notes,
            # Legacy
            source_metadata=source_metadata,
            user_id=current_user.id,
            status='uploaded'
        )
        
        # Enrich with Zotero metadata if requested (for PDFs)
        if check_zotero and saved_path and file_handler.get_file_extension(original_filename).lower() == 'pdf':
            try:
                from app.services.reference_metadata_enricher import ReferenceMetadataEnricher
                
                enricher = ReferenceMetadataEnricher(use_zotero=True)
                delta = enricher.extract_with_zotero(
                    saved_path,
                    title=title,
                    existing=document.source_metadata or {},
                    allow_overwrite=False
                )
                
                if delta:
                    # Merge Zotero metadata
                    merged = document.source_metadata or {}
                    for k, v in delta.items():
                        if k not in merged or not merged.get(k):
                            merged[k] = v
                    document.source_metadata = merged
                    
                    if 'zotero_key' in delta:
                        current_app.logger.info(
                            f"Enriched document with Zotero metadata "
                            f"(key: {delta['zotero_key']}, score: {delta.get('zotero_match_score', 0):.2f})"
                        )
            except Exception as e:
                current_app.logger.warning(f"Zotero metadata enrichment failed: {str(e)}")
        
        db.session.add(document)
        db.session.commit()

        # Track document upload with PROV-O
        try:
            from app.services.provenance_service import provenance_service
            experiment = Experiment.query.get(experiment_id) if experiment_id else None
            provenance_service.track_document_upload(document, current_user, experiment)
        except Exception as e:
            current_app.logger.warning(f"Failed to track document upload provenance: {str(e)}")

        # Process the document based on options
        processing_service = TextProcessingService()
        
        try:
            # Basic processing
            processing_service.process_document(document)
            
            # Note: Segments are now created manually from document processing page
            # Removed automatic segmentation to allow user control
            # if create_segments:
            #     processing_service.create_initial_segments(document)
            
            # Extract entities if requested
            if extract_entities:
                # This would trigger entity extraction
                # You might need to implement this based on your entity extraction service
                pass
            
            # Temporal analysis if requested
            if temporal_analysis:
                # This would trigger temporal analysis
                # You might need to implement this based on your temporal service
                pass
            
            flash(f'Document "{document.title}" uploaded and processed successfully', 'success')
            
        except Exception as e:
            flash(f'Document uploaded but processing failed: {str(e)}', 'warning')
        
        # Link to experiment if applicable (experiment_id already extracted at top)
        if experiment_id:
            experiment = Experiment.query.get(experiment_id)
            if experiment and experiment.user_id == current_user.id:
                include_in_analysis = request.form.get('include_in_analysis') == 'true'
                
                # Add document to experiment based on type
                if document_type == 'reference':
                    experiment.add_reference(document, include_in_analysis=include_in_analysis)
                else:
                    # Add as source document - you might need to implement this method
                    if not hasattr(experiment, 'documents'):
                        experiment.documents = []
                    if document not in experiment.documents:
                        experiment.documents.append(document)
                        db.session.commit()
                
                flash(f'Document linked to experiment "{experiment.name}"', 'success')
                return redirect(url_for('experiments.view', experiment_id=experiment_id))
        
        # All documents now go to the same detail page with full processing options
        return redirect(url_for('text_input.document_detail', document_uuid=document.uuid))
            
    except Exception as e:
        current_app.logger.error(f"Error uploading document: {str(e)}")
        flash(f'An error occurred while uploading: {str(e)}', 'error')
        return redirect(url_for('upload.unified'))

@upload_bp.route('/redirect', methods=['GET'])
@api_require_login_for_write
def redirect_old_routes():
    """
    Redirect old upload routes to the unified interface.
    This ensures backward compatibility.
    """
    # Capture any query parameters
    experiment_id = request.args.get('experiment_id')
    
    # Determine which tab to open based on the referrer
    referrer = request.referrer or ''
    
    # Build redirect URL
    redirect_url = url_for('upload.unified')
    if experiment_id:
        redirect_url = f"{redirect_url}?experiment_id={experiment_id}"
    
    # You could add logic here to pre-select a tab based on the referrer
    # For example, if coming from references, open the reference tab

    return redirect(redirect_url)


# Enhanced Upload Routes with Metadata Extraction and Provenance

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


@upload_bp.route('/extract_metadata_stream', methods=['POST'])
@api_require_login_for_write
def extract_metadata_stream():
    """
    Stream metadata extraction progress using Server-Sent Events (SSE).

    This endpoint provides real-time progress updates during PDF analysis
    and external API lookups (Semantic Scholar, CrossRef).
    """
    from app.services.upload_service import upload_service
    import json
    import queue
    import threading

    # Get the uploaded file
    if 'document_file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['document_file']
    title = request.form.get('title', '').strip()
    enable_crossref = request.form.get('enable_crossref', 'true').lower() == 'true'

    # Save to temporary location first (before streaming)
    upload_result = upload_service.save_to_temp(file)
    if not upload_result.success:
        return jsonify({'error': upload_result.error}), 400

    temp_path = upload_result.temp_path
    original_filename = upload_result.filename

    # Create a queue for progress messages
    progress_queue = queue.Queue()
    result_holder = {'result': None, 'error': None}

    def extraction_worker():
        """Run extraction in background thread, putting progress into queue."""
        try:
            if enable_crossref:
                # Use the streaming version of metadata extraction
                result = upload_service.extract_metadata_from_pdf_streaming(
                    temp_path,
                    progress_callback=lambda msg: progress_queue.put({'type': 'progress', 'message': msg})
                )
                result_holder['result'] = result
            else:
                # No extraction needed
                result_holder['result'] = {
                    'success': True,
                    'metadata': {},
                    'source': 'user'
                }
            progress_queue.put({'type': 'complete'})
        except Exception as e:
            result_holder['error'] = str(e)
            progress_queue.put({'type': 'error', 'message': str(e)})

    # Capture app context for the generator
    app = current_app._get_current_object()

    def generate():
        """Generator that yields SSE events."""
        # Start the extraction in a background thread
        worker = threading.Thread(target=extraction_worker)
        worker.start()

        try:
            while True:
                try:
                    # Wait for messages with timeout (for heartbeat)
                    msg = progress_queue.get(timeout=1.0)

                    if msg['type'] == 'progress':
                        yield f"data: {json.dumps({'type': 'progress', 'message': msg['message']})}\n\n"

                    elif msg['type'] == 'complete':
                        # Worker finished, send final result
                        result = result_holder['result']
                        if result:
                            # Build the full response similar to extract_metadata
                            with app.app_context():
                                final_data = _build_extraction_response(
                                    result, temp_path, original_filename, title, enable_crossref
                                )
                            yield f"data: {json.dumps({'type': 'complete', 'data': final_data})}\n\n"
                        break

                    elif msg['type'] == 'error':
                        yield f"data: {json.dumps({'type': 'error', 'message': msg['message']})}\n\n"
                        break

                except queue.Empty:
                    # Send heartbeat to keep connection alive
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"

        finally:
            worker.join(timeout=30)  # Wait for worker to finish

    return Response(generate(), mimetype='text/event-stream')


def _build_extraction_response(result, temp_path, original_filename, title, enable_crossref):
    """Build the response data from extraction result (shared logic)."""
    from datetime import datetime

    crossref_metadata = {}
    crossref_provenance = {}
    pdf_extracted_title = None
    pdf_extracted_metadata = {}
    progress_messages = []
    extraction_method = None

    if hasattr(result, 'success'):
        # It's a MetadataExtractionResult
        if hasattr(result, 'progress') and result.progress:
            progress_messages = result.progress

        if result.success:
            crossref_metadata = result.metadata
            extraction_method = result.metadata.get('extraction_method', 'pdf_analysis')
            source_name = result.source

            # Capture PDF-extracted title
            if crossref_metadata.get('extracted_title'):
                pdf_extracted_title = crossref_metadata['extracted_title']
                pdf_extracted_metadata = {'title': pdf_extracted_title}
                if crossref_metadata.get('extracted_authors'):
                    pdf_extracted_metadata['authors'] = crossref_metadata['extracted_authors']

            # Track provenance
            for key, value in crossref_metadata.items():
                if value is not None:
                    if 'arxiv' in str(extraction_method):
                        confidence = 0.95
                    elif 'doi' in str(extraction_method):
                        confidence = 0.9
                    else:
                        confidence = 0.85

                    crossref_provenance[key] = {
                        'source': source_name,
                        'confidence': confidence,
                        'timestamp': datetime.utcnow().isoformat(),
                        'raw_value': value,
                        'extraction_method': extraction_method
                    }
        else:
            # Extraction failed, use fallback
            pdf_extracted_metadata = result.metadata or {}
            if pdf_extracted_metadata.get('title'):
                pdf_extracted_title = pdf_extracted_metadata['title']
    else:
        # It's a dict result
        crossref_metadata = result.get('metadata', {})
        progress_messages = result.get('progress', [])

    # Merge metadata
    merged_metadata = {**crossref_metadata}
    merged_metadata['filename'] = original_filename

    # Build provenance for filename
    provenance = {**crossref_provenance}
    provenance['filename'] = {
        'source': 'file',
        'confidence': 1.0,
        'timestamp': datetime.utcnow().isoformat()
    }

    # Determine confidence level for CrossRef matches
    confidence_level = crossref_metadata.get('confidence_level', 'high')
    crossref_found = bool(crossref_metadata.get('title'))

    return {
        'success': True,
        'metadata': merged_metadata,
        'provenance': provenance,
        'temp_path': temp_path,
        'crossref_found': crossref_found,
        'confidence_level': confidence_level,
        'match_score': crossref_metadata.get('confidence_value', 0.0),
        'progress': progress_messages,
        'pdf_extracted_title': pdf_extracted_title,
        'pdf_extracted_metadata': pdf_extracted_metadata
    }


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


@upload_bp.route('/create_reference', methods=['POST'])
@login_required
def create_reference():
    """
    Create a reference document from dictionary definition
    Quick add feature for experiment creation
    """
    try:
        data = request.get_json()

        title = data.get('title')
        content = data.get('content')
        source = data.get('source')  # MW or OED
        source_type = data.get('source_type', 'dictionary')
        experiment_id = data.get('experiment_id')
        include_in_analysis = data.get('include_in_analysis', False)

        if not title or not content:
            return jsonify({'success': False, 'error': 'Title and content are required'}), 400

        # Create reference document
        document = Document(
            title=title,
            content=content,
            document_type='reference',
            source=source,
            user_id=current_user.id,
            content_type='text/plain',
            word_count=len(content.split()),
            created_at=datetime.utcnow()
        )

        db.session.add(document)
        db.session.commit()

        # If experiment_id provided, associate reference with experiment
        if experiment_id:
            experiment = Experiment.query.get(experiment_id)
            if experiment and experiment.user_id == current_user.id:
                experiment.add_reference(document, include_in_analysis=include_in_analysis)

        return jsonify({
            'success': True,
            'document_id': document.id,
            'document_uuid': str(document.uuid)
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating reference: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
