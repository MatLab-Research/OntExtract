"""Experiment editing routes."""

from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import current_user
from app.utils.auth_decorators import api_require_login_for_write, write_login_required
from app import db
from app.models import Document, Experiment
from app.services.text_processing import TextProcessingService
from app.services.experiment_domain_comparison import DomainComparisonService
from app.services.experiment_service import get_experiment_service
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
import logging
from .. import experiments_bp


@experiments_bp.route('/<int:experiment_id>/edit')
@write_login_required
def edit(experiment_id):
    """Edit experiment"""
    from app.models import Term

    experiment = Experiment.query.filter_by(id=experiment_id).first_or_404()

    # Can only edit experiments that are draft or error status
    if experiment.status == 'running':
        flash('Cannot edit an experiment that is currently running.', 'error')
        return redirect(url_for('experiments.view', experiment_id=experiment_id))

    if experiment.status == 'completed':
        flash('This experiment has been run and is locked to preserve provenance. Use "Duplicate" to create an editable copy.', 'warning')
        return redirect(url_for('experiments.view', experiment_id=experiment_id))

    # Get documents and references separately (matching new route structure)
    documents = Document.query.filter_by(document_type='document').order_by(Document.created_at.desc()).all()
    references = Document.query.filter_by(document_type='reference').order_by(Document.created_at.desc()).all()

    # Get all terms for the focus term dropdown
    terms = Term.query.order_by(Term.term_text).all()

    # Get IDs of documents and references already in the experiment
    selected_doc_ids = [doc.id for doc in experiment.documents]
    selected_ref_ids = [ref.id for ref in experiment.references]

    # Get focus term ID from proper term_id foreign key column
    selected_term_ids = []
    if experiment.term_id:
        selected_term_ids = [str(experiment.term_id)]

    return render_template('experiments/edit.html',
                         experiment=experiment,
                         documents=documents,
                         references=references,
                         terms=terms,
                         selected_doc_ids=selected_doc_ids,
                         selected_ref_ids=selected_ref_ids,
                         selected_term_ids=selected_term_ids)

@experiments_bp.route('/<int:experiment_id>/update', methods=['POST'])
@api_require_login_for_write
def update(experiment_id):
    """
    Update an existing experiment

    REFACTORED: Now uses ExperimentService with DTO validation
    """
    try:
        # Validate request data using DTO (automatic validation)
        data = UpdateExperimentDTO(**request.get_json())

        # Call service to update experiment (all business logic in service)
        experiment = experiment_service.update_experiment(experiment_id, data, current_user.id)

        # Return consistent response
        return jsonify({
            'success': True,
            'message': 'Experiment updated successfully',
            'experiment_id': experiment.id
        }), 200

    except PydanticValidationError as e:
        # Validation errors from DTO
        logger.warning(f"Validation error updating experiment {experiment_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Validation failed',
            'details': e.errors()
        }), 400

    except ValidationError as e:
        # Business validation errors (e.g., cannot update running experiment)
        logger.warning(f"Business validation error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

    except PermissionError as e:
        # Permission errors
        logger.warning(f"Permission error: {e}")
        return jsonify({
            'success': False,
            'error': 'Permission denied'
        }), 403

    except ServiceError as e:
        # Service errors (database, etc.)
        logger.error(f"Service error updating experiment {experiment_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to update experiment'
        }), 500

    except Exception as e:
        # Unexpected errors
        logger.error(f"Unexpected error updating experiment {experiment_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred'
        }), 500
