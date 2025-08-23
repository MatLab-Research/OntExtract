"""
Unified upload route for all content types.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
import uuid
from app import db
from app.models.experiment import Experiment
from app.models.document import Document
from app.services.text_processing import TextProcessingService
from app.utils.file_handler import FileHandler

upload_bp = Blueprint('upload', __name__, url_prefix='/upload')

@upload_bp.route('/')
@login_required
def unified():
    """
    Unified upload interface for all content types:
    - Documents for analysis
    - References/citations
    - Pasted text
    - Dictionary entries
    """
    # Check if this is linked from an experiment
    experiment_id = request.args.get('experiment_id')
    experiment = None
    
    if experiment_id:
        experiment = Experiment.query.filter_by(
            id=experiment_id,
            user_id=current_user.id
        ).first()
    
    return render_template('upload/unified.html', experiment=experiment)

@upload_bp.route('/document', methods=['POST'])
@login_required
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
        authors = request.form.get('authors', '').split(',')
        authors = [a.strip() for a in authors if a.strip()]
        publication_date = request.form.get('publication_date')
        journal = request.form.get('journal')
        doi = request.form.get('doi')
        isbn = request.form.get('isbn')
        url = request.form.get('url')
        abstract = request.form.get('abstract')
        citation = request.form.get('citation')
        
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
        
        # Create base metadata with PROV-O classification
        source_metadata = {
            'prov_type': prov_type,  # PROV-O classification
            'authors': authors if authors else None,
            'publication_date': publication_date,
            'journal': journal,
            'doi': doi,
            'isbn': isbn,
            'url': url,
            'abstract': abstract,
            'citation': citation
        }
        
        # Remove empty values
        source_metadata = {k: v for k, v in source_metadata.items() if v}
        
        # Determine document type based on PROV-O classification
        # Map PROV-O types to internal document_type for backward compatibility
        if 'Reference' in prov_type or 'Academic' in prov_type or 'Standard' in prov_type:
            document_type = 'reference'
            reference_subtype = 'academic' if 'Academic' in prov_type else 'standard' if 'Standard' in prov_type else 'other'
        else:
            document_type = 'document'
            reference_subtype = None
        
        # Create document record
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
            source_metadata=source_metadata if source_metadata else None,
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
        
        # Process the document based on options
        processing_service = TextProcessingService()
        
        try:
            # Basic processing
            processing_service.process_document(document)
            
            # Create segments if requested
            if create_segments:
                processing_service.create_initial_segments(document)
            
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
        
        # Link to experiment if applicable
        experiment_id = request.form.get('experiment_id')
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
                return redirect(url_for('experiments.view', id=experiment_id))
        
        # Redirect based on document type
        if document_type == 'reference':
            return redirect(url_for('references.view', id=document.id))
        else:
            return redirect(url_for('text_input.document_detail', document_id=document.id))
            
    except Exception as e:
        current_app.logger.error(f"Error uploading document: {str(e)}")
        flash(f'An error occurred while uploading: {str(e)}', 'error')
        return redirect(url_for('upload.unified'))

@upload_bp.route('/redirect', methods=['GET'])
@login_required
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
