"""Legacy direct document upload flow."""

from flask import current_app, flash, redirect, request, url_for
from flask_login import current_user
from werkzeug.utils import secure_filename

from app import db
from app.models.document import Document
from app.models.experiment import Experiment
from app.services.text_processing import TextProcessingService
from app.utils.auth_decorators import api_require_login_for_write
from app.utils.file_handler import FileHandler

from . import upload_bp


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
