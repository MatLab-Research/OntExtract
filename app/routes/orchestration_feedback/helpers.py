"""
Orchestration Feedback Template Helpers

Template helper functions for orchestration feedback system.
"""

from app.models.orchestration_feedback import OrchestrationFeedback

from . import bp


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
