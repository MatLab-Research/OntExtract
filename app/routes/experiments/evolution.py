"""
Experiments Semantic Evolution Routes

This module handles semantic evolution analysis for experiments.

Routes:
- GET  /experiments/<id>/semantic_evolution_visual - Semantic evolution visualization
- POST /experiments/<id>/analyze_evolution         - Analyze term evolution over time

REFACTORED: Now uses EvolutionService with DTO validation
"""

from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import current_user
from app.utils.auth_decorators import api_require_login_for_write
from app.services.evolution_service import get_evolution_service
from app.services.base_service import ServiceError, ValidationError, NotFoundError
from app.dto.evolution_dto import AnalyzeEvolutionDTO
from pydantic import ValidationError as PydanticValidationError
import logging

from . import experiments_bp

logger = logging.getLogger(__name__)
evolution_service = get_evolution_service()


@experiments_bp.route('/<int:experiment_id>/semantic_evolution_visual')
@api_require_login_for_write
def semantic_evolution_visual(experiment_id):
    """
    Display semantic evolution visualization for any term with academic anchors

    REFACTORED: Now uses EvolutionService
    """
    try:
        # Get target term from URL parameter
        target_term = request.args.get('term')

        # Get evolution data from service
        data = evolution_service.get_evolution_visualization_data(experiment_id, target_term)

        # Get experiment for template context
        from app.models import Experiment
        experiment = Experiment.query.filter_by(id=experiment_id).first_or_404()

        return render_template(
            'experiments/semantic_evolution_visual.html',
            experiment=experiment,
            target_term=data['term'],
            term_record=data['term_record'],
            academic_anchors=data['academic_anchors'],
            oed_data=data['oed_data'],
            reference_data=data['reference_data'],
            temporal_span=data['temporal_span'],
            domains=data['domains']
        )

    except ValidationError as e:
        # Validation errors (no term specified, etc.)
        flash(str(e), 'warning')
        return redirect(url_for('experiments.view', experiment_id=experiment_id))

    except NotFoundError as e:
        # Term or versions not found
        flash(str(e), 'warning')
        return redirect(url_for('experiments.view', experiment_id=experiment_id))

    except ServiceError as e:
        logger.error(f"Service error getting evolution data: {e}", exc_info=True)
        flash('Failed to load evolution data', 'danger')
        return redirect(url_for('experiments.view', experiment_id=experiment_id))

    except Exception as e:
        logger.error(f"Unexpected error getting evolution data: {e}", exc_info=True)
        flash('An unexpected error occurred', 'danger')
        return redirect(url_for('experiments.view', experiment_id=experiment_id))


@experiments_bp.route('/<int:experiment_id>/analyze_evolution', methods=['POST'])
@api_require_login_for_write
def analyze_evolution(experiment_id):
    """
    Analyze the evolution of a term over time with detailed semantic drift analysis

    REFACTORED: Now uses EvolutionService with DTO validation
    """
    try:
        # Validate request data using DTO
        data = AnalyzeEvolutionDTO(**request.get_json())

        # Call service to analyze evolution
        result = evolution_service.analyze_evolution(
            experiment_id,
            term=data.term,
            periods=data.periods
        )

        return jsonify({
            'success': True,
            'analysis': result['analysis'],
            'drift_metrics': result['drift_metrics']
        }), 200

    except PydanticValidationError as e:
        # Validation errors from DTO
        logger.warning(f"Validation error analyzing evolution for experiment {experiment_id}: {e}")
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
        logger.error(f"Service error analyzing evolution for experiment {experiment_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to analyze evolution'
        }), 500

    except Exception as e:
        # Unexpected errors
        logger.error(f"Unexpected error analyzing evolution for experiment {experiment_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
