"""Experiment listing and creation-form pages."""

from flask import render_template, request
from flask_login import current_user
from sqlalchemy import or_

from app.models import Document, Experiment
from app.utils.auth_decorators import write_login_required

from .. import experiments_bp


@experiments_bp.route('/')
def index():
    """List all experiments for all users - public view"""
    experiments = Experiment.query.order_by(Experiment.created_at.desc()).all()
    return render_template('experiments/index.html', experiments=experiments)

@experiments_bp.route('/new')
@write_login_required
def new():
    """Show new experiment form - requires login"""
    from app.models import Term

    documents, references = _creation_resources()

    # Get all terms for the focus term dropdown
    terms_query = Term.query
    if not current_user.is_admin:
        terms_query = terms_query.filter(or_(
            Term.created_by == current_user.id,
            Term.created_by.is_(None),
        ))
    terms = terms_query.order_by(Term.term_text).all()

    # Handle single document mode
    mode = request.args.get('mode')
    selected_document = None
    document_title = None
    document_uuid = None
    generated_description = None

    if mode == 'single_document':
        document_uuid = request.args.get('document_uuid')

        if document_uuid:
            selected_document = Document.query.filter_by(
                uuid=document_uuid,
                document_type='document',
            ).first()
            if (
                selected_document
                and not current_user.can_edit_resource(
                    selected_document.get_root_document()
                )
            ):
                selected_document = None
            if selected_document:
                # Use document title (from metadata), fall back to display name
                title = selected_document.title or selected_document.get_display_name()
                document_title = title
                generated_description = f"Document analysis of {title}"
            else:
                document_uuid = None
                document_title = None

    return render_template('experiments/new.html',
                         documents=documents,
                         references=references,
                         terms=terms,
                         mode=mode,
                         selected_document=selected_document,
                         document_title=document_title,
                         document_uuid=document_uuid,
                         generated_description=generated_description)

@experiments_bp.route('/wizard')
@write_login_required
def wizard():
    """Guided wizard to create an experiment - requires login"""
    documents, references = _creation_resources()
    return render_template('experiments/wizard.html', documents=documents, references=references)


def _creation_resources():
    query = Document.query.filter_by(version_type='original')
    if not current_user.is_admin:
        query = query.filter_by(user_id=current_user.id)
    documents = query.filter_by(document_type='document').order_by(
        Document.created_at.desc()
    ).all()
    references = query.filter_by(document_type='reference').order_by(
        Document.created_at.desc()
    ).all()
    return documents, references
