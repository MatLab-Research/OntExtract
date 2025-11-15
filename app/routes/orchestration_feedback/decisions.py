"""
Orchestration Decision Management Routes

Decision feedback and override routes.

Routes:
- GET  /orchestration/decisions/<id>          - View decision detail
- POST /orchestration/decisions/<id>/feedback - Provide feedback
- POST /orchestration/decisions/<id>/override - Apply override
"""

from flask import request, jsonify, render_template, current_app
from flask_login import current_user
from app.utils.auth_decorators import api_require_login_for_write
from app import db
from app.models.orchestration_logs import OrchestrationDecision
from app.models.orchestration_feedback import (
    OrchestrationFeedback,
    LearningPattern,
    OrchestrationOverride
)
import logging
from datetime import datetime

from . import bp

logger = logging.getLogger(__name__)


@bp.route('/decisions/<decision_id>', methods=['GET'])
@api_require_login_for_write
def get_decision(decision_id):
    """View detailed orchestration decision for feedback"""

    decision = OrchestrationDecision.query.get_or_404(decision_id)

    # Get existing feedback
    existing_feedback = OrchestrationFeedback.query.filter_by(
        orchestration_decision_id=decision.id
    ).order_by(OrchestrationFeedback.provided_at.desc()).all()

    # Get applicable learning patterns
    context = {
        'year': decision.input_metadata.get('year') if decision.input_metadata else None,
        'domain': decision.input_metadata.get('domain') if decision.input_metadata else None,
        'complexity': decision.input_metadata.get('complexity') if decision.input_metadata else None
    }

    applicable_patterns = LearningPattern.find_applicable_patterns(context)

    if request.headers.get('Accept') == 'application/json':
        return jsonify({
            'decision': decision.get_decision_summary(),
            'input_metadata': decision.input_metadata,
            'decision_factors': decision.decision_factors,
            'existing_feedback': [
                {
                    'id': str(feedback.id),
                    'type': feedback.feedback_type,
                    'agreement': feedback.agreement_level,
                    'reasoning': feedback.reasoning,
                    'provided_at': feedback.provided_at.isoformat(),
                    'researcher_id': feedback.researcher_id
                }
                for feedback in existing_feedback
            ],
            'applicable_patterns': [
                {
                    'id': str(pattern.id),
                    'name': pattern.pattern_name,
                    'type': pattern.pattern_type,
                    'confidence': float(pattern.confidence),
                    'success_rate': float(pattern.success_rate) if pattern.success_rate else None
                }
                for pattern in applicable_patterns
            ]
        })

    return render_template(
        'orchestration/decision_detail.html',
        decision=decision,
        existing_feedback=existing_feedback,
        applicable_patterns=applicable_patterns
    )


@bp.route('/decisions/<decision_id>/feedback', methods=['POST'])
@api_require_login_for_write
def provide_feedback(decision_id):
    """Provide feedback on an orchestration decision"""

    decision = OrchestrationDecision.query.get_or_404(decision_id)

    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ['feedback_type', 'agreement_level', 'reasoning']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        # Create feedback entry
        feedback = OrchestrationFeedback(
            orchestration_decision_id=decision.id,
            researcher_id=current_user.id,
            feedback_type=data['feedback_type']
        )

        # Set researcher expertise context
        researcher_expertise = data.get('expertise', {})
        if not researcher_expertise:
            # Try to infer from user profile or previous feedback
            researcher_expertise = {
                'domains': [decision.input_metadata.get('domain', 'general')] if decision.input_metadata else ['general'],
                'experience_level': 'intermediate'  # Default
            }

        feedback_data = {
            'type': data['feedback_type'],
            'scope': data.get('feedback_scope', 'tool_selection'),
            'agreement': data['agreement_level'],
            'confidence': data.get('confidence_assessment', 0.8),
            'reasoning': data['reasoning'],
            'preferred_decision': data.get('researcher_preference', {}),
            'domain_factors': data.get('domain_specific_factors', {}),
            'suggested_tools': data.get('suggested_tools', []),
            'suggested_model': data.get('suggested_embedding_model'),
            'suggested_strategy': data.get('suggested_processing_strategy'),
            'alternative_reasoning': data.get('alternative_reasoning'),
            'expertise': researcher_expertise
        }

        feedback.create_from_decision(decision, current_user, feedback_data)

        db.session.add(feedback)
        db.session.commit()

        # Generate learning pattern if feedback indicates disagreement
        if data['agreement_level'] in ['disagree', 'strongly_disagree']:
            learning_pattern_data = feedback.generate_learning_pattern()

            # Create or update learning pattern
            pattern = LearningPattern(
                pattern_name=f"Feedback_{feedback.feedback_type}_{datetime.now().strftime('%Y%m%d')}",
                pattern_type='preference' if feedback.feedback_type == 'enhancement' else 'avoidance',
                context_signature=learning_pattern_data['context_signature'],
                conditions=learning_pattern_data['applicability_conditions'],
                recommendations=learning_pattern_data['prefer_decisions'],
                confidence=learning_pattern_data['confidence'],
                derived_from_feedback=feedback.id,
                researcher_authority=learning_pattern_data['researcher_authority']
            )

            db.session.add(pattern)
            db.session.commit()

            logger.info(f"Learning pattern created from feedback {feedback.id}")

        return jsonify({
            'success': True,
            'feedback_id': str(feedback.id),
            'message': 'Feedback recorded successfully',
            'learning_pattern_created': data['agreement_level'] in ['disagree', 'strongly_disagree']
        })

    except Exception as e:
        logger.error(f"Error creating feedback: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/decisions/<decision_id>/override', methods=['POST'])
@api_require_login_for_write
def apply_override(decision_id):
    """Apply manual override to orchestration decision"""

    decision = OrchestrationDecision.query.get_or_404(decision_id)

    try:
        data = request.get_json()

        # Validate override data
        required_fields = ['override_type', 'overridden_decision', 'justification']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        # Create override record
        override = OrchestrationOverride(
            orchestration_decision_id=decision.id,
            researcher_id=current_user.id,
            override_type=data['override_type'],
            original_decision={
                'selected_tools': decision.selected_tools,
                'embedding_model': decision.embedding_model,
                'processing_strategy': decision.processing_strategy,
                'confidence': float(decision.decision_confidence) if decision.decision_confidence else None
            },
            overridden_decision=data['overridden_decision'],
            justification=data['justification'],
            expert_knowledge_applied=data.get('expert_knowledge', {})
        )

        db.session.add(override)

        # If requested, execute the override immediately
        if data.get('execute_immediately', False):
            execution_result = override.execute_override()

            # Generate improvement insights
            insights = override.generate_improvement_insights()

            # Optionally create learning pattern from override
            if data.get('create_learning_pattern', True):
                pattern = LearningPattern(
                    pattern_name=f"Override_{override.override_type}_{datetime.now().strftime('%Y%m%d')}",
                    pattern_type='preference',
                    context_signature=insights['applicability']['context_signature'],
                    conditions={'override_context': True},  # Mark as override-derived
                    recommendations=insights['decision_improvement']['improved'],
                    confidence=0.9,  # High confidence from expert override
                    researcher_authority={'source': 'manual_override', 'confidence': 1.0}
                )

                db.session.add(pattern)

        db.session.commit()

        response_data = {
            'success': True,
            'override_id': str(override.id),
            'message': 'Override applied successfully'
        }

        if data.get('execute_immediately', False):
            response_data['execution_result'] = execution_result
            response_data['improvement_insights'] = insights

        return jsonify(response_data)

    except Exception as e:
        logger.error(f"Error applying override: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
