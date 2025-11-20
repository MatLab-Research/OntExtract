"""
Experiments LLM Orchestration Routes

This module handles human-in-the-loop LLM orchestration for experiments.

Routes:
- GET  /experiments/<id>/orchestrated_analysis         - Orchestrated analysis UI
- POST /experiments/<id>/create_orchestration_decision - Create orchestration decision
- POST /experiments/<id>/run_orchestrated_analysis     - Run orchestrated analysis
- GET  /experiments/<id>/orchestration-results         - View orchestration results
- GET  /experiments/<id>/orchestration-provenance.json - Download PROV-O JSON

NEW LLM Analyze Routes:
- POST /experiments/<id>/orchestration/analyze         - Start LLM orchestration
- GET  /orchestration/status/<run_id>                  - Poll orchestration status
- POST /orchestration/approve-strategy/<run_id>        - Approve strategy & continue
- GET  /experiments/<id>/orchestration/llm-results/<run_id> - View LLM results

REFACTORED: Now uses OrchestrationService with DTO validation
"""

from flask import render_template, request, jsonify
from flask_login import current_user
from app.utils.auth_decorators import api_require_login_for_write
from app.services.orchestration_service import get_orchestration_service
from app.services.workflow_executor import get_workflow_executor
from app.services.base_service import ServiceError, ValidationError, NotFoundError
from app.dto.orchestration_dto import (
    CreateOrchestrationDecisionDTO,
    RunOrchestratedAnalysisDTO
)
from app.models.experiment_orchestration_run import ExperimentOrchestrationRun
from app.models import Experiment
from app import db
from pydantic import ValidationError as PydanticValidationError
import logging
from uuid import UUID
from datetime import datetime

from . import experiments_bp

logger = logging.getLogger(__name__)
orchestration_service = get_orchestration_service()
workflow_executor = get_workflow_executor()


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


# ============================================================================
# NEW: LLM Analyze Workflow Routes
# ============================================================================

@experiments_bp.route('/<int:experiment_id>/orchestration/analyze', methods=['POST'])
@api_require_login_for_write
def start_llm_orchestration(experiment_id):
    """
    Start LLM orchestration workflow (Stages 1-2: Analyze + Recommend)

    POST Body:
    {
        "review_choices": true,  // Whether to pause for user review
        "auto_approve_high_confidence": false,
        "confidence_threshold": 0.85
    }

    Returns:
    {
        "success": true,
        "run_id": "uuid-here",
        "status": "analyzing",
        "current_stage": "analyzing",
        "message": "Orchestration started"
    }
    """
    try:
        # Verify experiment exists
        experiment = Experiment.query.get(experiment_id)
        if not experiment:
            return jsonify({
                'success': False,
                'error': 'Experiment not found'
            }), 404

        # Get user preferences
        data = request.get_json() or {}
        review_choices = data.get('review_choices', True)

        # Create orchestration run
        run = ExperimentOrchestrationRun(
            experiment_id=experiment_id,
            user_id=current_user.id,
            status='analyzing',
            current_stage='analyzing'
        )
        db.session.add(run)
        db.session.commit()

        logger.info(f"Created orchestration run {run.id} for experiment {experiment_id}")

        # Execute recommendation phase in background
        try:
            result = workflow_executor.execute_recommendation_phase(
                run_id=run.id,
                review_choices=review_choices
            )

            return jsonify({
                'success': True,
                'run_id': str(run.id),
                'status': result['status'],
                'current_stage': result['status'],
                'message': 'Orchestration completed - awaiting review' if review_choices else 'Orchestration completed'
            }), 200

        except Exception as e:
            logger.error(f"Error executing recommendation phase: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': f'Orchestration failed: {str(e)}'
            }), 500

    except Exception as e:
        logger.error(f"Error starting orchestration for experiment {experiment_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@experiments_bp.route('/orchestration/status/<uuid:run_id>', methods=['GET'])
def get_orchestration_status(run_id):
    """
    Get current status of orchestration run

    Returns status, progress, and recommendations when ready
    """
    try:
        run = ExperimentOrchestrationRun.query.get(run_id)
        if not run:
            return jsonify({
                'error': 'Orchestration run not found'
            }), 404

        # Calculate progress percentage
        stage_progress = {
            'analyzing': 20,
            'recommending': 40,
            'reviewing': 50,
            'executing': 70,
            'synthesizing': 90,
            'completed': 100,
            'failed': 0
        }
        progress_percentage = stage_progress.get(run.status, 0)

        response = {
            'run_id': str(run.id),
            'status': run.status,
            'current_stage': run.current_stage or run.status,
            'progress_percentage': progress_percentage,
            'error_message': run.error_message
        }

        # Add stage completion flags
        response['stage_completed'] = {
            'analyze_experiment': run.experiment_goal is not None,
            'recommend_strategy': run.recommended_strategy is not None,
            'human_review': run.strategy_approved or False,
            'execute_strategy': run.processing_results is not None,
            'synthesize_experiment': run.cross_document_insights is not None
        }

        # If waiting for review, include strategy details
        if run.status == 'reviewing':
            response['awaiting_user_approval'] = True
            response['recommended_strategy'] = run.recommended_strategy
            response['strategy_reasoning'] = run.strategy_reasoning
            response['confidence'] = run.confidence
            response['experiment_goal'] = run.experiment_goal

        # If completed, include summary
        if run.status == 'completed':
            response['completed_at'] = run.completed_at.isoformat() if run.completed_at else None
            response['duration_seconds'] = (
                (run.completed_at - run.started_at).total_seconds()
                if run.completed_at and run.started_at else None
            )

        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Error getting orchestration status for run {run_id}: {e}", exc_info=True)
        return jsonify({
            'error': str(e)
        }), 500


@experiments_bp.route('/orchestration/approve-strategy/<uuid:run_id>', methods=['POST'])
@api_require_login_for_write
def approve_orchestration_strategy(run_id):
    """
    Approve strategy and continue to execution (Stages 4-5)

    POST Body:
    {
        "strategy_approved": true,
        "modified_strategy": {  // Optional: user modifications
            "217": ["extract_entities_spacy", "extract_temporal"]
        },
        "review_notes": "Added temporal extraction to first document"
    }

    Returns:
    {
        "success": true,
        "status": "executing",
        "message": "Strategy approved - beginning execution"
    }
    """
    try:
        run = ExperimentOrchestrationRun.query.get(run_id)
        if not run:
            return jsonify({
                'success': False,
                'error': 'Orchestration run not found'
            }), 404

        # Verify run is in correct state
        if run.status != 'reviewing':
            return jsonify({
                'success': False,
                'error': f'Cannot approve strategy in {run.status} state'
            }), 400

        # Get approval data
        data = request.get_json() or {}
        strategy_approved = data.get('strategy_approved', True)

        if not strategy_approved:
            # User rejected strategy
            run.status = 'cancelled'
            run.review_notes = data.get('review_notes', 'User rejected strategy')
            db.session.commit()

            return jsonify({
                'success': True,
                'status': 'cancelled',
                'message': 'Strategy rejected'
            }), 200

        # Execute processing phase
        try:
            result = workflow_executor.execute_processing_phase(
                run_id=run.id,
                modified_strategy=data.get('modified_strategy'),
                review_notes=data.get('review_notes'),
                reviewer_id=current_user.id
            )

            return jsonify({
                'success': True,
                'status': result['status'],
                'message': 'Strategy approved - processing complete',
                'execution_time': result['execution_time']
            }), 200

        except Exception as e:
            logger.error(f"Error executing processing phase: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': f'Processing failed: {str(e)}'
            }), 500

    except Exception as e:
        logger.error(f"Error approving strategy for run {run_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@experiments_bp.route('/<int:experiment_id>/orchestration/llm-results/<uuid:run_id>')
def llm_orchestration_results(experiment_id, run_id):
    """
    Display LLM orchestration results for an experiment

    Shows:
    - Cross-document insights
    - Term evolution analysis
    - Processing summary
    - PROV-O provenance
    """
    try:
        # Get experiment
        experiment = Experiment.query.get(experiment_id)
        if not experiment:
            from flask import abort
            abort(404)

        # Get orchestration run
        run = ExperimentOrchestrationRun.query.get(run_id)
        if not run or run.experiment_id != experiment_id:
            from flask import abort
            abort(404)

        # Calculate metrics
        duration = None
        if run.completed_at and run.started_at:
            duration_seconds = (run.completed_at - run.started_at).total_seconds()
            duration = {
                'seconds': duration_seconds,
                'formatted': f"{int(duration_seconds // 60)}m {int(duration_seconds % 60)}s"
            }

        # Count operations
        total_operations = 0
        if run.processing_results:
            for doc_results in run.processing_results.values():
                total_operations += len(doc_results)

        # Get document count
        from app.models import Document
        document_count = Document.query.filter_by(experiment_id=experiment_id).count()

        return render_template(
            'experiments/llm_orchestration_results.html',
            experiment=experiment,
            run=run,
            duration=duration,
            total_operations=total_operations,
            document_count=document_count
        )

    except Exception as e:
        logger.error(f"Error displaying LLM orchestration results: {e}", exc_info=True)
        from flask import abort
        abort(500)


@experiments_bp.route('/<int:experiment_id>/orchestration/llm-provenance/<uuid:run_id>')
def download_llm_provenance(experiment_id, run_id):
    """
    Download PROV-O provenance JSON for LLM orchestration run
    """
    try:
        run = ExperimentOrchestrationRun.query.get(run_id)
        if not run or run.experiment_id != experiment_id:
            return jsonify({'error': 'Orchestration run not found'}), 404

        # Build PROV-O structure
        provenance = {
            "@context": "http://www.w3.org/ns/prov",
            "@type": "prov:Bundle",
            "prov:generatedAtTime": run.started_at.isoformat() if run.started_at else None,
            "experiment": {
                "@id": f"experiment:{experiment_id}",
                "@type": "prov:Entity",
                "prov:type": "Experiment"
            },
            "orchestration_run": {
                "@id": f"run:{run.id}",
                "@type": "prov:Activity",
                "prov:startedAtTime": run.started_at.isoformat() if run.started_at else None,
                "prov:endedAtTime": run.completed_at.isoformat() if run.completed_at else None,
                "prov:used": f"experiment:{experiment_id}",
                "status": run.status,
                "confidence": run.confidence
            },
            "strategy": {
                "@id": f"strategy:{run.id}",
                "@type": "prov:Entity",
                "prov:wasGeneratedBy": f"run:{run.id}",
                "recommended_strategy": run.recommended_strategy,
                "modified_strategy": run.modified_strategy,
                "reasoning": run.strategy_reasoning
            },
            "execution_trace": run.execution_trace or [],
            "results": {
                "@id": f"results:{run.id}",
                "@type": "prov:Entity",
                "prov:wasGeneratedBy": f"run:{run.id}",
                "cross_document_insights": run.cross_document_insights,
                "term_evolution_analysis": run.term_evolution_analysis
            }
        }

        return jsonify(provenance), 200

    except Exception as e:
        logger.error(f"Error generating provenance: {e}", exc_info=True)
        return jsonify({'error': 'Failed to generate provenance data'}), 500
