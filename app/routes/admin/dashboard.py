"""Administrative dashboard routes."""

from flask import render_template

from app.models.user import User
from app.utils.auth_decorators import admin_required

from . import admin_bp


@admin_bp.route('/admin')
@admin_required
def dashboard():
    """Admin dashboard with user statistics"""
    # Get user statistics
    total_users = User.query.count()
    active_users = User.query.filter_by(account_status='active').count()
    suspended_users = User.query.filter_by(account_status='suspended').count()
    admin_users = User.query.filter_by(is_admin=True).count()

    # Get recent users
    recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()

    stats = {
        'total_users': total_users,
        'active_users': active_users,
        'suspended_users': suspended_users,
        'admin_users': admin_users,
        'recent_users': recent_users,
        'active_page': 'dashboard',
        'page_title': 'Dashboard'
    }

    return render_template('admin/dashboard.html', **stats)
