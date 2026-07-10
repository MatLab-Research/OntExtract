"""Document metadata editing routes."""

from flask import current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user

from app import db
from app.models.document import Document
from app.utils.auth_decorators import write_login_required

from .. import text_input_bp


@text_input_bp.route('/document/<uuid:document_uuid>/edit', methods=['GET', 'POST'])
@write_login_required
def document_edit(document_uuid):
    """Edit document metadata"""
    from app.utils.date_parser import parse_flexible_date

    document = Document.query.filter_by(uuid=document_uuid).first_or_404()

    # Check permissions - only owner or admin can edit
    if not current_user.can_edit_resource(document):
        flash('You do not have permission to edit this document', 'error')
        return redirect(url_for('text_input.document_detail', document_uuid=document_uuid))

    if request.method == 'POST':
        try:
            # Update basic fields
            document.title = request.form.get('title', document.title)

            # Update bibliographic metadata
            document.authors = request.form.get('authors', '').strip() or None
            document.editor = request.form.get('editor', '').strip() or None
            document.edition = request.form.get('edition', '').strip() or None

            # Parse publication date
            pub_date_str = request.form.get('publication_date', '').strip()
            if pub_date_str:
                document.publication_date = parse_flexible_date(pub_date_str)
            else:
                document.publication_date = None

            # Publication details
            document.journal = request.form.get('journal', '').strip() or None
            document.container_title = request.form.get('container_title', '').strip() or None
            document.volume = request.form.get('volume', '').strip() or None
            document.issue = request.form.get('issue', '').strip() or None
            document.pages = request.form.get('pages', '').strip() or None
            document.series = request.form.get('series', '').strip() or None
            document.publisher = request.form.get('publisher', '').strip() or None
            document.place = request.form.get('place', '').strip() or None

            # Identifiers
            document.doi = request.form.get('doi', '').strip() or None
            document.isbn = request.form.get('isbn', '').strip() or None
            document.issn = request.form.get('issn', '').strip() or None
            document.url = request.form.get('url', '').strip() or None

            # Parse access date
            access_date_str = request.form.get('access_date', '').strip()
            if access_date_str:
                document.access_date = parse_flexible_date(access_date_str)
            else:
                document.access_date = None

            # Dictionary/reference entry
            document.entry_term = request.form.get('entry_term', '').strip() or None

            # Notes & abstract
            document.abstract = request.form.get('abstract', '').strip() or None
            document.notes = request.form.get('notes', '').strip() or None
            document.citation = request.form.get('citation', '').strip() or None

            # Document type
            document.reference_subtype = request.form.get('reference_subtype') or document.reference_subtype

            db.session.commit()

            flash('Document updated successfully', 'success')
            return redirect(url_for('text_input.document_detail', document_uuid=document_uuid))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating document: {str(e)}")
            flash(f'Error updating document: {str(e)}', 'error')

    return render_template('text_input/document_edit.html', document=document)
