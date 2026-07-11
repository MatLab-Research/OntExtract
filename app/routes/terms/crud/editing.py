"""Term metadata editing routes."""

from flask import current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user

from app import db
from app.forms import EditTermForm
from app.models import Term, TermVersion
from app.services.provenance_service import provenance_service
from app.utils.auth_decorators import write_login_required

from .. import terms_bp


@terms_bp.route('/<uuid:term_id>/edit', methods=['GET', 'POST'])
@write_login_required
def edit_term(term_id):
    """Edit term basic information"""
    term = Term.query.get_or_404(term_id)

    # Check permissions
    if term.created_by != current_user.id and not current_user.is_admin:
        flash('You do not have permission to edit this term.', 'error')
        return redirect(url_for('terms.view_term', term_id=term_id))

    # Get all temporal versions for this term, ordered by latest first
    versions = TermVersion.query.filter_by(term_id=term.id).order_by(
        TermVersion.generated_at_time.desc()
    ).all()

    # Get the version ID from request (for editing specific versions)
    version_id = request.args.get('version_id') or request.form.get('selected_version_id')
    selected_version = None

    if version_id:
        selected_version = TermVersion.query.filter_by(id=version_id, term_id=term.id).first()

    # If no specific version selected, use the latest version
    if not selected_version and versions:
        selected_version = versions[0]

    # Initialize form with existing term data
    form = EditTermForm()

    if form.validate_on_submit():
        try:
            # Track what changed for provenance
            changes = {}
            if term.research_domain != form.research_domain.data:
                changes['research_domain'] = {'old': term.research_domain, 'new': form.research_domain.data}
            if term.status != form.status.data:
                changes['status'] = {'old': term.status, 'new': form.status.data}
            if term.notes != form.notes.data:
                changes['notes'] = {'old': term.notes, 'new': form.notes.data}

            # Update term fields from form (term_text is read-only)
            term.research_domain = form.research_domain.data
            term.status = form.status.data
            term.notes = form.notes.data
            term.updated_by = current_user.id

            db.session.commit()

            # Track term update in provenance system
            if changes:  # Only track if something actually changed
                try:
                    provenance_service.track_term_update(term, current_user, changes)
                except Exception as prov_error:
                    current_app.logger.error(f"Failed to track term update provenance: {str(prov_error)}")
                    # Don't fail the term update if provenance tracking fails

            flash(f'Term "{term.term_text}" updated successfully.', 'success')
            return redirect(url_for('terms.view_term', term_id=term_id))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating term: {str(e)}")
            flash('An error occurred while updating the term.', 'error')

    # Pre-populate form with existing data for GET requests
    if request.method == 'GET':
        form.term_text.data = term.term_text
        form.research_domain.data = term.research_domain
        form.status.data = term.status
        form.notes.data = term.notes

    # Get existing research domains for autocomplete
    existing_domains = db.session.query(Term.research_domain).distinct().filter(
        Term.research_domain.isnot(None),
        Term.research_domain != ''
    ).all()
    existing_domains = [d[0] for d in existing_domains]

    return render_template('terms/edit.html',
                         term=term,
                         form=form,
                         versions=versions,
                         selected_version=selected_version,
                         existing_domains=existing_domains)
