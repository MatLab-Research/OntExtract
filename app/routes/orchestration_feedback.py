"""
Human-in-the-Loop Orchestration Feedback Routes

RESTful API endpoints for researchers to provide feedback on orchestration decisions
and apply manual overrides for continuous system improvement.
"""

from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for
from flask_login import current_user
from app.utils.auth_decorators import api_require_login_for_write
from app import db
from app.models.orchestration_logs import OrchestrationDecision
from app.models.orchestration_feedback import (
    OrchestrationFeedback, 
    LearningPattern, 
    OrchestrationOverride
)
import json
import logging
from datetime import datetime
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

bp = Blueprint('orchestration_feedback', __name__, url_prefix='/orchestration')


@bp.route('/')
@bp.route('/dashboard')
@api_require_login_for_write
def dashboard():
    """Orchestration dashboard showing recent activity and key metrics"""
    
    # Get recent decisions
    recent_decisions = OrchestrationDecision.query.order_by(
        OrchestrationDecision.created_at.desc()
    ).limit(10).all()
    
    # Get pending feedback count
    pending_feedback = OrchestrationFeedback.query.filter_by(
        feedback_status='pending'
    ).count()
    
    # Get active learning patterns
    active_patterns = LearningPattern.query.filter_by(
        pattern_status='active'
    ).limit(5).all()
    
    # Get recent overrides
    recent_overrides = OrchestrationOverride.query.order_by(
        OrchestrationOverride.applied_at.desc()
    ).limit(5).all()
    
    # Basic analytics
    total_decisions = OrchestrationDecision.query.count()
    total_feedback = OrchestrationFeedback.query.count()
    total_patterns = LearningPattern.query.count()
    
    return render_template('orchestration/dashboard.html',
                         recent_decisions=recent_decisions,
                         pending_feedback=pending_feedback,
                         active_patterns=active_patterns,
                         recent_overrides=recent_overrides,
                         total_decisions=total_decisions,
                         total_feedback=total_feedback,
                         total_patterns=total_patterns)


@bp.route('/decisions', methods=['GET'])
@api_require_login_for_write
def decisions():
    """List recent orchestration decisions for feedback"""
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Filter options
    experiment_id = request.args.get('experiment_id', type=int)
    term_text = request.args.get('term')
    confidence_threshold = request.args.get('min_confidence', type=float)
    
    query = OrchestrationDecision.query
    
    if experiment_id:
        query = query.filter_by(experiment_id=experiment_id)
    
    if term_text:
        query = query.filter(OrchestrationDecision.term_text.ilike(f'%{term_text}%'))
    
    if confidence_threshold:
        query = query.filter(OrchestrationDecision.decision_confidence >= confidence_threshold)
    
    # Order by most recent first
    query = query.order_by(OrchestrationDecision.created_at.desc())
    
    decisions = query.paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    if request.headers.get('Accept') == 'application/json':
        return jsonify({
            'decisions': [
                {
                    'id': str(decision.id),
                    'term_text': decision.term_text,
                    'selected_tools': decision.selected_tools,
                    'embedding_model': decision.embedding_model,
                    'confidence': float(decision.decision_confidence) if decision.decision_confidence else None,
                    'created_at': decision.created_at.isoformat() if decision.created_at else None,
                    'feedback_count': len(decision.feedback_entries) if hasattr(decision, 'feedback_entries') and decision.feedback_entries else 0,
                    'has_override': len(decision.manual_overrides) > 0 if hasattr(decision, 'manual_overrides') and decision.manual_overrides else False
                }
                for decision in decisions.items
            ],
            'pagination': {
                'page': decisions.page,
                'pages': decisions.pages,
                'per_page': decisions.per_page,
                'total': decisions.total
            }
        })
    
    return render_template('orchestration/decision_list.html', decisions=decisions)


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


@bp.route('/learning-patterns', methods=['GET'])
@api_require_login_for_write
def learning_patterns():
    """List active learning patterns derived from researcher feedback"""
    
    patterns = LearningPattern.query.filter_by(pattern_status='active').order_by(
        LearningPattern.success_rate.desc(),
        LearningPattern.confidence.desc()
    ).all()
    
    if request.headers.get('Accept') == 'application/json':
        return jsonify({
            'patterns': [
                {
                    'id': str(pattern.id),
                    'name': pattern.pattern_name,
                    'type': pattern.pattern_type,
                    'context_signature': pattern.context_signature,
                    'confidence': float(pattern.confidence),
                    'success_rate': float(pattern.success_rate) if pattern.success_rate else None,
                    'times_applied': pattern.times_applied,
                    'recommendations': pattern.recommendations,
                    'created_at': pattern.created_at.isoformat()
                }
                for pattern in patterns
            ]
        })
    
    return render_template('orchestration/learning_patterns.html', patterns=patterns)


@bp.route('/learning-patterns/<pattern_id>/toggle', methods=['POST'])
@api_require_login_for_write
def toggle_learning_pattern(pattern_id):
    """Enable/disable a learning pattern"""
    
    pattern = LearningPattern.query.get_or_404(pattern_id)
    
    new_status = 'active' if pattern.pattern_status != 'active' else 'deprecated'
    pattern.pattern_status = new_status
    pattern.updated_at = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'pattern_id': str(pattern.id),
        'new_status': new_status,
        'message': f'Pattern {"activated" if new_status == "active" else "deactivated"}'
    })


@bp.route('/feedback-analytics', methods=['GET'])
@api_require_login_for_write
def feedback_analytics():
    """Analytics dashboard for orchestration feedback and improvements"""
    
    # Feedback summary statistics
    total_feedback = OrchestrationFeedback.query.count()
    recent_feedback = OrchestrationFeedback.query.filter(
        OrchestrationFeedback.provided_at >= datetime.utcnow().replace(day=1)  # This month
    ).count()
    
    # Agreement level distribution
    agreement_stats = db.session.query(
        OrchestrationFeedback.agreement_level,
        db.func.count(OrchestrationFeedback.id)
    ).group_by(OrchestrationFeedback.agreement_level).all()
    
    # Learning pattern effectiveness
    effective_patterns = LearningPattern.query.filter(
        LearningPattern.success_rate >= 0.7,
        LearningPattern.times_applied >= 3
    ).count()
    
    # Improvement trends
    integrated_feedback = OrchestrationFeedback.query.filter_by(
        feedback_status='integrated'
    ).count()
    
    analytics_data = {
        'summary': {
            'total_feedback_entries': total_feedback,
            'recent_feedback_count': recent_feedback,
            'active_learning_patterns': LearningPattern.query.filter_by(pattern_status='active').count(),
            'effective_patterns': effective_patterns,
            'integrated_feedback': integrated_feedback
        },
        'agreement_distribution': {
            level: count for level, count in agreement_stats
        },
        'top_improvement_areas': [
            # Most common feedback types
            {'area': 'Tool Selection', 'feedback_count': 
             OrchestrationFeedback.query.filter_by(feedback_scope='tool_selection').count()},
            {'area': 'Model Choice', 'feedback_count':
             OrchestrationFeedback.query.filter_by(feedback_scope='model_choice').count()},
            {'area': 'Processing Strategy', 'feedback_count':
             OrchestrationFeedback.query.filter_by(feedback_scope='strategy').count()}
        ]
    }
    
    if request.headers.get('Accept') == 'application/json':
        return jsonify(analytics_data)
    
    return render_template('orchestration/feedback_analytics.html', analytics=analytics_data)


@bp.route('/researchers/<researcher_id>/expertise', methods=['PUT'])
@api_require_login_for_write  
def update_researcher_expertise(researcher_id):
    """Update researcher expertise profile for better feedback weighting"""
    
    if current_user.id != int(researcher_id) and not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        
        # Update user's expertise profile
        # This would typically update a User profile field
        expertise_profile = {
            'domains': data.get('domains', []),
            'experience_level': data.get('experience_level', 'intermediate'),
            'specializations': data.get('specializations', []),
            'research_interests': data.get('research_interests', []),
            'publications': data.get('publications', []),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        # For now, store in session or return success
        # In real implementation, this would update User model
        
        return jsonify({
            'success': True,
            'message': 'Expertise profile updated',
            'expertise_profile': expertise_profile
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Template helper functions
@bp.app_template_global()
def get_feedback_summary(decision):
    """Template helper to get feedback summary for a decision"""
    feedback_entries = OrchestrationFeedback.query.filter_by(
        orchestration_decision_id=decision.id
    ).all()
    
    if not feedback_entries:
        return {'count': 0, 'sentiment': 'none'}
    
    agreement_scores = {
        'strongly_agree': 5,
        'agree': 4,
        'neutral': 3,
        'disagree': 2,
        'strongly_disagree': 1
    }
    
    avg_score = sum(
        agreement_scores.get(feedback.agreement_level, 3) 
        for feedback in feedback_entries
    ) / len(feedback_entries)
    
    if avg_score >= 4:
        sentiment = 'positive'
    elif avg_score <= 2:
        sentiment = 'negative'
    else:
        sentiment = 'mixed'
    
    return {
        'count': len(feedback_entries),
        'sentiment': sentiment,
        'avg_agreement': avg_score
    }