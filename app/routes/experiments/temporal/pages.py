"""Temporal management and timeline pages."""

from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import current_user
from app.utils.auth_decorators import api_require_login_for_write
from app.services.base_service import ServiceError, ValidationError, NotFoundError
from app.dto.temporal_dto import (
    UpdateTemporalTermsDTO,
    FetchTemporalDataDTO
)
from pydantic import ValidationError as PydanticValidationError
from app.models import Experiment, Document
from app import db
import json
from .. import experiments_bp
from .context import logger, temporal_service


@experiments_bp.route('/<int:experiment_id>/manage_temporal_terms')
@api_require_login_for_write
def manage_temporal_terms(experiment_id):
    """
    Manage terms for temporal evolution experiment

    REFACTORED: Now uses TemporalService
    """
    try:
        # Get temporal UI data from service
        data = temporal_service.get_temporal_ui_data(experiment_id)

        # Get document date statistics for UI
        # Note: Using Document.publication_date as single source of truth
        documents = Document.query.filter_by(experiment_id=experiment_id).all()

        docs_with_pub_dates = sum(1 for doc in documents if doc.publication_date)
        docs_with_any_dates = sum(1 for doc in documents if doc.publication_date or doc.created_at)

        data['document_count'] = len(documents)
        data['docs_with_pub_dates'] = docs_with_pub_dates
        data['docs_with_any_dates'] = docs_with_any_dates

        return render_template(
            'experiments/temporal_term_manager.html',
            experiment=data['experiment'],
            time_periods=data['time_periods'],
            terms=data['terms'],
            start_year=data['start_year'],
            end_year=data['end_year'],
            use_oed_periods=data['use_oed_periods'],
            oed_period_data=data['oed_period_data'],
            term_periods=data['term_periods'],
            orchestration_decisions=data['orchestration_decisions'],
            document_count=data['document_count'],
            docs_with_pub_dates=data['docs_with_pub_dates'],
            docs_with_any_dates=data['docs_with_any_dates'],
            period_documents=data['period_documents'],
            period_metadata=data['period_metadata'],
            semantic_events=data['semantic_events'],
            periods=data.get('periods', []),  # Full period objects for timeline view
            named_periods=data.get('named_periods', [])  # Named period ranges with start/end years
        )

    except ValidationError as e:
        # Business validation errors (wrong experiment type)
        flash(str(e), 'warning')
        return redirect(url_for('experiments.view', experiment_id=experiment_id))

    except NotFoundError as e:
        logger.warning(f"Experiment {experiment_id} not found: {e}")
        from flask import abort
        abort(404)

    except ServiceError as e:
        logger.error(f"Service error getting temporal UI data: {e}", exc_info=True)
        flash('Failed to load temporal term manager', 'danger')
        return redirect(url_for('experiments.view', experiment_id=experiment_id))

@experiments_bp.route('/<int:experiment_id>/timeline')
@api_require_login_for_write
def timeline_view(experiment_id):
    """
    Full-page horizontal timeline visualization for temporal evolution
    """
    try:
        # Get temporal UI data from service
        data = temporal_service.get_temporal_ui_data(experiment_id)

        return render_template(
            'experiments/temporal_timeline_view.html',
            experiment=data['experiment'],
            periods=data.get('periods', []),
            semantic_events=data['semantic_events']
        )

    except ValidationError as e:
        flash(str(e), 'warning')
        return redirect(url_for('experiments.view', experiment_id=experiment_id))

    except NotFoundError as e:
        logger.warning(f"Experiment {experiment_id} not found: {e}")
        from flask import abort
        abort(404)

    except ServiceError as e:
        logger.error(f"Service error getting timeline data: {e}", exc_info=True)
        flash('Failed to load timeline', 'danger')
        return redirect(url_for('experiments.view', experiment_id=experiment_id))
