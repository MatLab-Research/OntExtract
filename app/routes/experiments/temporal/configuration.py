"""Temporal configuration and period generation routes."""

from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import current_user
from app.utils.auth_decorators import api_require_login_for_write
from app.services.temporal_service import get_temporal_service
from app.services.ontserve_client import get_ontserve_client
from app.services.base_service import ServiceError, ValidationError, NotFoundError
from app.dto.temporal_dto import (
    UpdateTemporalTermsDTO,
    FetchTemporalDataDTO
)
from pydantic import ValidationError as PydanticValidationError
from app.models import Experiment, Document
from app import db
import logging
import json
from .. import experiments_bp


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

@experiments_bp.route('/<int:experiment_id>/generate_periods_from_documents', methods=['POST'])
@api_require_login_for_write
def generate_periods_from_documents(experiment_id):
    """
    Generate time periods based on document publication dates

    Analyzes all documents in the experiment and creates evenly-spaced
    time periods covering the date range.
    """
    try:
        # Generate periods from document dates
        result = temporal_service.generate_periods_from_documents(experiment_id)

        return jsonify({
            'success': True,
            'periods': result['periods'],
            'document_count': result['document_count'],
            'date_range': result['date_range'],
            'source_type': result.get('source_type', 'publication dates'),
            'using_fallback': result.get('using_fallback', False),
            'message': f"Generated {len(result['periods'])} periods from {result['document_count']} documents"
        }), 200

    except ValidationError as e:
        # Business validation errors
        logger.warning(f"Validation error generating periods: {e}")
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
        logger.error(f"Service error generating periods for experiment {experiment_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to generate periods from documents'
        }), 500

    except Exception as e:
        logger.error(f"Unexpected error generating periods for experiment {experiment_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
