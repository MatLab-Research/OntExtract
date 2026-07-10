"""Experiment listing and creation-form pages."""

from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import current_user
from app.utils.auth_decorators import api_require_login_for_write, write_login_required
from app import db
from app.models import Document, Experiment
from app.services.text_processing import TextProcessingService
from app.services.experiment_domain_comparison import DomainComparisonService
from app.dto.experiment_dto import (
    CreateExperimentDTO,
    UpdateExperimentDTO,
    ExperimentResponseDTO,
    ExperimentListItemDTO,
    ExperimentDetailDTO
)
from app.services.base_service import ServiceError, ValidationError
from pydantic import ValidationError as PydanticValidationError
from datetime import datetime
import json
from typing import Optional
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

    # Get documents and references separately for all users
    # Only show original (v1) documents - derived versions belong to their source experiments
    documents = Document.query.filter_by(document_type='document', version_type='original').order_by(Document.created_at.desc()).all()
    references = Document.query.filter_by(document_type='reference', version_type='original').order_by(Document.created_at.desc()).all()

    # Get all terms for the focus term dropdown
    terms = Term.query.order_by(Term.term_text).all()

    # Handle single document mode
    mode = request.args.get('mode')
    selected_document = None
    document_title = None
    document_uuid = None
    generated_description = None

    if mode == 'single_document':
        document_uuid = request.args.get('document_uuid')
        document_title = request.args.get('document_title')

        if document_uuid:
            selected_document = Document.query.filter_by(uuid=document_uuid).first()
            if selected_document:
                # Use document title (from metadata), fall back to display name
                title = selected_document.title or selected_document.get_display_name()
                generated_description = f"Document analysis of {title}"

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
    # Only show original (v1) documents - derived versions belong to their source experiments
    documents = Document.query.filter_by(document_type='document', version_type='original').order_by(Document.created_at.desc()).all()
    references = Document.query.filter_by(document_type='reference', version_type='original').order_by(Document.created_at.desc()).all()
    return render_template('experiments/wizard.html', documents=documents, references=references)
