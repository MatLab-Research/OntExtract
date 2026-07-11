"""Temporal analysis data retrieval routes."""

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
