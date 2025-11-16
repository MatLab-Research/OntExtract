"""
Experiments Term Management Routes

This module handles term management for domain comparison experiments.

Routes:
- GET  /experiments/<id>/manage_terms       - Term management UI
- POST /experiments/<id>/update_terms       - Update terms and domains
- GET  /experiments/<id>/get_terms          - Get saved terms
- POST /experiments/<id>/fetch_definitions  - Fetch term definitions

REFACTORED: Now uses TermService with DTO validation
"""

from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import current_user
from app.utils.auth_decorators import api_require_login_for_write
from app.services.term_service import get_term_service
from app.services.base_service import ServiceError, ValidationError
from app.dto.term_dto import UpdateTermsDTO, FetchDefinitionsDTO
from pydantic import ValidationError as PydanticValidationError
import logging

from . import experiments_bp

logger = logging.getLogger(__name__)
term_service = get_term_service()


@experiments_bp.route('/<int:experiment_id>/manage_terms')
@api_require_login_for_write
def manage_terms(experiment_id):
    """
    Manage terms for domain comparison experiment

    REFACTORED: Now uses TermService
    """
    try:
        # Get term configuration from service
        config = term_service.get_term_configuration(experiment_id)

        # Get experiment for template context
        from app.models import Experiment
        experiment = Experiment.query.filter_by(id=experiment_id).first_or_404()

        return render_template(
            'experiments/term_manager.html',
            experiment=experiment,
            domains=config['domains'],
            terms=config['terms']
        )

    except ValidationError as e:
        # Not a domain comparison experiment
        flash(str(e), 'warning')
        return redirect(url_for('experiments.view', experiment_id=experiment_id))

    except ServiceError as e:
        logger.error(f"Service error getting term configuration: {e}", exc_info=True)
        flash('Failed to load term configuration', 'danger')
        return redirect(url_for('experiments.view', experiment_id=experiment_id))

    except Exception as e:
        logger.error(f"Unexpected error getting term configuration: {e}", exc_info=True)
        flash('An unexpected error occurred', 'danger')
        return redirect(url_for('experiments.view', experiment_id=experiment_id))


@experiments_bp.route('/<int:experiment_id>/update_terms', methods=['POST'])
@api_require_login_for_write
def update_terms(experiment_id):
    """
    Update terms and domains for an experiment

    REFACTORED: Now uses TermService with DTO validation
    """
    try:
        # Validate request data using DTO
        data = UpdateTermsDTO(**request.get_json())

        # Call service to update configuration
        term_service.update_term_configuration(
            experiment_id,
            terms=data.terms,
            domains=data.domains,
            definitions=data.definitions
        )

        return jsonify({
            'success': True,
            'message': 'Terms updated successfully'
        }), 200

    except PydanticValidationError as e:
        # Validation errors from DTO
        logger.warning(f"Validation error updating terms for experiment {experiment_id}: {e}")
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

    except ServiceError as e:
        # Service errors (database, etc.)
        logger.error(f"Service error updating terms for experiment {experiment_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to update terms'
        }), 500

    except Exception as e:
        # Unexpected errors
        logger.error(f"Unexpected error updating terms for experiment {experiment_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred'
        }), 500


@experiments_bp.route('/<int:experiment_id>/get_terms')
@api_require_login_for_write
def get_terms(experiment_id):
    """
    Get saved terms and definitions for an experiment

    REFACTORED: Now uses TermService
    """
    try:
        # Get term configuration from service
        config = term_service.get_term_configuration(experiment_id)

        return jsonify({
            'success': True,
            'terms': config['terms'],
            'domains': config['domains'],
            'definitions': config['definitions']
        }), 200

    except ValidationError as e:
        # Business validation errors
        logger.warning(f"Validation error getting terms for experiment {experiment_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

    except ServiceError as e:
        # Service errors
        logger.error(f"Service error getting terms for experiment {experiment_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to get terms'
        }), 500

    except Exception as e:
        # Unexpected errors
        logger.error(f"Unexpected error getting terms for experiment {experiment_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred'
        }), 500


@experiments_bp.route('/<int:experiment_id>/fetch_definitions', methods=['POST'])
@api_require_login_for_write
def fetch_definitions(experiment_id):
    """
    Fetch definitions for a term from references and ontologies

    REFACTORED: Now uses TermService with DTO validation
    """
    try:
        # Validate request data using DTO
        data = FetchDefinitionsDTO(**request.get_json())

        # Call service to fetch definitions
        result = term_service.fetch_definitions(
            experiment_id,
            term=data.term,
            domains=data.domains
        )

        return jsonify({
            'success': True,
            'definitions': result['definitions'],
            'ontology_mappings': result['ontology_mappings']
        }), 200

    except PydanticValidationError as e:
        # Validation errors from DTO
        logger.warning(f"Validation error fetching definitions for experiment {experiment_id}: {e}")
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

    except ServiceError as e:
        # Service errors
        logger.error(f"Service error fetching definitions for experiment {experiment_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to fetch definitions'
        }), 500

    except Exception as e:
        # Unexpected errors
        logger.error(f"Unexpected error fetching definitions for experiment {experiment_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred'
        }), 500
