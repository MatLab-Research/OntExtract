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

from flask import render_template, request, redirect, url_for, flash, send_file, current_app
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
    from app.utils.date_parser import parse_flexible_date

    reference = Document.query.filter_by(
        id=id,
        document_type='reference'
    ).first_or_404()

    if request.method == 'POST':
        try:
            # Update basic info
            reference.title = request.form.get('title', reference.title)
            reference.reference_subtype = request.form.get('reference_subtype', reference.reference_subtype)

            # Update normalized bibliographic columns
            reference.authors = request.form.get('authors', '').strip() or None
            reference.editor = request.form.get('editor', '').strip() or None
            reference.edition = request.form.get('edition', '').strip() or None

            # Parse publication date
            pub_date_str = request.form.get('publication_date', '').strip()
            if pub_date_str:
                reference.publication_date = parse_flexible_date(pub_date_str)
            else:
                reference.publication_date = None

            # Publication details
            reference.journal = request.form.get('journal', '').strip() or None
            reference.container_title = request.form.get('container_title', '').strip() or None
            reference.volume = request.form.get('volume', '').strip() or None
            reference.issue = request.form.get('issue', '').strip() or None
            reference.pages = request.form.get('pages', '').strip() or None
            reference.series = request.form.get('series', '').strip() or None
            reference.publisher = request.form.get('publisher', '').strip() or None
            reference.place = request.form.get('place', '').strip() or None

            # Identifiers
            reference.doi = request.form.get('doi', '').strip() or None
            reference.isbn = request.form.get('isbn', '').strip() or None
            reference.issn = request.form.get('issn', '').strip() or None
            reference.url = request.form.get('url', '').strip() or None

            # Parse access date
            access_date_str = request.form.get('access_date', '').strip()
            if access_date_str:
                reference.access_date = parse_flexible_date(access_date_str)
            else:
                reference.access_date = None

            # Dictionary/reference entry
            reference.entry_term = request.form.get('entry_term', '').strip() or None

            # Notes & abstract
            reference.abstract = request.form.get('abstract', '').strip() or None
            reference.notes = request.form.get('notes', '').strip() or None
            reference.citation = request.form.get('citation', '').strip() or None

            db.session.commit()
            flash('Reference updated successfully', 'success')
            return redirect(url_for('references.view', id=reference.id))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating reference: {str(e)}")
            flash(f'Error updating reference: {str(e)}', 'error')

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
