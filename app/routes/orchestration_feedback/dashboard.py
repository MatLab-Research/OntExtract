"""
Orchestration Feedback Dashboard Routes

Dashboard and overview routes for orchestration feedback system.

Routes:
- GET /orchestration/ or /orchestration/dashboard - Main dashboard
- GET /orchestration/decisions                    - List decisions
"""

from flask import request, jsonify, render_template
from app.utils.auth_decorators import api_require_login_for_write
from app.models.orchestration_logs import OrchestrationDecision
from app.models.orchestration_feedback import (
    OrchestrationFeedback,
    LearningPattern,
    OrchestrationOverride
)

from . import bp


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
