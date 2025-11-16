"""
Orchestration Feedback Analytics Routes

Analytics and researcher profile management routes.

Routes:
- GET /orchestration/feedback-analytics        - Analytics dashboard
- PUT /orchestration/researchers/<id>/expertise - Update researcher expertise
"""

from flask import request, jsonify, render_template, current_app
from flask_login import current_user
from app.utils.auth_decorators import api_require_login_for_write
from app import db
from app.models.orchestration_feedback import (
    OrchestrationFeedback,
    LearningPattern
)
from datetime import datetime

from . import bp


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
