"""
Learning Pattern Management Routes

Routes for managing learning patterns derived from feedback.

Routes:
- GET  /orchestration/learning-patterns          - List patterns
- POST /orchestration/learning-patterns/<id>/toggle - Toggle pattern
"""

from flask import request, jsonify, render_template
from app.utils.auth_decorators import api_require_login_for_write
from app import db
from app.models.orchestration_feedback import LearningPattern
from datetime import datetime

from . import bp


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
