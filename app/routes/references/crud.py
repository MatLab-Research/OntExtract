"""
References CRUD Operations Routes

This module handles basic CRUD operations for reference documents.

Routes:
- GET  /references/            - List all references
- GET  /references/<id>        - View reference details
- GET  /references/<id>/edit   - Edit reference form
- POST /references/<id>/edit   - Update reference
- POST /references/<id>/delete - Delete reference
- GET  /references/<id>/download - Download reference file
"""

from flask import render_template, request, redirect, url_for, flash, send_file
from flask_login import current_user
from app.utils.auth_decorators import api_require_login_for_write
import os
from app import db
from app.models.document import Document
from app.models.experiment import Experiment

from . import references_bp


@references_bp.route('/')
def index():
    """List all references for all users - public view"""
    references = Document.query.filter_by(
        document_type='reference'
    ).order_by(Document.created_at.desc()).all()

    return render_template('references/index.html', references=references)


@references_bp.route('/<int:id>')
@api_require_login_for_write
def view(id):
    """View reference details"""
    reference = Document.query.filter_by(
        id=id,
        document_type='reference'
    ).first_or_404()

    # Get experiments that use this reference (use relationship.any to avoid typing issues)
    experiments_using = Experiment.query.filter(
        Experiment.references.any(Document.id == reference.id)
    ).all()

    return render_template('references/view.html',
                         reference=reference,
                         experiments_using=experiments_using)


@references_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@api_require_login_for_write
def edit(id):
    """Edit reference metadata"""
    reference = Document.query.filter_by(
        id=id,
        document_type='reference'
    ).first_or_404()

    if request.method == 'POST':
        # Update basic info
        reference.title = request.form.get('title', reference.title)
        reference.reference_subtype = request.form.get('reference_subtype', reference.reference_subtype)

        # Update source metadata
        authors = request.form.get('authors', '').split(',')
        authors = [a.strip() for a in authors if a.strip()]

        provided_meta = {
            'authors': authors,
            'publication_date': request.form.get('publication_date'),
            'journal': request.form.get('journal'),
            'doi': request.form.get('doi'),
            'isbn': request.form.get('isbn'),
            'url': request.form.get('url'),
            'abstract': request.form.get('abstract'),
            'citation': request.form.get('citation')
        }

        # Remove empty values and merge into existing metadata to preserve OED-specific fields
        provided_meta = {k: v for k, v in provided_meta.items() if v}
        existing_meta = reference.source_metadata or {}
        if not isinstance(existing_meta, dict):
            existing_meta = {}
        merged = {**existing_meta, **provided_meta}
        reference.source_metadata = merged if merged else None

        db.session.commit()
        flash('Reference updated successfully', 'success')
        return redirect(url_for('references.view', id=reference.id))

    return render_template('references/edit.html', reference=reference)


@references_bp.route('/<int:id>/delete', methods=['POST'])
@api_require_login_for_write
def delete(id):
    """Delete a reference"""
    reference = Document.query.filter_by(
        id=id,
        document_type='reference'
    ).first_or_404()

    # Delete file if exists
    reference.delete_file()

    # Delete from database
    db.session.delete(reference)
    db.session.commit()

    flash('Reference deleted successfully', 'success')
    return redirect(url_for('references.index'))


@references_bp.route('/<int:id>/download')
@api_require_login_for_write
def download(id: int):
    """Download the original file for a reference document if present."""
    doc = Document.query.filter_by(id=id).first_or_404()
    if not doc.file_path:
        flash('No file attached to this reference.', 'warning')
        return redirect(url_for('references.view', id=id))
    try:
        filename = doc.original_filename or os.path.basename(doc.file_path)
        return send_file(doc.file_path, as_attachment=True, download_name=filename)
    except Exception as e:
        flash(f'Failed to download file: {e}', 'error')
        return redirect(url_for('references.view', id=id))
