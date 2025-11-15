"""
Experiments LLM Orchestration Routes

This module handles human-in-the-loop LLM orchestration for experiments.

Routes:
- GET  /experiments/<id>/orchestrated_analysis         - Orchestrated analysis UI
- POST /experiments/<id>/create_orchestration_decision - Create orchestration decision
- POST /experiments/<id>/run_orchestrated_analysis     - Run orchestrated analysis
"""

from flask import render_template, request, jsonify
from flask_login import current_user
from app.utils.auth_decorators import api_require_login_for_write
from app import db
from app.models import Experiment
from datetime import datetime
import json

from . import experiments_bp


@experiments_bp.route('/<int:experiment_id>/orchestrated_analysis')
@api_require_login_for_write
def orchestrated_analysis(experiment_id):
    """Human-in-the-loop orchestrated analysis interface"""
    experiment = Experiment.query.filter_by(id=experiment_id).first_or_404()

    # Get orchestration decisions for this experiment
    from app.models.orchestration_logs import OrchestrationDecision
    from app.models.orchestration_feedback import OrchestrationFeedback, LearningPattern

    decisions = OrchestrationDecision.query.filter_by(
        experiment_id=experiment.id
    ).order_by(OrchestrationDecision.created_at.desc()).all()

    # Get learning patterns
    patterns = LearningPattern.query.filter_by(
        pattern_status='active'
    ).order_by(LearningPattern.confidence.desc()).limit(5).all()

    # Get experiment configuration
    config = json.loads(experiment.configuration) if experiment.configuration else {}
    terms = config.get('target_terms', [])

    return render_template('experiments/orchestrated_analysis.html',
                         experiment=experiment,
                         decisions=decisions,
                         patterns=patterns,
                         terms=terms)


@experiments_bp.route('/<int:experiment_id>/create_orchestration_decision', methods=['POST'])
@api_require_login_for_write
def create_orchestration_decision(experiment_id):
    """Create a new orchestration decision for human feedback"""
    try:
        experiment = Experiment.query.filter_by(id=experiment_id).first_or_404()
        data = request.get_json()

        term_text = data.get('term_text', '')
        if not term_text:
            return jsonify({'error': 'Term text is required'}), 400

        # Get document characteristics
        doc_characteristics = {
            'document_count': experiment.get_document_count(),
            'total_words': experiment.get_total_word_count(),
            'experiment_type': experiment.experiment_type
        }

        # Create input metadata
        config = json.loads(experiment.configuration) if experiment.configuration else {}
        input_metadata = {
            'experiment_id': experiment.id,
            'experiment_type': experiment.experiment_type,
            'document_count': experiment.get_document_count(),
            'total_words': experiment.get_total_word_count(),
            'time_periods': config.get('time_periods', []),
            'domains': config.get('domains', [])
        }

        # Simulate LLM orchestration decision (in production, this would call actual LLM service)
        selected_tools = ['spacy', 'embeddings']
        embedding_model = 'bert-base-uncased'
        decision_confidence = 0.85

        # Apply learning patterns for more intelligent selection
        from app.models.orchestration_feedback import LearningPattern
        active_patterns = LearningPattern.query.filter_by(pattern_status='active').all()

        reasoning_parts = [f"Selected tools for term '{term_text}' based on:"]
        for pattern in active_patterns[:2]:  # Apply top 2 patterns
            if pattern.pattern_type == 'preference':
                pattern_tools = pattern.recommendations.get('tools', [])
                selected_tools.extend([t for t in pattern_tools if t not in selected_tools])
                reasoning_parts.append(f"- {pattern.pattern_name}: {pattern.recommendations.get('reasoning', 'Applied learned pattern')}")

                # Apply embedding model recommendations
                pattern_model = pattern.recommendations.get('embedding_model')
                if pattern_model:
                    embedding_model = pattern_model

        reasoning = '\\n'.join(reasoning_parts)

        # Create orchestration decision
        from app.models.orchestration_logs import OrchestrationDecision

        decision = OrchestrationDecision(
            experiment_id=experiment.id,
            term_text=term_text,
            selected_tools=selected_tools,
            embedding_model=embedding_model,
            decision_confidence=decision_confidence,
            orchestrator_provider='claude',
            orchestrator_model='claude-3-sonnet',
            orchestrator_prompt=f"Analyze term '{term_text}' and recommend optimal NLP processing approach",
            orchestrator_response=f"Recommended: {', '.join(selected_tools)} with {embedding_model}",
            orchestrator_response_time_ms=1200,
            processing_strategy='sequential',
            reasoning=reasoning,
            input_metadata=input_metadata,
            document_characteristics=doc_characteristics,
            created_by=current_user.id
        )

        db.session.add(decision)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Orchestration decision created successfully',
            'decision_id': str(decision.id),
            'selected_tools': selected_tools,
            'embedding_model': embedding_model,
            'confidence': decision_confidence,
            'reasoning': reasoning
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@experiments_bp.route('/<int:experiment_id>/run_orchestrated_analysis', methods=['POST'])
@api_require_login_for_write
def run_orchestrated_analysis(experiment_id):
    """Run analysis with LLM orchestration decisions and real-time feedback"""
    try:
        experiment = Experiment.query.filter_by(id=experiment_id).first_or_404()
        data = request.get_json()

        # Get analysis parameters
        terms = data.get('terms', [])
        if not terms:
            return jsonify({'error': 'At least one term is required'}), 400

        # Create orchestration decisions for each term
        from app.models.orchestration_logs import OrchestrationDecision
        from app.services.adaptive_orchestration_service import AdaptiveOrchestrationService

        orchestration_service = AdaptiveOrchestrationService()
        analysis_results = []

        for term in terms:
            # Create or get existing orchestration decision
            existing_decision = OrchestrationDecision.query.filter_by(
                experiment_id=experiment.id,
                term_text=term
            ).first()

            if not existing_decision:
                # Create new decision using adaptive service
                decision_context = {
                    'experiment_id': experiment.id,
                    'term_text': term,
                    'experiment_type': experiment.experiment_type,
                    'document_count': experiment.get_document_count(),
                    'user_id': current_user.id
                }

                decision = orchestration_service.create_adaptive_decision(decision_context)
            else:
                decision = existing_decision

            # Simulate analysis execution with the orchestrated tools
            analysis_result = {
                'term': term,
                'decision_id': str(decision.id),
                'tools_used': decision.selected_tools,
                'embedding_model': decision.embedding_model,
                'confidence': float(decision.decision_confidence),
                'processing_time': '2.3s',
                'semantic_drift_detected': True,
                'drift_magnitude': 0.32,
                'periods_analyzed': 4,
                'insights': [
                    f"Term '{term}' shows moderate semantic drift over time",
                    f"Most stable usage in period 2010-2015",
                    f"Significant shift detected in recent period"
                ]
            }

            analysis_results.append(analysis_result)

        # Mark experiment as running
        experiment.status = 'running'
        experiment.started_at = datetime.utcnow()
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Orchestrated analysis initiated for {len(terms)} terms',
            'results': analysis_results,
            'total_decisions': len(analysis_results)
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
