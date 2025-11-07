"""
Unified upload route for all content types.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import current_user
from app.utils.auth_decorators import require_login_for_write, api_require_login_for_write
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
    from datetime import datetime
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
                # Try to get CrossRef metadata from title (if provided) OR from PDF analysis
                title = request.form.get('title', '').strip()
                crossref_metadata = {}
                crossref_provenance = {}

                # If no title provided and file is PDF, try automatic extraction
                if not title and file.filename.lower().endswith('.pdf'):
                    current_app.logger.info(f"No title provided, attempting PDF analysis for {file.filename}")
                    pdf_result = upload_service.extract_metadata_from_pdf(upload_result.temp_path)

                    if pdf_result.success:
                        crossref_metadata = pdf_result.metadata
                        # Track CrossRef provenance with automatic extraction note
                        for key, value in crossref_metadata.items():
                            if value is not None and key not in ['extracted_doi', 'extracted_title', 'extraction_method']:
                                crossref_provenance[key] = {
                                    'source': 'crossref_auto',
                                    'confidence': 0.90,
                                    'timestamp': datetime.utcnow().isoformat(),
                                    'raw_value': value,
                                    'extraction_method': pdf_result.metadata.get('extraction_method', 'auto')
                                }
                        current_app.logger.info(f"PDF extraction successful: {pdf_result.metadata.get('extraction_method')}")
                    else:
                        current_app.logger.warning(f"PDF extraction failed: {pdf_result.error if hasattr(pdf_result, 'error') else 'Unknown'}")

                # If title was provided by user, use that
                if title:
                    metadata_result = upload_service.extract_metadata_from_title(title)
                    if metadata_result.success:
                        crossref_metadata = metadata_result.metadata
                        # Track CrossRef provenance
                        for key, value in crossref_metadata.items():
                            if value is not None:
                                crossref_provenance[key] = {
                                    'source': 'crossref',
                                    'confidence': metadata_result.metadata.get('match_score', 0.85),
                                    'timestamp': datetime.utcnow().isoformat(),
                                    'raw_value': value
                                }

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
                    user_metadata['publication_year'] = int(pub_year)
                    user_provenance['publication_year'] = {
                        'source': 'user',
                        'confidence': 1.0,
                        'timestamp': datetime.utcnow().isoformat(),
                        'raw_value': int(pub_year)
                    }

                authors_str = request.form.get('authors', '').strip()
                if authors_str:
                    authors = [a.strip() for a in authors_str.split(',')]
                    user_metadata['authors'] = authors
                    user_provenance['authors'] = {
                        'source': 'user',
                        'confidence': 1.0,
                        'timestamp': datetime.utcnow().isoformat(),
                        'raw_value': authors
                    }

                # Merge metadata (user takes precedence over CrossRef)
                merged_metadata = upload_service.merge_metadata(
                    crossref_metadata,
                    user_metadata,
                    {'filename': file.filename}
                )

                # Merge provenance (user takes precedence)
                merged_provenance = {**crossref_provenance, **user_provenance}

                # Add filename provenance
                merged_provenance['filename'] = {
                    'source': 'file',
                    'confidence': 1.0,
                    'timestamp': datetime.utcnow().isoformat(),
                    'raw_value': file.filename
                }

                return jsonify({
                    'success': True,
                    'metadata': merged_metadata,
                    'provenance': merged_provenance,
                    'temp_path': upload_result.temp_path,
                    'needs_file': False,
                    'message': 'Document analyzed. Please review metadata before saving.'
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

        # Create upload directory
        upload_dir = current_app.config.get('UPLOAD_FOLDER', 'uploads')

        # Save permanently
        save_result = upload_service.save_permanent(temp_path, upload_dir, filename)
        if not save_result.success:
            return jsonify({'error': save_result.error}), 400

        final_path = save_result.file_path

        # Extract text content for the document
        content, error = upload_service.extract_text_content(final_path, filename)
        if error:
            return jsonify({'error': error}), 400

        # Prepare source_metadata (bibliographic info)
        source_metadata = {
            'authors': metadata.get('authors', []),
            'publication_year': metadata.get('publication_year'),
            'journal': metadata.get('journal'),
            'publisher': metadata.get('publisher'),
            'doi': metadata.get('doi'),
            'url': metadata.get('url'),
            'abstract': metadata.get('abstract'),
            'type': metadata.get('type'),
            'extraction_source': 'enhanced_upload'
        }

        # Create document record
        document = Document(
            title=metadata.get('title', filename),
            content_type='file',
            file_type='pdf',
            original_filename=filename,
            file_path=final_path,
            file_size=os.path.getsize(final_path),
            content=content,
            source_metadata=source_metadata,
            metadata_provenance=provenance,
            status='uploaded',
            user_id=current_user.id
        )

        db.session.add(document)
        db.session.commit()

        # Track document upload with PROV-O
        try:
            from app.services.provenance_service import provenance_service
            provenance_service.track_document_upload(document, current_user)

            # Track metadata extraction separately if CrossRef/Zotero was used
            if provenance:
                # Collect fields that came from automated extraction
                crossref_fields = {}
                zotero_fields = {}

                for field_name, prov_data in provenance.items():
                    if isinstance(prov_data, dict):
                        source = prov_data.get('source', '')
                        if source in ['crossref', 'crossref_auto']:
                            crossref_fields[field_name] = prov_data.get('raw_value')
                        elif source == 'zotero':
                            zotero_fields[field_name] = prov_data.get('raw_value')

                # Track CrossRef extraction if any fields were extracted
                if crossref_fields:
                    confidence = provenance.get('match_score', {}).get('raw_value', 0.9) if 'match_score' in provenance else 0.9
                    provenance_service.track_metadata_extraction(
                        document, current_user, 'crossref', crossref_fields, confidence
                    )

                # Track Zotero extraction if any fields were extracted
                if zotero_fields:
                    provenance_service.track_metadata_extraction(
                        document, current_user, 'zotero', zotero_fields, 0.95
                    )
        except Exception as e:
            current_app.logger.warning(f"Failed to track document upload provenance: {str(e)}")

        return jsonify({
            'success': True,
            'message': 'Document saved successfully',
            'document_id': document.id,
            'document_uuid': str(document.uuid)
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error saving document: {str(e)}")
        return jsonify({'error': str(e)}), 500
