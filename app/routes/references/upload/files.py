"""General reference file upload routes."""

from flask import current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user
from werkzeug.utils import secure_filename

from app import db
from app.models.document import Document
from app.models.experiment import Experiment
from app.services.text_processing import TextProcessingService
from app.utils.auth_decorators import api_require_login_for_write
from app.utils.file_handler import FileHandler

from .. import references_bp


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
