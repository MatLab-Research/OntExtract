"""
Flask routes for experiment-level orchestration.

Implements the 5-stage workflow:
1. Analyze Experiment - Understand goals and context
2. Recommend Strategy - Suggest processing tools per document
3. Human Review - Optional approval/modification (conditional)
4. Execute Strategy - Process all documents with chosen tools
5. Synthesize Experiment - Generate cross-document insights
"""

from flask import Blueprint, render_template, request, jsonify, Response, current_app
from flask_login import current_user, login_required
from app.utils.auth_decorators import api_require_login_for_write
from app import db
from app.models import Experiment, Document
from app.models.experiment_orchestration_run import ExperimentOrchestrationRun
from datetime import datetime
from typing import List, Dict, Any, Optional
import uuid
import json
import time
import markdown


orchestration_bp = Blueprint('orchestration', __name__, url_prefix='/orchestration')


@orchestration_bp.route('/analyze-experiment/<int:experiment_id>', methods=['POST'])
@api_require_login_for_write
def analyze_experiment(experiment_id: int):
    """
    Start experiment-level orchestration.

    Validates experiment exists and user has access, fetches all documents,
    creates initial state, and starts LangGraph execution for Stages 1-2
    (analysis and strategy recommendation).

    The workflow stops at Stage 2 for user review. The review page will
    allow approval before continuing to Stages 4-5 (execution and synthesis).

    Request body:
        {
            "review_choices": true  // Always true for this implementation
        }

    Returns:
        {
            "success": true,
            "run_id": "uuid",
            "message": "Orchestration started"
        }
    """
    try:
        # Get experiment
        experiment = Experiment.query.get(experiment_id)
        if not experiment:
            return jsonify({'error': 'Experiment not found'}), 404

        # Validate user has access (all experiments are public view)
        # Write operations already protected by @api_require_login_for_write

        # Get request data
        data = request.get_json() or {}
        review_choices = data.get('review_choices', True)  # Always use review

        # Fetch all experiment documents
        documents_query = experiment.documents.all()
        if not documents_query:
            return jsonify({'error': 'No documents in experiment'}), 400

        # Build document list for orchestration
        documents = []
        for doc in documents_query:
            documents.append({
                'id': str(doc.id),
                'title': doc.title,
                'content': doc.content or '',
                'metadata': {
                    'file_type': doc.file_type,
                    'word_count': doc.word_count,
                    'created_at': doc.created_at.isoformat() if doc.created_at else None
                }
            })

        # Get focus term if exists
        focus_term = experiment.term.term_text if experiment.term else None

        # Create orchestration run record
        run_id = uuid.uuid4()
        orchestration_run = ExperimentOrchestrationRun(
            id=run_id,
            experiment_id=experiment_id,
            user_id=current_user.id,
            status='analyzing',
            current_stage='analyzing',
            started_at=datetime.utcnow()
        )
        db.session.add(orchestration_run)
        db.session.commit()

        # Start Celery task for background processing
        # The task rebuilds state from database, so we just pass the run_id
        from app.tasks.orchestration import run_orchestration_task
        task = run_orchestration_task.delay(str(run_id), review_choices)

        # Store task ID for monitoring
        orchestration_run.celery_task_id = task.id
        db.session.commit()

        current_app.logger.info(f"Started Celery task {task.id} for orchestration run {run_id}")

        return jsonify({
            'success': True,
            'run_id': str(run_id),
            'celery_task_id': task.id,
            'message': 'Orchestration started - analyzing experiment'
        })

    except Exception as e:
        current_app.logger.error(f"Error starting orchestration: {str(e)}")
        return jsonify({'error': str(e)}), 500


@orchestration_bp.route('/experiment/<run_id>/status')
def experiment_status(run_id: str):
    """
    Server-Sent Events endpoint for real-time progress tracking.

    Streams progress updates during Stages 1-2 (recommendation phase).
    Closes stream when status reaches 'strategy_ready' (review needed)
    or 'failed' (error occurred).

    SSE format:
        data: {"stage": "analyzing", "progress": 10, "message": "..."}
        data: {"stage": "recommending", "progress": 50, "message": "..."}
        data: {"status": "strategy_ready", "progress": 100}
    """
    # Capture app instance for generator context
    app = current_app._get_current_object()

    def generate():
        try:
            # Parse UUID
            try:
                run_uuid = uuid.UUID(run_id)
            except ValueError:
                yield f"data: {json.dumps({'error': 'Invalid run ID'})}\n\n"
                return

            # Find orchestration run (need app context for db query)
            with app.app_context():
                orchestration_run = ExperimentOrchestrationRun.query.get(run_uuid)
                if not orchestration_run:
                    yield f"data: {json.dumps({'error': 'Orchestration run not found'})}\n\n"
                    return

                # Stream progress updates
                last_stage = None
                while True:
                    # Refresh from database
                    db.session.refresh(orchestration_run)

                    current_stage = orchestration_run.current_stage
                    status = orchestration_run.status

                    # Map stages to progress percentages
                    stage_progress = {
                        'analyzing': 25,
                        'recommending': 75,
                        'reviewing': 100,
                        'strategy_ready': 100
                    }

                    progress = stage_progress.get(current_stage, 0)

                    # Only send update if stage changed
                    if current_stage != last_stage:
                        message = {
                            'stage': current_stage,
                            'status': status,
                            'progress': progress,
                            'message': get_stage_message(current_stage, status)
                        }

                        yield f"data: {json.dumps(message)}\n\n"
                        last_stage = current_stage

                    # Check if workflow finished (strategy ready for review)
                    # Handle both 'strategy_ready' and 'reviewing' statuses
                    if status in ('strategy_ready', 'reviewing'):
                        yield f"data: {json.dumps({'status': 'strategy_ready', 'progress': 100})}\n\n"
                        break

                    # Check if workflow failed
                    if status == 'failed':
                        yield f"data: {json.dumps({'status': 'failed', 'error': orchestration_run.error_message})}\n\n"
                        break

                    # Send heartbeat every 2 seconds
                    time.sleep(2)
                    yield f"data: {json.dumps({'heartbeat': True})}\n\n"

        except Exception as e:
            # Don't use current_app.logger in generator - just yield error
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(generate(), mimetype='text/event-stream')


@orchestration_bp.route('/experiment/<run_id>/review')
def review_strategy(run_id: str):
    """
    Display strategy review page.

    Shows:
    - Experiment goal (Stage 1)
    - Recommended strategy per document (Stage 2)
    - LLM reasoning and confidence
    - Interactive tool selection interface
    - Approve/Cancel buttons

    User can modify tool selections before approval.
    """
    try:
        # Parse UUID
        try:
            run_uuid = uuid.UUID(run_id)
        except ValueError:
            return "Invalid run ID", 400

        # Find orchestration run
        orchestration_run = ExperimentOrchestrationRun.query.get(run_uuid)
        if not orchestration_run:
            return "Orchestration run not found", 404

        # Check status
        if orchestration_run.status != 'strategy_ready':
            return f"Strategy not ready for review (status: {orchestration_run.status})", 400

        # Get experiment and documents
        experiment = orchestration_run.experiment
        documents = experiment.documents.all()

        # Get available tools for UI
        from app.services.tool_registry import TOOL_REGISTRY, get_available_tools
        available_tools = get_available_tools(include_stubs=True)

        # Build document strategy data for template
        document_strategies = []
        for doc in documents:
            doc_id = str(doc.id)
            recommended_tools = orchestration_run.recommended_strategy.get(doc_id, [])

            document_strategies.append({
                'id': doc_id,
                'title': doc.title,
                'recommended_tools': recommended_tools,
                'word_count': doc.word_count
            })

        return render_template(
            'orchestration/experiment_review.html',
            orchestration_run=orchestration_run,
            experiment=experiment,
            document_strategies=document_strategies,
            available_tools=available_tools,
            tool_registry=TOOL_REGISTRY
        )

    except Exception as e:
        current_app.logger.error(f"Error loading review page: {str(e)}")
        return str(e), 500


@orchestration_bp.route('/experiment/<run_id>/approve', methods=['POST'])
@api_require_login_for_write
def approve_strategy(run_id: str):
    """
    Approve and execute the processing strategy.

    Request body:
        {
            "approved": true,
            "modified_strategy": {"doc_id": ["tool1", "tool2"], ...},  // Optional
            "review_notes": "..."  // Optional
        }

    Executes Stages 4-5 (execute_strategy and synthesize_experiment) in background.

    Returns:
        {"success": true, "message": "Strategy approved, processing started"}
    """
    try:
        # Parse UUID
        try:
            run_uuid = uuid.UUID(run_id)
        except ValueError:
            return jsonify({'error': 'Invalid run ID'}), 400

        # Find orchestration run
        orchestration_run = ExperimentOrchestrationRun.query.get(run_uuid)
        if not orchestration_run:
            return jsonify({'error': 'Orchestration run not found'}), 404

        # Check status
        if orchestration_run.status != 'strategy_ready':
            return jsonify({'error': f'Cannot approve - status is {orchestration_run.status}'}), 400

        # Get request data
        data = request.get_json()
        approved = data.get('approved', False)
        modified_strategy = data.get('modified_strategy')
        review_notes = data.get('review_notes', '')

        if not approved:
            # User rejected - mark as cancelled
            orchestration_run.status = 'cancelled'
            orchestration_run.strategy_approved = False
            orchestration_run.review_notes = review_notes
            orchestration_run.reviewed_by = current_user.id
            orchestration_run.reviewed_at = datetime.utcnow()
            db.session.commit()

            return jsonify({
                'success': True,
                'message': 'Strategy rejected - orchestration cancelled'
            })

        # User approved - update database
        orchestration_run.strategy_approved = True
        orchestration_run.modified_strategy = modified_strategy
        orchestration_run.review_notes = review_notes
        orchestration_run.reviewed_by = current_user.id
        orchestration_run.reviewed_at = datetime.utcnow()
        orchestration_run.status = 'executing'
        orchestration_run.current_stage = 'executing'
        db.session.commit()

        # Start Celery task for execution phase (Stages 4-5)
        from app.tasks.orchestration import run_execution_phase_task
        task = run_execution_phase_task.delay(
            str(run_uuid),
            modified_strategy=modified_strategy,
            review_notes=review_notes,
            reviewer_id=current_user.id
        )

        # Store task ID for monitoring
        orchestration_run.celery_task_id = task.id
        db.session.commit()

        current_app.logger.info(f"Started Celery task {task.id} for execution phase of run {run_id}")

        return jsonify({
            'success': True,
            'celery_task_id': task.id,
            'message': 'Strategy approved - processing documents'
        })

    except Exception as e:
        current_app.logger.error(f"Error approving strategy: {str(e)}")
        return jsonify({'error': str(e)}), 500


def get_stage_message(stage: str, status: str) -> str:
    """Generate user-friendly stage messages for SSE updates."""
    messages = {
        'analyzing': 'Analyzing experiment goals and document collection...',
        'recommending': 'Recommending optimal processing strategy...',
        'reviewing': 'Strategy ready for review',
        'strategy_ready': 'Strategy ready for review',
        'executing': 'Processing documents with selected tools...',
        'synthesizing': 'Generating cross-document insights...',
        'completed': 'Orchestration completed successfully',
        'failed': 'Orchestration failed'
    }

    return messages.get(stage, f'Current stage: {stage}')
