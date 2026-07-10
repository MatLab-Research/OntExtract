"""Dictionary reference creation routes."""

from flask import flash, redirect, request, url_for
from flask_login import current_user

from app import db
from app.models.document import Document
from app.models.experiment import Experiment
from app.utils.auth_decorators import api_require_login_for_write

from .. import references_bp


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
