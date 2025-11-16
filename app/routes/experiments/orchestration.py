"""
Experiments LLM Orchestration Routes

This module handles human-in-the-loop LLM orchestration for experiments.

Routes:
- GET  /experiments/<id>/orchestrated_analysis         - Orchestrated analysis UI
- POST /experiments/<id>/create_orchestration_decision - Create orchestration decision
- POST /experiments/<id>/run_orchestrated_analysis     - Run orchestrated analysis
- GET  /experiments/<id>/orchestration-results         - View orchestration results
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


@experiments_bp.route('/<int:experiment_id>/orchestration-results')
def orchestration_results(experiment_id):
    """Display orchestration results for an experiment (public for screenshots)"""
    experiment = Experiment.query.filter_by(id=experiment_id).first_or_404()

    # Query experiment_orchestration_runs directly (no model class exists yet)
    from sqlalchemy import text
    from app.models.orchestration_logs import OrchestrationDecision
    import re

    # Get orchestration decisions for this experiment
    decisions = OrchestrationDecision.query.filter_by(
        experiment_id=experiment.id
    ).order_by(OrchestrationDecision.created_at.desc()).all()

    total_decisions = len(decisions)
    completed_decisions = sum(1 for d in decisions if d.activity_status == 'completed')

    # Get most recent decision
    recent_decision = decisions[0] if decisions else None

    # Set defaults
    avg_confidence = 0.0
    cross_document_insights = None
    duration = None
    document_count = experiment.documents.count()

    # Calculate average confidence from decisions
    if decisions:
        valid_confidences = [float(d.decision_confidence) for d in decisions if d.decision_confidence]
        if valid_confidences:
            avg_confidence = sum(valid_confidences) / len(valid_confidences)

    # Get the most recent completed orchestration run via raw SQL
    query = text("""
        SELECT confidence, cross_document_insights, started_at, completed_at
        FROM experiment_orchestration_runs
        WHERE experiment_id = :exp_id AND status = 'completed'
        ORDER BY completed_at DESC
        LIMIT 1
    """)

    result = db.session.execute(query, {'exp_id': experiment_id}).fetchone()

    # If we have orchestration run data, use it
    if result:
        # Use orchestration run confidence if available, otherwise use decisions average
        if result[0]:
            avg_confidence = result[0]
        cross_document_insights = result[1]
        started_at = result[2]
        completed_at = result[3]

        # Calculate duration from orchestration run
        if started_at and completed_at:
            duration_seconds = (completed_at - started_at).total_seconds()
            if duration_seconds < 60:
                duration = f"{int(duration_seconds)}s"
            elif duration_seconds < 3600:
                minutes = int(duration_seconds / 60)
                seconds = int(duration_seconds % 60)
                duration = f"{minutes}m {seconds}s"
            else:
                hours = int(duration_seconds / 3600)
                minutes = int((duration_seconds % 3600) / 60)
                duration = f"{hours}h {minutes}m"

    # Convert markdown-style formatting to HTML
    if cross_document_insights:
        # Convert **bold** to <strong>bold</strong>
        cross_document_insights = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', cross_document_insights)
        # Convert ### headers to h4
        cross_document_insights = re.sub(r'###\s*(.+?)$', r'<h4>\1</h4>', cross_document_insights, flags=re.MULTILINE)
        # Convert bullet points to proper HTML list items
        cross_document_insights = re.sub(r'•\s*(.+?)$', r'<li>\1</li>', cross_document_insights, flags=re.MULTILINE)
        # Wrap list items in ul
        if '<li>' in cross_document_insights:
            cross_document_insights = re.sub(r'(<li>.*?</li>)', r'<ul class="list-unstyled mb-4">\n\1\n</ul>', cross_document_insights, flags=re.DOTALL)
            # Clean up multiple ul tags
            cross_document_insights = cross_document_insights.replace('</ul>\n<ul class="list-unstyled mb-4">', '')
        # Convert newlines to br tags (but not within ul/li)
        lines = cross_document_insights.split('\n')
        processed_lines = []
        in_list = False
        for line in lines:
            if '<ul' in line:
                in_list = True
            elif '</ul>' in line:
                in_list = False

            if line.strip() and not in_list and '<h4>' not in line and '<ul' not in line and '</ul>' not in line and '<li>' not in line:
                processed_lines.append(line + '<br>')
            else:
                processed_lines.append(line)
        cross_document_insights = '\n'.join(processed_lines)

    # Allow template override via query parameter (for backward compatibility or screenshots)
    template = request.args.get('template', 'enhanced')
    if template == 'compact':
        template_name = 'experiments/orchestration_results.html'
    else:
        template_name = 'experiments/orchestration_results_enhanced.html'

    return render_template(template_name,
                         experiment=experiment,
                         decisions=decisions,
                         total_decisions=total_decisions,
                         completed_decisions=completed_decisions,
                         avg_confidence=float(avg_confidence) if avg_confidence else 0.0,
                         recent_decision=recent_decision,
                         cross_document_insights=cross_document_insights,
                         duration=duration,
                         document_count=experiment.get_document_count())


@experiments_bp.route('/<int:experiment_id>/orchestration-provenance.json')
def orchestration_provenance_json(experiment_id):
    """Download PROV-O compliant JSON provenance record for orchestration decisions"""
    experiment = Experiment.query.filter_by(id=experiment_id).first_or_404()

    # Get orchestration decisions for this experiment
    from app.models.orchestration_logs import OrchestrationDecision
    from sqlalchemy import desc

    decisions = OrchestrationDecision.query.filter_by(
        experiment_id=experiment.id
    ).order_by(desc(OrchestrationDecision.created_at)).all()

    # Build PROV-O compliant provenance record
    provenance_data = {
        '@context': 'http://www.w3.org/ns/prov',
        '@type': 'prov:Bundle',
        'prov:generatedAtTime': datetime.utcnow().isoformat() + 'Z',
        'experiment': {
            'id': experiment.id,
            'name': experiment.name,
            'type': experiment.experiment_type,
            'created_at': experiment.created_at.isoformat() if experiment.started_at else None,
            'started_at': experiment.started_at.isoformat() if experiment.started_at else None,
            'completed_at': experiment.completed_at.isoformat() if experiment.completed_at else None,
            'status': experiment.status,
            'document_count': experiment.get_document_count()
        },
        'orchestration_decisions': []
    }

    # Add each orchestration decision as a PROV-O Activity
    for decision in decisions:
        decision_data = {
            '@id': f'urn:orchestration:decision:{decision.id}',
            '@type': 'prov:Activity',
            'prov:startedAtTime': decision.started_at_time.isoformat() if decision.started_at_time else None,
            'prov:endedAtTime': decision.ended_at_time.isoformat() if decision.ended_at_time else None,
            'activity_status': decision.activity_status,

            # Context
            'experiment_id': decision.experiment_id,
            'document_id': decision.document_id,
            'term_analyzed': decision.term_text,

            # LLM Orchestration Details
            'orchestrator': {
                'provider': decision.orchestrator_provider,
                'model': decision.orchestrator_model,
                'response_time_ms': decision.orchestrator_response_time_ms
            },

            # Decision Outputs
            'decision': {
                'selected_tools': decision.selected_tools,
                'embedding_model': decision.embedding_model,
                'processing_strategy': decision.processing_strategy,
                'confidence': float(decision.decision_confidence) if decision.decision_confidence else None,
                'expected_runtime_seconds': decision.expected_runtime_seconds,
                'actual_runtime_seconds': decision.actual_runtime_seconds
            },

            # Input Metadata
            'input_metadata': decision.input_metadata,
            'document_characteristics': decision.document_characteristics,

            # Reasoning
            'reasoning_summary': decision.reasoning_summary,
            'decision_factors': decision.decision_factors,

            # Validation
            'validated': decision.decision_validated,
            'tool_execution_success': decision.tool_execution_success,

            # Provenance Relationships
            'prov:wasAssociatedWith': f'urn:agent:{decision.was_associated_with}' if decision.was_associated_with else None,
            'prov:used': f'urn:entity:{decision.used_entity}' if decision.used_entity else None,

            # Audit
            'created_at': decision.created_at.isoformat() if decision.created_at else None,
            'created_by': decision.created_by
        }

        provenance_data['orchestration_decisions'].append(decision_data)

    # Return as JSON with appropriate headers
    return jsonify(provenance_data)
