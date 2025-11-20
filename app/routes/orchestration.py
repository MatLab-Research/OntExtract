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
import asyncio
import uuid
import json
import time
import markdown

from app.orchestration.experiment_state import create_initial_experiment_state
from app.orchestration.experiment_graph import get_experiment_graph
from app.orchestration.experiment_nodes import (
    execute_strategy_node,
    synthesize_experiment_node
)


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

        # Create initial state
        initial_state = create_initial_experiment_state(
            experiment_id=str(experiment_id),
            run_id=str(run_id),
            documents=documents,
            focus_term=focus_term,
            user_preferences={
                'review_choices': review_choices
            }
        )

        # Capture app instance for background thread
        app = current_app._get_current_object()

        # Execute graph in background thread for Stages 1-2 only
        # (analyze_experiment and recommend_strategy)
        def run_recommendation_phase():
            try:
                # Create new app context for background thread
                with app.app_context():
                    # Get fresh db session in this thread
                    from app import db
                    orch_run = db.session.get(ExperimentOrchestrationRun, run_id)

                    # Update status to analyzing
                    orch_run.status = 'analyzing'
                    orch_run.current_stage = 'analyzing'
                    db.session.commit()

                    # Run the graph (only Stages 1-2) - synchronously via asyncio.run
                    graph = get_experiment_graph()

                    async def execute_graph():
                        return await graph.ainvoke(initial_state)

                    final_state = asyncio.run(execute_graph())

                    # Update database with Stage 1-2 results
                    orch_run.experiment_goal = final_state.get('experiment_goal', '')
                    orch_run.term_context = final_state.get('term_context')
                    orch_run.recommended_strategy = final_state.get('recommended_strategy', {})
                    orch_run.strategy_reasoning = final_state.get('strategy_reasoning', '')
                    orch_run.confidence = final_state.get('confidence', 0.0)
                    orch_run.status = 'strategy_ready'
                    orch_run.current_stage = 'reviewing'
                    db.session.commit()

            except Exception as e:
                with app.app_context():
                    from app import db
                    orch_run = db.session.get(ExperimentOrchestrationRun, run_id)
                    app.logger.error(f"Orchestration error (run {run_id}): {str(e)}")
                    orch_run.status = 'failed'
                    orch_run.error_message = str(e)
                    db.session.commit()

        # Start in background thread
        # Note: In production, use Celery or similar for proper task management
        import threading
        thread = threading.Thread(target=run_recommendation_phase)
        thread.daemon = True
        thread.start()

        return jsonify({
            'success': True,
            'run_id': str(run_id),
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
                    if status == 'strategy_ready':
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

        # Prepare state for Stages 4-5
        # Reconstruct state from database
        experiment = orchestration_run.experiment
        documents = []
        for doc in experiment.documents.all():
            documents.append({
                'id': str(doc.id),
                'title': doc.title,
                'content': doc.content or '',
                'metadata': {}
            })

        focus_term = experiment.term.term_text if experiment.term else None

        state = {
            'experiment_id': str(experiment.id),
            'run_id': str(run_id),
            'documents': documents,
            'focus_term': focus_term,
            'user_preferences': {'review_choices': True},

            # Stage 1-2 results from database
            'experiment_goal': orchestration_run.experiment_goal,
            'term_context': orchestration_run.term_context,
            'recommended_strategy': orchestration_run.recommended_strategy,
            'strategy_reasoning': orchestration_run.strategy_reasoning,
            'confidence': orchestration_run.confidence,

            # Stage 3 (just approved)
            'strategy_approved': True,
            'modified_strategy': modified_strategy,
            'review_notes': review_notes,

            # Initialize Stage 4-5 fields
            'processing_results': {},
            'execution_trace': [],
            'cross_document_insights': '',
            'term_evolution_analysis': None,
            'comparative_summary': '',
            'current_stage': 'executing',
            'error_message': None
        }

        # Capture app instance for background thread
        app = current_app._get_current_object()

        # Execute Stages 4-5 in background thread
        def run_execution_phase():
            try:
                # Create new app context for background thread
                with app.app_context():
                    from app import db
                    orch_run = db.session.get(ExperimentOrchestrationRun, run_uuid)

                    # Execute graph stages synchronously via asyncio.run
                    async def execute_stages():
                        # Stage 4: Execute strategy
                        result_state = await execute_strategy_node(state)
                        state.update(result_state)

                        # Stage 5: Synthesize insights
                        final_state = await synthesize_experiment_node(state)
                        state.update(final_state)

                        return state

                    final_state = asyncio.run(execute_stages())

                    # Update database
                    orch_run.processing_results = final_state['processing_results']
                    orch_run.execution_trace = final_state['execution_trace']
                    orch_run.cross_document_insights = final_state['cross_document_insights']
                    orch_run.term_evolution_analysis = final_state.get('term_evolution_analysis')
                    orch_run.comparative_summary = final_state['comparative_summary']
                    orch_run.status = 'completed'
                    orch_run.current_stage = 'completed'
                    orch_run.completed_at = datetime.utcnow()
                    db.session.commit()

            except Exception as e:
                with app.app_context():
                    from app import db
                    orch_run = db.session.get(ExperimentOrchestrationRun, run_uuid)
                    app.logger.error(f"Execution error (run {run_id}): {str(e)}")
                    orch_run.status = 'failed'
                    orch_run.error_message = str(e)
                    db.session.commit()

        # Start in background thread
        import threading
        thread = threading.Thread(target=run_execution_phase)
        thread.daemon = True
        thread.start()

        return jsonify({
            'success': True,
            'message': 'Strategy approved - processing documents'
        })

    except Exception as e:
        current_app.logger.error(f"Error approving strategy: {str(e)}")
        return jsonify({'error': str(e)}), 500


@orchestration_bp.route('/experiment/<run_id>/results')
def view_results(run_id: str):
    """
    Display final orchestration results.

    Shows:
    - Experiment summary
    - Cross-document insights (Stage 5)
    - Term evolution analysis (if focus term)
    - Per-document processing results
    - Download options
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
        if orchestration_run.status != 'completed':
            return f"Results not ready (status: {orchestration_run.status})", 400

        # Get experiment
        experiment = orchestration_run.experiment

        # Convert markdown to HTML for insights
        insights_html = None
        if orchestration_run.cross_document_insights:
            insights_html = markdown.markdown(
                orchestration_run.cross_document_insights,
                extensions=['fenced_code', 'tables', 'nl2br']
            )

        evolution_html = None
        if orchestration_run.term_evolution_analysis:
            evolution_html = markdown.markdown(
                orchestration_run.term_evolution_analysis,
                extensions=['fenced_code', 'tables', 'nl2br']
            )

        return render_template(
            'orchestration/experiment_results.html',
            orchestration_run=orchestration_run,
            experiment=experiment,
            insights_html=insights_html,
            evolution_html=evolution_html
        )

    except Exception as e:
        current_app.logger.error(f"Error loading results page: {str(e)}")
        return str(e), 500


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
