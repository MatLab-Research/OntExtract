"""
Experiments LLM Orchestration Routes

This module handles human-in-the-loop LLM orchestration for experiments.

Routes:
- GET  /experiments/<id>/orchestrated_analysis         - Orchestrated analysis UI
- POST /experiments/<id>/create_orchestration_decision - Create orchestration decision
- POST /experiments/<id>/run_orchestrated_analysis     - Run orchestrated analysis
- GET  /experiments/<id>/orchestration-results         - View orchestration results
- GET  /experiments/<id>/orchestration-provenance.json - Download PROV-O JSON

REFACTORED: Now uses OrchestrationService with DTO validation
"""

from flask import render_template, request, jsonify
from flask_login import current_user
from app.utils.auth_decorators import api_require_login_for_write
from app.services.orchestration_service import get_orchestration_service
from app.services.base_service import ServiceError, ValidationError, NotFoundError
from app.dto.orchestration_dto import (
    CreateOrchestrationDecisionDTO,
    RunOrchestratedAnalysisDTO
)
from pydantic import ValidationError as PydanticValidationError
import logging

from . import experiments_bp

logger = logging.getLogger(__name__)
orchestration_service = get_orchestration_service()


@experiments_bp.route('/<int:experiment_id>/orchestrated_analysis')
@api_require_login_for_write
def orchestrated_analysis(experiment_id):
    """
    Human-in-the-loop orchestrated analysis interface

    REFACTORED: Now uses OrchestrationService
    """
    try:
        # Get orchestration UI data from service
        data = orchestration_service.get_orchestration_ui_data(experiment_id)

        return render_template(
            'experiments/orchestrated_analysis.html',
            experiment=data['experiment'],
            decisions=data['decisions'],
            patterns=data['patterns'],
            terms=data['terms']
        )

    except NotFoundError as e:
        logger.warning(f"Experiment {experiment_id} not found: {e}")
        from flask import abort
        abort(404)

    except ServiceError as e:
        logger.error(f"Service error getting orchestration UI data: {e}", exc_info=True)
        from flask import abort
        abort(500)


@experiments_bp.route('/<int:experiment_id>/create_orchestration_decision', methods=['POST'])
@api_require_login_for_write
def create_orchestration_decision(experiment_id):
    """
    Create a new orchestration decision for human feedback

    REFACTORED: Now uses OrchestrationService with DTO validation
    """
    try:
        # Validate request data using DTO
        data = CreateOrchestrationDecisionDTO(**request.get_json())

        # Call service to create decision
        result = orchestration_service.create_orchestration_decision(
            experiment_id,
            term_text=data.term_text,
            user_id=current_user.id
        )

        return jsonify({
            'success': True,
            'message': 'Orchestration decision created successfully',
            'decision_id': result['decision_id'],
            'selected_tools': result['selected_tools'],
            'embedding_model': result['embedding_model'],
            'confidence': result['confidence'],
            'reasoning': result['reasoning']
        }), 201

    except PydanticValidationError as e:
        # Validation errors from DTO
        logger.warning(f"Validation error creating orchestration decision for experiment {experiment_id}: {e}")
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
        logger.error(f"Service error creating orchestration decision for experiment {experiment_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to create orchestration decision'
        }), 500

    except Exception as e:
        # Unexpected errors
        logger.error(f"Unexpected error creating orchestration decision for experiment {experiment_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@experiments_bp.route('/<int:experiment_id>/run_orchestrated_analysis', methods=['POST'])
@api_require_login_for_write
def run_orchestrated_analysis(experiment_id):
    """
    Run analysis with LLM orchestration decisions and real-time feedback

    REFACTORED: Now uses OrchestrationService with DTO validation
    """
    try:
        # Validate request data using DTO
        data = RunOrchestratedAnalysisDTO(**request.get_json())

        # Call service to run analysis
        result = orchestration_service.run_orchestrated_analysis(
            experiment_id,
            terms=data.terms,
            user_id=current_user.id
        )

        return jsonify({
            'success': True,
            'message': f'Orchestrated analysis initiated for {len(data.terms)} terms',
            'results': result['results'],
            'total_decisions': result['total_decisions']
        }), 200

    except PydanticValidationError as e:
        # Validation errors from DTO
        logger.warning(f"Validation error running orchestrated analysis for experiment {experiment_id}: {e}")
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
        logger.error(f"Service error running orchestrated analysis for experiment {experiment_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to run orchestrated analysis'
        }), 500

    except Exception as e:
        # Unexpected errors
        logger.error(f"Unexpected error running orchestrated analysis for experiment {experiment_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@experiments_bp.route('/<int:experiment_id>/orchestration-results')
def orchestration_results(experiment_id):
    """
    Display orchestration results for an experiment

    REFACTORED: Now uses OrchestrationService
    """
    try:
        # Get orchestration results from service
        data = orchestration_service.get_orchestration_results(experiment_id)

        # Allow template override via query parameter (for backward compatibility)
        template = request.args.get('template', 'enhanced')
        if template == 'compact':
            template_name = 'experiments/orchestration_results.html'
        else:
            template_name = 'experiments/orchestration_results_enhanced.html'

        return render_template(
            template_name,
            experiment=data['experiment'],
            decisions=data['decisions'],
            total_decisions=data['total_decisions'],
            completed_decisions=data['completed_decisions'],
            avg_confidence=data['avg_confidence'],
            recent_decision=data['recent_decision'],
            cross_document_insights=data['cross_document_insights'],
            duration=data['duration'],
            document_count=data['document_count']
        )

    except NotFoundError as e:
        logger.warning(f"Experiment {experiment_id} not found: {e}")
        from flask import abort
        abort(404)

    except ServiceError as e:
        logger.error(f"Service error getting orchestration results: {e}", exc_info=True)
        from flask import abort
        abort(500)


@experiments_bp.route('/<int:experiment_id>/orchestration-provenance.json')
def orchestration_provenance_json(experiment_id):
    """
    Download PROV-O compliant JSON provenance record for orchestration decisions

    REFACTORED: Now uses OrchestrationService
    """
    try:
        # Get provenance data from service
        provenance_data = orchestration_service.get_orchestration_provenance(experiment_id)

        return jsonify(provenance_data), 200

    except NotFoundError as e:
        logger.warning(f"Experiment {experiment_id} not found: {e}")
        return jsonify({
            'error': 'Experiment not found'
        }), 404

    except ServiceError as e:
        logger.error(f"Service error generating provenance: {e}", exc_info=True)
        return jsonify({
            'error': 'Failed to generate provenance data'
        }), 500
