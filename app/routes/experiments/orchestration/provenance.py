"""Orchestration provenance download routes."""

from flask import render_template, request, jsonify
from flask_login import current_user
from app.utils.auth_decorators import api_require_login_for_write
from app.services.orchestration_service import get_orchestration_service
from app.services.workflow_executor import get_workflow_executor
from app.services.base_service import ServiceError, NotFoundError
import markdown
from app.models.experiment_orchestration_run import ExperimentOrchestrationRun
from app.models import Experiment
from app import db
import logging
from datetime import datetime
from .. import experiments_bp


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
