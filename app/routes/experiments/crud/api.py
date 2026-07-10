"""Experiment JSON API routes."""

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
from .context import experiment_service, logger


@experiments_bp.route('/api/list')
def api_list():
    """
    API endpoint to list experiments

    REFACTORED: Now uses ExperimentService with DTOs
    """
    try:
        # Get experiments from service (returns DTOs)
        experiments = experiment_service.list_experiments()

        # Convert DTOs to dicts for JSON response
        return jsonify({
            'success': True,
            'experiments': [exp.to_dict() for exp in experiments]
        }), 200

    except ServiceError as e:
        logger.error(f"Service error listing experiments: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to list experiments'
        }), 500

    except Exception as e:
        logger.error(f"Unexpected error listing experiments: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred'
        }), 500

@experiments_bp.route('/api/<int:experiment_id>')
def api_get(experiment_id):
    """
    API endpoint to get experiment details

    REFACTORED: Now uses ExperimentService with DTOs
    """
    try:
        # Get experiment detail from service (returns DTO)
        experiment = experiment_service.get_experiment_detail(experiment_id)

        # Convert DTO to dict for JSON response
        return jsonify({
            'success': True,
            'experiment': experiment.to_dict()
        }), 200

    except ServiceError as e:
        logger.error(f"Service error getting experiment {experiment_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Experiment not found'
        }), 404

    except Exception as e:
        logger.error(f"Unexpected error getting experiment {experiment_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred'
        }), 500
