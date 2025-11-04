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
async def analyze_document(document_id):
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
        focus_term = document.experiments.first().term.lemma

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
            user_preferences=request.get_json() or {}
        )

        # Execute orchestration graph
        graph = get_orchestration_graph()
        final_state = await graph.ainvoke(initial_state)

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
async def analyze_experiment_documents(experiment_id):
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
    request_data = request.get_json() or {}
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
            final_state = await graph.ainvoke(initial_state)

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
