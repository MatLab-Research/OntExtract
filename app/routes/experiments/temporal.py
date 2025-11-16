"""
Experiments Temporal Analysis Routes

This module handles temporal evolution analysis for experiments.

Routes:
- GET  /experiments/<id>/manage_temporal_terms    - Temporal term management UI
- POST /experiments/<id>/update_temporal_terms    - Update temporal terms and periods
- GET  /experiments/<id>/get_temporal_terms       - Get saved temporal terms
- POST /experiments/<id>/fetch_temporal_data      - Fetch temporal data for analysis

REFACTORED: Now uses TemporalService with DTO validation
"""

from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import current_user
from app.utils.auth_decorators import api_require_login_for_write
from app.services.temporal_service import get_temporal_service
from app.services.base_service import ServiceError, ValidationError, NotFoundError
from app.dto.temporal_dto import (
    UpdateTemporalTermsDTO,
    FetchTemporalDataDTO
)
from pydantic import ValidationError as PydanticValidationError
import logging

from . import experiments_bp

logger = logging.getLogger(__name__)
temporal_service = get_temporal_service()


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
            orchestration_decisions=data['orchestration_decisions']
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


@experiments_bp.route('/<int:experiment_id>/update_temporal_terms', methods=['POST'])
@api_require_login_for_write
def update_temporal_terms(experiment_id):
    """
    Update terms and periods for a temporal evolution experiment

    REFACTORED: Now uses TemporalService with DTO validation
    """
    try:
        # Validate request data using DTO
        data = UpdateTemporalTermsDTO(**request.get_json())

        # Call service to update configuration
        temporal_service.update_temporal_configuration(
            experiment_id,
            terms=data.terms,
            periods=data.periods,
            temporal_data=data.temporal_data
        )

        return jsonify({
            'success': True,
            'message': 'Temporal terms updated successfully'
        }), 200

    except PydanticValidationError as e:
        # Validation errors from DTO
        logger.warning(f"Validation error updating temporal terms for experiment {experiment_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Validation failed',
            'details': e.errors()
        }), 400

    except NotFoundError as e:
        logger.warning(f"Experiment {experiment_id} not found: {e}")
        return jsonify({
            'success': False,
            'error': 'Experiment not found'
        }), 404

    except ServiceError as e:
        # Service errors (database, etc.)
        logger.error(f"Service error updating temporal terms for experiment {experiment_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to update temporal terms'
        }), 500

    except Exception as e:
        # Unexpected errors
        logger.error(f"Unexpected error updating temporal terms for experiment {experiment_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@experiments_bp.route('/<int:experiment_id>/get_temporal_terms')
@api_require_login_for_write
def get_temporal_terms(experiment_id):
    """
    Get saved temporal terms and data for an experiment

    REFACTORED: Now uses TemporalService
    """
    try:
        # Get temporal configuration from service
        config = temporal_service.get_temporal_configuration(experiment_id)

        return jsonify({
            'success': True,
            'terms': config['terms'],
            'periods': config['periods'],
            'temporal_data': config['temporal_data']
        }), 200

    except NotFoundError as e:
        logger.warning(f"Experiment {experiment_id} not found: {e}")
        return jsonify({
            'success': False,
            'error': 'Experiment not found'
        }), 404

    except ServiceError as e:
        logger.error(f"Service error getting temporal terms for experiment {experiment_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to get temporal terms'
        }), 500

    except Exception as e:
        logger.error(f"Unexpected error getting temporal terms for experiment {experiment_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@experiments_bp.route('/<int:experiment_id>/fetch_temporal_data', methods=['POST'])
@api_require_login_for_write
def fetch_temporal_data(experiment_id):
    """
    Fetch temporal data for a term across time periods using advanced temporal analysis

    REFACTORED: Now uses TemporalService with DTO validation
    """
    try:
        # Validate request data using DTO
        data = FetchTemporalDataDTO(**request.get_json())

        # Call service to fetch temporal analysis
        result = temporal_service.fetch_temporal_analysis(
            experiment_id,
            term=data.term,
            periods=data.periods,
            use_oed=data.use_oed
        )

        response = {
            'success': True,
            'temporal_data': result['temporal_data'],
            'frequency_data': result['frequency_data'],
            'drift_analysis': result['drift_analysis'],
            'narrative': result['narrative'],
            'periods_used': result['periods_used']
        }

        # Add OED data if available
        if 'oed_data' in result:
            response['oed_data'] = result['oed_data']

        return jsonify(response), 200

    except PydanticValidationError as e:
        # Validation errors from DTO
        logger.warning(f"Validation error fetching temporal data for experiment {experiment_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Validation failed',
            'details': e.errors()
        }), 400

    except ValidationError as e:
        # Business validation errors
        logger.warning(f"Business validation error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

    except NotFoundError as e:
        logger.warning(f"Experiment {experiment_id} not found: {e}")
        return jsonify({
            'success': False,
            'error': 'Experiment not found'
        }), 404

    except ServiceError as e:
        # Service errors
        logger.error(f"Service error fetching temporal data for experiment {experiment_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to fetch temporal data'
        }), 500

    except Exception as e:
        # Unexpected errors
        logger.error(f"Unexpected error fetching temporal data for experiment {experiment_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500
