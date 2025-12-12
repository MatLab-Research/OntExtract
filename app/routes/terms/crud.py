"""
Terms CRUD Operations Routes

This module handles basic CRUD operations for terms.

Routes:
- GET  /terms/                      - List all terms
- GET/POST /terms/add               - Add new term
- GET  /terms/<uuid:term_id>        - View term details
- GET/POST /terms/<uuid:term_id>/edit - Edit term
- POST /terms/<uuid:term_id>/delete - Delete term
- GET/POST /terms/<uuid:term_id>/add-version - Add term version
"""

from flask import render_template, request, redirect, url_for, flash, current_app
from flask_login import current_user
from app.utils.auth_decorators import write_login_required
from app import db
from app.models import Term, TermVersion, ContextAnchor
from app.forms import AddTermForm, EditTermForm, AddVersionForm
from app.services.provenance_service import provenance_service
from sqlalchemy import func, text
from datetime import datetime
import uuid as uuid_module

from . import terms_bp


@terms_bp.route('/')
def term_index():
    """Display alphabetical index of all terms - public view"""
    page = request.args.get('page', 1, type=int)
    per_page = 50

    # Search functionality
    search_query = request.args.get('search', '').strip()
    status_filter = request.args.get('status', '')
    domain_filter = request.args.get('domain', '')

    # Base query
    query = Term.query

    # Apply filters
    if search_query:
        query = query.filter(Term.term_text.ilike(f'%{search_query}%'))

    if status_filter:
        query = query.filter(Term.status == status_filter)

    if domain_filter:
        query = query.filter(Term.research_domain == domain_filter)

    # Order alphabetically
    query = query.order_by(Term.term_text)

    # Paginate
    terms = query.paginate(page=page, per_page=per_page, error_out=False)

    # Get available domains for filter dropdown
    domains = db.session.query(Term.research_domain).distinct().filter(
        Term.research_domain.isnot(None)
    ).all()
    domains = [d[0] for d in domains]

    return render_template('terms/index.html',
                         terms=terms,
                         search_query=search_query,
                         status_filter=status_filter,
                         domain_filter=domain_filter,
                         domains=domains)


@terms_bp.route('/add', methods=['GET', 'POST'])
@write_login_required
def add_term():
    """Add new term with WTForms validation"""
    form = AddTermForm()

    if form.validate_on_submit():
        try:
            # Check for duplicate across all users
            existing = Term.query.filter_by(term_text=form.term_text.data).first()
            if existing:
                flash(f'Term "{form.term_text.data}" already exists. Please choose a different term.', 'error')
                # Get existing research domains for error case as well
                existing_domains = db.session.query(Term.research_domain).distinct().filter(
                    Term.research_domain.isnot(None),
                    Term.research_domain != ''
                ).all()
                existing_domains = [d[0] for d in existing_domains]

                # Get documents for reference document selection
                from app.models.document import Document
                documents = Document.query.filter_by(user_id=current_user.id).order_by(Document.title).all()

                return render_template('terms/add.html', form=form, existing_domains=existing_domains, documents=documents)

            # Create term
            term = Term(
                term_text=form.term_text.data,
                description=form.description.data,
                etymology=form.etymology.data,
                notes=form.notes.data,
                research_domain=form.research_domain.data,
                selection_rationale=form.selection_rationale.data,
                historical_significance=form.historical_significance.data,
                created_by=current_user.id,
                status='active'
            )

            db.session.add(term)
            db.session.flush()

            # Parse context anchors
            anchor_list = []
            if form.context_anchor.data:
                anchor_list = [anchor.strip() for anchor in form.context_anchor.data.split(',') if anchor.strip()]

            # Create first version
            version = TermVersion(
                term_id=term.id,
                temporal_period=form.temporal_period.data,
                temporal_start_year=form.temporal_start_year.data,
                temporal_end_year=form.temporal_end_year.data,
                meaning_description=form.meaning_description.data,
                corpus_source=form.corpus_source.data,
                source_citation=form.source_citation.data,
                confidence_level=form.confidence_level.data,
                fuzziness_score=form.fuzziness_score.data,
                extraction_method='manual',
                context_anchor=anchor_list,
                generated_at_time=datetime.utcnow(),
                version_number=1,
                is_current=True,
                created_by=current_user.id
            )

            db.session.add(version)
            db.session.flush()

            # Add context anchors to the relationship table
            for anchor_term in anchor_list:
                anchor = ContextAnchor.get_or_create(anchor_term)
                version.add_context_anchor(anchor_term)

            db.session.commit()

            # Track term creation in provenance system
            try:
                provenance_service.track_term_creation(term, current_user)
            except Exception as prov_error:
                current_app.logger.error(f"Failed to track term creation provenance: {str(prov_error)}")
                # Don't fail the term creation if provenance tracking fails

            flash(f'Term "{form.term_text.data}" created successfully with first temporal version.', 'success')
            return redirect(url_for('terms.view_term', term_id=term.id))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating term: {str(e)}")
            flash('An error occurred while creating the term. Please try again.', 'error')

    # Get existing research domains for autocomplete
    existing_domains = db.session.query(Term.research_domain).distinct().filter(
        Term.research_domain.isnot(None),
        Term.research_domain != ''
    ).all()
    existing_domains = [d[0] for d in existing_domains]

    # Get documents for reference document selection
    from app.models.document import Document
    documents = Document.query.filter_by(user_id=current_user.id).order_by(Document.title).all()

    return render_template('terms/add.html', form=form, existing_domains=existing_domains, documents=documents)


@terms_bp.route('/<uuid:term_id>')
def view_term(term_id):
    """View term details and all versions"""
    term = Term.query.get_or_404(term_id)

    # Get all versions ordered by temporal period
    versions = term.get_all_versions_ordered()

    # Get semantic drift activities
    drift_activities = term.get_semantic_drift_activities()

    return render_template('terms/view.html',
                         term=term,
                         versions=versions,
                         drift_activities=drift_activities)


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


@terms_bp.route('/<uuid:term_id>/delete', methods=['POST'])
@write_login_required
def delete_term(term_id):
    """Delete a term (admin only)"""
    # Check if user is admin
    if not current_user.is_admin:
        flash('You do not have permission to delete terms.', 'error')
        return redirect(url_for('terms.term_index'))

    term = Term.query.get_or_404(term_id)
    term_text = term.term_text

    try:
        # Handle provenance records (purge or invalidate based on settings)
        prov_result = provenance_service.delete_or_invalidate_term_provenance(term_id)
        current_app.logger.info(f"Provenance handling for term {term_id}: {prov_result}")

        from app.models.semantic_drift import SemanticDriftActivity

        # Get all version IDs for this term
        version_ids = [str(v.id) for v in TermVersion.query.filter_by(term_id=term.id).all()]

        if version_ids:
            # Delete all semantic drift activities for this term
            activities_to_delete = SemanticDriftActivity.get_activities_for_term(term.id)
            for activity in activities_to_delete:
                db.session.delete(activity)

            # Delete term_version_anchors junction table entries
            for version_id in version_ids:
                db.session.execute(
                    text("DELETE FROM term_version_anchors WHERE term_version_id = :version_id"),
                    {'version_id': version_id}
                )

            # Update context_anchors to remove references to these versions
            for version_id in version_ids:
                # Set first_used_in to NULL for anchors that reference this version
                db.session.execute(
                    text("UPDATE context_anchors SET first_used_in = NULL WHERE first_used_in = :version_id"),
                    {'version_id': version_id}
                )
                # Set last_used_in to NULL for anchors that reference this version
                db.session.execute(
                    text("UPDATE context_anchors SET last_used_in = NULL WHERE last_used_in = :version_id"),
                    {'version_id': version_id}
                )

            # Now delete all versions
            TermVersion.query.filter_by(term_id=term.id).delete()

        # Now delete the term itself
        db.session.delete(term)
        db.session.commit()

        flash(f'Term "{term_text}" and all its versions have been deleted successfully.', 'success')

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting term {term_id}: {str(e)}")
        flash(f'An error occurred while deleting the term: {str(e)}', 'error')

    return redirect(url_for('terms.term_index'))


@terms_bp.route('/<uuid:term_id>/add-version', methods=['GET', 'POST'])
@write_login_required
def add_version(term_id):
    """Add new temporal version to existing term"""
    term = Term.query.get_or_404(term_id)
    form = AddVersionForm()

    if form.validate_on_submit():
        try:
            # Get data from form
            temporal_period = form.temporal_period.data.strip() if form.temporal_period.data else ''
            temporal_start_year = form.temporal_start_year.data
            temporal_end_year = form.temporal_end_year.data
            meaning_description = form.meaning_description.data.strip() if form.meaning_description.data else ''
            corpus_source = form.corpus_source.data.strip() if form.corpus_source.data else ''
            confidence_level = form.confidence_level.data if form.confidence_level.data else 'medium'
            context_anchors = form.context_anchor.data.strip() if form.context_anchor.data else ''
            notes = form.notes.data.strip() if form.notes.data else ''
            fuzziness_score = form.fuzziness_score.data

            # Handle derived from and derivation type (these might not be in the form)
            was_derived_from = request.form.get('was_derived_from')
            derivation_type = request.form.get('derivation_type', 'revision')

            # Get next version number
            max_version = db.session.query(func.max(TermVersion.version_number)).filter_by(term_id=term_id).scalar() or 0
            next_version = max_version + 1

            # Parse context anchors
            anchor_list = []
            if context_anchors:
                anchor_list = [anchor.strip() for anchor in context_anchors.split(',') if anchor.strip()]

            # Create new version
            version = TermVersion(
                term_id=term.id,
                temporal_period=temporal_period,
                temporal_start_year=temporal_start_year,
                temporal_end_year=temporal_end_year,
                meaning_description=meaning_description,
                corpus_source=corpus_source,
                confidence_level=confidence_level,
                certainty_notes=notes,
                fuzziness_score=fuzziness_score,
                extraction_method='manual',
                context_anchor=anchor_list,
                generated_at_time=datetime.utcnow(),
                version_number=next_version,
                is_current=request.form.get('is_current') == 'on',
                created_by=current_user.id,
                was_derived_from=uuid_module.UUID(was_derived_from) if was_derived_from else None,
                derivation_type=derivation_type
            )

            db.session.add(version)
            db.session.flush()

            # If this is set as current, update other versions
            if version.is_current:
                term.versions.filter(TermVersion.id != version.id).update({'is_current': False})

            # Add context anchors
            for anchor_term in anchor_list:
                anchor = ContextAnchor.get_or_create(anchor_term)
                version.add_context_anchor(anchor_term)

            db.session.commit()

            flash(f'New version added for "{term.term_text}" ({temporal_period}).', 'success')
            return redirect(url_for('terms.view_term', term_id=term_id))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error adding version: {str(e)}")
            flash('An error occurred while adding the version.', 'error')

    # Get existing versions for derivation dropdown
    existing_versions = term.get_all_versions_ordered()

    return render_template('terms/add_version.html', term=term, form=form, existing_versions=existing_versions)
