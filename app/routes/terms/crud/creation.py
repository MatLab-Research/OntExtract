"""Term creation routes."""

from datetime import datetime

from flask import current_app, flash, redirect, render_template, url_for
from flask_login import current_user

from app import db
from app.forms import AddTermForm
from app.models import ContextAnchor, Term, TermVersion
from app.services.provenance_service import provenance_service
from app.utils.auth_decorators import write_login_required

from .. import terms_bp


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
