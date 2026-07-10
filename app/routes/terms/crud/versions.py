"""Temporal term-version creation routes."""

from datetime import datetime
import uuid as uuid_module

from flask import current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import func

from app import db
from app.forms import AddVersionForm
from app.models import ContextAnchor, Term, TermVersion
from app.utils.auth_decorators import write_login_required

from .. import terms_bp


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
