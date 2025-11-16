"""
References Upload and Parsing Routes

This module handles upload operations and PDF parsing for reference documents.

Routes:
- GET/POST /references/upload           - Upload reference file
- POST     /references/parse_oed_pdf    - Parse OED PDF
- POST     /references/upload_dictionary - Upload dictionary entry
"""

from flask import render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import current_user
from app.utils.auth_decorators import api_require_login_for_write
from werkzeug.utils import secure_filename
import os
import tempfile
from app import db
from app.models.document import Document
from app.models.experiment import Experiment
from app.services.text_processing import TextProcessingService
from app.utils.file_handler import FileHandler

from . import references_bp


@references_bp.route('/upload', methods=['GET', 'POST'])
@api_require_login_for_write
def upload():
    """Upload a new reference document"""
    use_tabbed = request.args.get('tabbed', 'true').lower() == 'true'

    if request.method == 'POST':
        # Check if file was uploaded
        if 'file' not in request.files:
            flash('No file provided', 'error')
            return redirect(request.url)

        file = request.files['file']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(request.url)

        # Get metadata from form
        title = request.form.get('title')
        reference_subtype = request.form.get('reference_subtype', 'other')
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
        saved_path, file_size = file_handler.save_file(file, upload_folder=current_app.config.get('UPLOAD_FOLDER'))

        if not saved_path:
            flash('Failed to save file', 'error')
            return redirect(request.url)

        # Create source metadata
        source_metadata = {
            'authors': authors,
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

        # Create document record
        original_name = file.filename or ''
        document = Document(
            title=title or secure_filename(original_name),
            content_type='file',
            document_type='reference',
            reference_subtype=reference_subtype,
            file_type=file_handler.get_file_extension(original_name),
            original_filename=original_name,
            file_path=saved_path,
            file_size=file_size,
            source_metadata=source_metadata if source_metadata else None,
            user_id=current_user.id,
            status='uploaded'
        )

        # Phase 1: prefill metadata from PDF via heuristics (pypdf) and Zotero, if enabled
        try:
            fext = (file_handler.get_file_extension(original_name) or '').lower()
            if current_app.config.get('PREFILL_METADATA', True) and saved_path and fext == 'pdf':
                from app.services.reference_metadata_enricher import ReferenceMetadataEnricher

                # Enable Zotero lookup by default (can be disabled in config)
                use_zotero = current_app.config.get('USE_ZOTERO_METADATA', True)
                enricher = ReferenceMetadataEnricher(use_zotero=use_zotero)

                # Use the new method that includes Zotero lookup
                delta = enricher.extract_with_zotero(
                    saved_path,
                    title=title,
                    existing=document.source_metadata or {},
                    allow_overwrite=False
                )

                if delta:
                    # merge into document.source_metadata and persist
                    merged = document.source_metadata or {}
                    for k, v in delta.items():
                        if k not in merged or not merged.get(k):
                            merged[k] = v
                    document.source_metadata = merged

                    # Log if we found Zotero metadata
                    if 'zotero_key' in delta:
                        current_app.logger.info(
                            f"Enriched document {document.id} with Zotero metadata "
                            f"(key: {delta['zotero_key']}, match score: {delta.get('zotero_match_score', 0):.2f})"
                        )
        except Exception as _e:
            # Soft-fail: enrichment is best-effort
            current_app.logger.warning(f"Metadata enrichment failed: {str(_e)}")
            pass

        db.session.add(document)
        db.session.commit()

        # Process the reference document
        try:
            processing_service = TextProcessingService()
            processing_service.process_document(document)
            flash(f'Reference "{document.title}" uploaded and processed successfully', 'success')
        except Exception as e:
            flash(f'Reference uploaded but processing failed: {str(e)}', 'warning')

        # Check if this was uploaded from an experiment
        experiment_id = request.form.get('experiment_id')
        if experiment_id:
            experiment = Experiment.query.get(experiment_id)
            if experiment:
                experiment.add_reference(document,
                                       include_in_analysis=request.form.get('include_in_analysis') == 'true')
                flash(f'Reference linked to experiment "{experiment.name}"', 'success')
                return redirect(url_for('experiments.view', experiment_id=experiment_id))

        return redirect(url_for('references.view', id=document.id))

    # GET request - show upload form
    experiment_id = request.args.get('experiment_id')
    experiment = None
    if experiment_id:
        experiment = Experiment.query.filter_by(
            id=experiment_id
        ).first()

    # Use tabbed interface by default for better UX
    if use_tabbed:
        return render_template('references/upload_tabbed.html', experiment=experiment)
    else:
        return render_template('references/upload.html', experiment=experiment)


@references_bp.route('/parse_oed_pdf', methods=['POST'])
@api_require_login_for_write
def parse_oed_pdf():
    """Parse uploaded OED PDF and return structured data"""
    from app.services.oed_parser_final import OEDParser

    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    # Check if it's a PDF
    if not (file.filename or '').lower().endswith('.pdf'):
        return jsonify({'error': 'Only PDF files are supported'}), 400

    # Save temporarily
    temp_dir = tempfile.gettempdir()
    temp_name = secure_filename(file.filename or 'oed.pdf')
    temp_path = os.path.join(temp_dir, temp_name)

    try:
        file.save(temp_path)

        # Parse with OED parser
        parser = OEDParser()
        extracted_data = parser.parse_pdf(temp_path)

        # Format for frontend
        response_data = {
            'success': True,
            'data': extracted_data,
            'message': 'Successfully parsed OED entry'
        }

        return jsonify(response_data)

    except Exception as e:
        current_app.logger.error(f"Error parsing OED PDF: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to parse OED PDF'
        }), 500

    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass


@references_bp.route('/upload_dictionary', methods=['POST'])
@api_require_login_for_write
def upload_dictionary():
    """Upload a dictionary entry (OED or general)"""
    # Helper cleaners to strip NULs from inputs (Postgres cannot store \x00)
    def _clean_str(val):
        if val is None:
            return None
        try:
            return val.replace('\x00', '')
        except Exception:
            return val

    def _clean_meta(obj):
        if obj is None:
            return None
        if isinstance(obj, str):
            return _clean_str(obj)
        if isinstance(obj, dict):
            return {k: _clean_meta(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_clean_meta(v) for v in obj]
        return obj

    # Get form data
    title = _clean_str(request.form.get('title') or '')
    content = _clean_str(request.form.get('content') or '')
    reference_subtype = request.form.get('reference_subtype', 'dictionary_general')

    if not title or not content:
        flash('Term and definition are required', 'error')
        return redirect(url_for('references.upload'))

    # Build source metadata based on dictionary type
    source_metadata = {}

    if reference_subtype == 'dictionary_oed':
        # OED-specific fields - store everything in metadata for reference
        source_metadata = _clean_meta({
            'pronunciation': request.form.get('pronunciation'),
            'etymology': request.form.get('etymology'),
            'usage_notes': request.form.get('usage_notes'),
            'examples': request.form.get('examples'),
            'first_use': request.form.get('first_use'),
            'edition': request.form.get('edition'),
            'journal': 'Oxford English Dictionary',
            'url': request.form.get('url'),
            'citation': request.form.get('citation'),
            'pdf_link': request.form.get('pdf_link')
        })

        # Store the FULL content as-is (no formatting, just the complete text)
        formatted_content = content

    else:
        # General dictionary fields
        source_metadata = _clean_meta({
            'journal': request.form.get('journal'),
            'context': request.form.get('context'),
            'synonyms': request.form.get('synonyms'),
            'url': request.form.get('url')
        })

        # Format the content for general dictionary
        formatted_content = f"Term: {title}\n\n"
        if source_metadata and isinstance(source_metadata, dict):
            formatted_content += f"Source: {source_metadata.get('journal', 'Unknown')}\n\n"
            if source_metadata.get('context'):
                formatted_content += f"Context/Domain: {source_metadata.get('context')}\n\n"
        formatted_content += f"Definition:\n{content}\n"
        if source_metadata and isinstance(source_metadata, dict) and source_metadata.get('synonyms'):
            formatted_content += f"\nSynonyms: {source_metadata.get('synonyms')}\n"

    # Remove empty values from metadata (ensure it's a dict first)
    if not isinstance(source_metadata, dict):
        source_metadata = {}
    else:
        source_metadata = {k: v for k, v in source_metadata.items() if v}

    # Create document record
    document = Document(
        title=title or '',
        content_type='text',
        document_type='reference',
        reference_subtype=reference_subtype,
        content=formatted_content or '',
        content_preview=(formatted_content or '')[:500] + ('...' if len(formatted_content or '') > 500 else ''),
        source_metadata=source_metadata if source_metadata else None,
        user_id=current_user.id,
        status='completed',
        word_count=len((formatted_content or '').split()),
        character_count=len(formatted_content or '')
    )

    db.session.add(document)
    db.session.commit()

    flash(f'Dictionary entry "{document.title}" saved successfully', 'success')

    # Check if this was linked from an experiment
    experiment_id = request.form.get('experiment_id')
    if experiment_id:
        experiment = Experiment.query.get(experiment_id)
        if experiment and experiment.user_id == current_user.id:
            experiment.add_reference(document,
                                   include_in_analysis=request.form.get('include_in_analysis') == 'true')
            flash(f'Dictionary entry linked to experiment "{experiment.name}"', 'success')
            return redirect(url_for('experiments.view', experiment_id=experiment_id))

    return redirect(url_for('references.view', id=document.id))
