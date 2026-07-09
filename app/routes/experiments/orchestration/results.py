"""Orchestration result pages."""

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

        # Get document count and build document lookup
        from app.models import Document
        experiment_docs = Document.query.filter_by(experiment_id=experiment_id).all()
        document_count = len(experiment_docs)

        # Build document lookup dict for template (maps string ID to document info)
        document_lookup = {}
        for doc in experiment_docs:
            document_lookup[str(doc.id)] = {
                'id': doc.id,
                'uuid': str(doc.uuid),
                'title': doc.title,
                'authors': doc.authors,
                'publication_date': doc.publication_date.strftime('%Y') if doc.publication_date else None,
                'version_number': doc.version_number,
                'version_type': doc.version_type,
            }

        # Convert markdown to HTML for insights
        insights_html = None
        if run.cross_document_insights:
            insights_html = markdown.markdown(
                run.cross_document_insights,
                extensions=['fenced_code', 'tables', 'nl2br']
            )

        evolution_html = None
        if run.term_evolution_analysis:
            evolution_html = markdown.markdown(
                run.term_evolution_analysis,
                extensions=['fenced_code', 'tables', 'nl2br']
            )

        # Get temporal periods for temporal_evolution experiments
        temporal_periods = []
        if experiment.experiment_type == 'temporal_evolution':
            import json
            config = experiment.configuration or {}
            if isinstance(config, str):
                try:
                    config = json.loads(config)
                except (json.JSONDecodeError, TypeError):
                    config = {}
            temporal_periods = config.get('time_periods', [])

        return render_template(
            'experiments/llm_orchestration_results.html',
            experiment=experiment,
            run=run,
            duration=duration,
            total_operations=total_operations,
            document_count=document_count,
            document_lookup=document_lookup,
            insights_html=insights_html,
            evolution_html=evolution_html,
            temporal_periods=temporal_periods
        )

    except Exception as e:
        # Re-raise HTTPExceptions (like abort(404)) without catching them
        from werkzeug.exceptions import HTTPException
        if isinstance(e, HTTPException):
            raise
        logger.error(f"Error displaying LLM orchestration results: {e}", exc_info=True)
        from flask import abort
        abort(500)
