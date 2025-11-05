"""
LangGraph Orchestration Routes

API endpoints for LLM-powered document orchestration.
Integrates with experiment framework for multi-document comparison.
"""

from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import current_user
from app.utils.auth_decorators import require_login_for_write, api_require_login_for_write
import asyncio
import json
from datetime import datetime

from app import db
from app.models.document import Document
from app.models.experiment import Experiment
from app.models.experiment_document import ExperimentDocument
from app.orchestration.state import create_initial_state
from app.orchestration.graph import get_orchestration_graph

orchestration_bp = Blueprint('orchestration', __name__, url_prefix='/orchestration')


@orchestration_bp.route('/analyze/<int:document_id>', methods=['POST'])
@api_require_login_for_write
def analyze_document(document_id):
    """
    Run LLM orchestration on a single document.

    Claude analyzes the document and recommends processing tools.

    POST /orchestration/analyze/<document_id>

    Returns:
        {
            "success": true,
            "document_id": 123,
            "orchestration": {
                "recommended_tools": ["segment_paragraph", "extract_entities_spacy"],
                "confidence": 0.85,
                "reasoning": "Document has clear structure..."
            },
            "results": {
                "segmentation": {...},
                "entities": {...}
            },
            "synthesis": "Key findings...",
            "provenance": [...]
        }
    """

    # Get document
    document = Document.query.get_or_404(document_id)

    # Get focus term if document is part of an experiment with a term
    focus_term = None
    if document.experiments.first() and document.experiments.first().term:
        focus_term = document.experiments.first().term.term_text

    try:
        # Create initial state
        initial_state = create_initial_state(
            document_id=document.id,
            document_text=document.content,
            document_metadata={
                "title": document.title,
                "format": getattr(document, 'file_format', 'unknown'),
                "source": getattr(document, 'source', 'database'),
                "focus_term": focus_term  # Optional: term for semantic evolution tracking
            },
            user_preferences=request.get_json(silent=True) or {}
        )

        # Execute orchestration graph
        graph = get_orchestration_graph()
        final_state = asyncio.run(graph.ainvoke(initial_state))

        # Format response
        response = {
            "success": True,
            "document_id": document.id,
            "document_title": document.title,
            "orchestration": {
                "recommended_tools": final_state.get('recommended_tools', []),
                "confidence": final_state.get('confidence_score', 0.0),
                "reasoning": final_state.get('orchestration_reasoning', ''),
                "characteristics": final_state.get('document_characteristics', {})
            },
            "results": {
                "segmentation": final_state.get('segmentation_results'),
                "entities": final_state.get('entity_results'),
                "temporal": final_state.get('temporal_results'),
                "embeddings": final_state.get('embedding_results')
            },
            "synthesis": final_state.get('synthesis'),
            "insights": final_state.get('insights', []),
            "suggested_next_steps": final_state.get('suggested_next_steps', []),
            "provenance": final_state.get('execution_trace', []),
            "errors": final_state.get('errors'),
            "warnings": final_state.get('warnings')
        }

        return jsonify(response)

    except Exception as e:
        current_app.logger.error(f"Orchestration error for document {document_id}: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "document_id": document_id
        }), 500


@orchestration_bp.route('/experiment/<int:experiment_id>/analyze', methods=['POST'])
@api_require_login_for_write
def analyze_experiment_documents(experiment_id):
    """
    Run LLM orchestration on all documents in an experiment.

    Enables comparison of how Claude orchestrates different documents.

    POST /orchestration/experiment/<experiment_id>/analyze

    Body (optional):
        {
            "document_ids": [1, 2, 3]  // Subset of documents, or omit for all
        }

    Returns:
        {
            "success": true,
            "experiment_id": 456,
            "documents_analyzed": 5,
            "results": [
                {
                    "document_id": 1,
                    "orchestration": {...},
                    "results": {...}
                },
                ...
            ],
            "comparison": {
                "tool_frequency": {"segment_paragraph": 5, "extract_entities": 3},
                "avg_confidence": 0.87,
                "tool_combinations": [...]
            }
        }
    """

    # Get experiment
    experiment = Experiment.query.get_or_404(experiment_id)

    # Get document IDs (from request or all in experiment)
    request_data = request.get_json(silent=True) or {}
    requested_doc_ids = request_data.get('document_ids')

    if requested_doc_ids:
        # Get specified documents
        documents = Document.query.filter(
            Document.id.in_(requested_doc_ids)
        ).all()
    else:
        # Get all documents in experiment
        documents = experiment.documents.all()

    if not documents:
        return jsonify({
            "success": False,
            "error": "No documents found for this experiment"
        }), 400

    try:
        # Analyze each document
        results = []
        tool_frequency = {}
        total_confidence = 0.0
        tool_combinations = []

        for document in documents:
            # Create state
            initial_state = create_initial_state(
                document_id=document.id,
                document_text=document.content,
                document_metadata={
                    "title": document.title,
                    "format": getattr(document, 'file_format', 'unknown'),
                    "experiment_id": experiment_id
                }
            )

            # Execute orchestration
            graph = get_orchestration_graph()
            final_state = asyncio.run(graph.ainvoke(initial_state))

            # Collect results
            recommended_tools = final_state.get('recommended_tools', [])
            confidence = final_state.get('confidence_score', 0.0)

            # Track tool frequency
            for tool in recommended_tools:
                tool_frequency[tool] = tool_frequency.get(tool, 0) + 1

            # Track tool combinations
            tool_combo = tuple(sorted(recommended_tools))
            tool_combinations.append(tool_combo)

            # Track confidence
            total_confidence += confidence

            # Store result
            results.append({
                "document_id": document.id,
                "document_title": document.title,
                "orchestration": {
                    "recommended_tools": recommended_tools,
                    "confidence": confidence,
                    "reasoning": final_state.get('orchestration_reasoning', '')
                },
                "results": {
                    "segmentation": final_state.get('segmentation_results'),
                    "entities": final_state.get('entity_results')
                },
                "synthesis": final_state.get('synthesis'),
                "insights": final_state.get('insights', [])
            })

        # Calculate comparison metrics
        from collections import Counter
        combo_frequency = Counter(tool_combinations)

        comparison = {
            "tool_frequency": tool_frequency,
            "avg_confidence": total_confidence / len(documents) if documents else 0.0,
            "unique_tool_combinations": len(combo_frequency),
            "most_common_combination": list(combo_frequency.most_common(1)[0][0]) if combo_frequency else [],
            "documents_with_same_tools": combo_frequency.most_common(1)[0][1] if combo_frequency else 0
        }

        return jsonify({
            "success": True,
            "experiment_id": experiment_id,
            "experiment_name": experiment.name,
            "documents_analyzed": len(documents),
            "results": results,
            "comparison": comparison
        })

    except Exception as e:
        current_app.logger.error(f"Experiment orchestration error: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "experiment_id": experiment_id
        }), 500


@orchestration_bp.route('/document/<int:document_id>')
@require_login_for_write
def view_document_orchestration(document_id):
    """
    UI view: Display orchestration results for a single document.
    """

    document = Document.query.get_or_404(document_id)

    return render_template(
        'orchestration/document_view.html',
        document=document
    )


@orchestration_bp.route('/experiment/<int:experiment_id>')
@require_login_for_write
def view_experiment_orchestration(experiment_id):
    """
    UI view: Compare orchestration results across documents in an experiment.
    """

    experiment = Experiment.query.get_or_404(experiment_id)
    documents = experiment.documents.all()

    return render_template(
        'orchestration/experiment_comparison.html',
        experiment=experiment,
        documents=documents
    )


# ===== EXPERIMENT-LEVEL ORCHESTRATION ROUTES =====

# Import additional dependencies
from app.models.experiment_orchestration_run import ExperimentOrchestrationRun
from app.models.term import Term
from app.orchestration.experiment_state import create_initial_experiment_state
from app.orchestration.experiment_graph import get_experiment_graph
import uuid
import threading
from flask import Response, stream_with_context
import time
import queue

# Store for SSE progress updates (in-memory, could use Redis in production)
progress_queues = {}


@orchestration_bp.route('/analyze-experiment/<int:experiment_id>', methods=['POST'])
@api_require_login_for_write
def analyze_experiment_unified(experiment_id):
    """
    Run experiment-level orchestration (NEW).

    LLM analyzes ALL documents together and recommends a coherent strategy.

    POST /orchestration/analyze-experiment/<experiment_id>

    Body:
        {
            "review_choices": true/false  // Optional human review
        }

    Returns:
        {
            "success": true,
            "run_id": "uuid",
            "status": "analyzing" or "reviewing" or "completed",
            "experiment_id": 123
        }
    """

    # Get experiment
    experiment = Experiment.query.get_or_404(experiment_id)

    # Check user has access
    if experiment.user_id != current_user.id:
        return jsonify({"success": False, "error": "Access denied"}), 403

    # Get documents
    documents = experiment.documents.all()
    if not documents:
        return jsonify({"success": False, "error": "Experiment has no documents"}), 400

    # Get focus term if exists
    focus_term = None
    if experiment.term:
        focus_term = experiment.term.term_text

    try:
        # Create orchestration run record
        run = ExperimentOrchestrationRun(
            experiment_id=experiment_id,
            user_id=current_user.id,
            status='analyzing',
            current_stage='analyzing',
            term_context=focus_term
        )
        db.session.add(run)
        db.session.commit()

        run_id = str(run.id)

        # Create progress queue for SSE
        progress_queues[run_id] = queue.Queue()

        # Get user preferences
        request_data = request.get_json(silent=True) or {}
        review_choices = request_data.get('review_choices', False)

        # Prepare documents for orchestration
        doc_list = [
            {
                "id": str(doc.id),
                "title": doc.title,
                "content": doc.content,
                "metadata": {
                    "format": getattr(doc, 'file_format', 'unknown'),
                    "source": getattr(doc, 'source', 'database')
                }
            }
            for doc in documents
        ]

        # Create initial state
        initial_state = create_initial_experiment_state(
            experiment_id=str(experiment_id),
            run_id=run_id,
            documents=doc_list,
            focus_term=focus_term,
            user_preferences={"review_choices": review_choices}
        )

        # Run orchestration in background thread
        def run_orchestration():
            try:
                # Execute graph
                graph = get_experiment_graph()

                # Update progress
                progress_queues[run_id].put({"stage": "analyzing", "progress": 10})

                final_state = asyncio.run(graph.ainvoke(initial_state))

                # Check if stopped at review
                if final_state['current_stage'] == 'waiting_for_review':
                    # Save state to database
                    run.status = 'reviewing'
                    run.current_stage = 'reviewing'
                    run.experiment_goal = final_state.get('experiment_goal')
                    run.recommended_strategy = final_state.get('recommended_strategy')
                    run.strategy_reasoning = final_state.get('strategy_reasoning')
                    run.confidence = final_state.get('confidence')
                    db.session.commit()

                    progress_queues[run_id].put({"stage": "reviewing", "progress": 30, "status": "waiting_for_review"})

                else:
                    # Completed without review
                    run.status = 'completed'
                    run.current_stage = 'completed'
                    run.completed_at = datetime.utcnow()

                    # Save all results
                    run.experiment_goal = final_state.get('experiment_goal')
                    run.recommended_strategy = final_state.get('recommended_strategy')
                    run.strategy_reasoning = final_state.get('strategy_reasoning')
                    run.confidence = final_state.get('confidence')
                    run.strategy_approved = final_state.get('strategy_approved')
                    run.processing_results = final_state.get('processing_results')
                    run.execution_trace = final_state.get('execution_trace')
                    run.cross_document_insights = final_state.get('cross_document_insights')
                    run.term_evolution_analysis = final_state.get('term_evolution_analysis')
                    run.comparative_summary = final_state.get('comparative_summary')

                    db.session.commit()

                    progress_queues[run_id].put({"stage": "completed", "progress": 100, "status": "completed"})

            except Exception as e:
                current_app.logger.error(f"Orchestration error for run {run_id}: {e}")
                run.status = 'failed'
                run.error_message = str(e)
                db.session.commit()

                progress_queues[run_id].put({"stage": "failed", "progress": 0, "error": str(e)})

        # Start background thread
        thread = threading.Thread(target=run_orchestration)
        thread.daemon = True
        thread.start()

        return jsonify({
            "success": True,
            "run_id": run_id,
            "status": "analyzing",
            "experiment_id": experiment_id
        })

    except Exception as e:
        current_app.logger.error(f"Failed to start orchestration: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@orchestration_bp.route('/experiment/<run_id>/status')
@require_login_for_write
def experiment_status_sse(run_id):
    """
    SSE endpoint for real-time orchestration progress.

    GET /orchestration/experiment/<run_id>/status

    Streams:
        data: {"stage": "analyzing", "progress": 10}
        data: {"stage": "recommending", "progress": 20}
        data: {"stage": "completed", "progress": 100, "status": "completed"}
    """

    def generate():
        q = progress_queues.get(run_id)
        if not q:
            yield f"data: {json.dumps({'error': 'Run not found'})}\n\n"
            return

        while True:
            try:
                # Wait for progress update with timeout
                update = q.get(timeout=30)
                yield f"data: {json.dumps(update)}\n\n"

                # Stop streaming if completed or failed
                if update.get('status') in ['completed', 'failed', 'waiting_for_review']:
                    break

            except queue.Empty:
                # Send heartbeat
                yield f"data: {json.dumps({'heartbeat': True})}\n\n"

    return Response(stream_with_context(generate()), mimetype='text/event-stream')


@orchestration_bp.route('/experiment/<run_id>/review')
@require_login_for_write
def experiment_review(run_id):
    """
    UI view: Review and modify recommended strategy.

    GET /orchestration/experiment/<run_id>/review

    Displays:
    - Experiment goal
    - Recommended strategy per document
    - LLM reasoning and confidence
    - Allow modifications
    - Approve/Cancel buttons
    """

    run = ExperimentOrchestrationRun.query.get_or_404(run_id)

    # Check access
    if run.user_id != current_user.id:
        return "Access denied", 403

    # Check status
    if run.status != 'reviewing':
        return f"Run is not in review state (status: {run.status})", 400

    experiment = run.experiment
    documents = experiment.documents.all()

    return render_template(
        'orchestration/experiment_review.html',
        run=run,
        experiment=experiment,
        documents=documents
    )


@orchestration_bp.route('/experiment/<run_id>/approve', methods=['POST'])
@api_require_login_for_write
def approve_strategy(run_id):
    """
    Approve (and optionally modify) the recommended strategy.

    POST /orchestration/experiment/<run_id>/approve

    Body:
        {
            "approved": true,
            "modified_strategy": {...},  // Optional
            "review_notes": "..."  // Optional
        }

    Returns:
        {
            "success": true,
            "run_id": "uuid",
            "status": "executing"
        }
    """

    run = ExperimentOrchestrationRun.query.get_or_404(run_id)

    # Check access
    if run.user_id != current_user.id:
        return jsonify({"success": False, "error": "Access denied"}), 403

    # Check status
    if run.status != 'reviewing':
        return jsonify({"success": False, "error": f"Run is not in review state (status: {run.status})"}), 400

    try:
        request_data = request.get_json()
        approved = request_data.get('approved', False)

        if not approved:
            # User rejected strategy
            run.status = 'cancelled'
            run.strategy_approved = False
            run.review_notes = request_data.get('review_notes')
            run.reviewed_by = current_user.id
            run.reviewed_at = datetime.utcnow()
            db.session.commit()

            return jsonify({"success": True, "run_id": run_id, "status": "cancelled"})

        # User approved - save modifications if any
        run.strategy_approved = True
        run.modified_strategy = request_data.get('modified_strategy')
        run.review_notes = request_data.get('review_notes')
        run.reviewed_by = current_user.id
        run.reviewed_at = datetime.utcnow()
        run.status = 'executing'
        run.current_stage = 'executing'
        db.session.commit()

        # Resume orchestration from execute_strategy node
        # TODO: Implement resume logic
        # For now, return success
        return jsonify({"success": True, "run_id": run_id, "status": "executing"})

    except Exception as e:
        current_app.logger.error(f"Approval error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@orchestration_bp.route('/experiment/<run_id>/results')
@require_login_for_write
def experiment_results(run_id):
    """
    UI view: Display final orchestration results.

    GET /orchestration/experiment/<run_id>/results

    Shows:
    - Cross-document insights
    - Term evolution analysis
    - Per-document results
    """

    run = ExperimentOrchestrationRun.query.get_or_404(run_id)

    # Check access
    if run.user_id != current_user.id:
        return "Access denied", 403

    # Check completed
    if run.status != 'completed':
        return f"Run not completed yet (status: {run.status})", 400

    experiment = run.experiment
    documents = experiment.documents.all()

    return render_template(
        'orchestration/experiment_results.html',
        run=run,
        experiment=experiment,
        documents=documents
    )
