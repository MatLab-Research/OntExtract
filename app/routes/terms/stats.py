"""
Terms Statistics and Status Routes

This module handles statistics and service status display.

Routes:
- GET /terms/service-status - Service status display
- GET /terms/stats          - Term statistics and analytics
"""

from flask import render_template
from flask_login import current_user
from app.utils.auth_decorators import api_require_login_for_write
from app import db
from app.models import Term, TermVersion
from sqlalchemy import func, desc

from . import terms_bp, get_term_analysis_service


@terms_bp.route('/service-status')
@api_require_login_for_write
def service_status():
    """Display status of all shared services."""
    analysis_service = get_term_analysis_service()

    if not analysis_service:
        status = {'analysis_service': {'available': False, 'reason': 'Service not initialized'}}
    else:
        status = analysis_service.get_service_status()
        status['analysis_service'] = {'available': True, 'initialized': True}

    return render_template('terms/service_status.html', status=status)


@terms_bp.route('/stats')
@api_require_login_for_write
def term_stats():
    """Display term statistics and analytics"""
    # Basic counts
    total_terms = Term.query.count()
    total_versions = TermVersion.query.count()
    user_terms = Term.query.filter_by(created_by=current_user.id).count()
    user_versions = TermVersion.query.filter_by(created_by=current_user.id).count()

    # Domain breakdown
    domain_stats = db.session.query(
        Term.research_domain,
        func.count(Term.id).label('count')
    ).group_by(Term.research_domain).all()

    # Most active users
    user_stats = db.session.query(
        Term.created_by,
        func.count(Term.id).label('term_count')
    ).join(Term.creator).group_by(Term.created_by).order_by(desc('term_count')).limit(10).all()

    # Recent activity
    recent_terms = Term.query.order_by(Term.created_at.desc()).limit(5).all()
    recent_versions = TermVersion.query.order_by(TermVersion.created_at.desc()).limit(5).all()

    return render_template('terms/stats.html',
                         total_terms=total_terms,
                         total_versions=total_versions,
                         user_terms=user_terms,
                         user_versions=user_versions,
                         domain_stats=domain_stats,
                         user_stats=user_stats,
                         recent_terms=recent_terms,
                         recent_versions=recent_versions)
