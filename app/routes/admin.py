"""
Admin Routes for OntExtract

User management, system settings, and administrative functions.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import current_user
from app import db
from app.models.user import User
from app.utils.auth_decorators import admin_required
from datetime import datetime

admin_bp = Blueprint('admin', __name__)


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
        'recent_users': recent_users
    }

    return render_template('admin/dashboard.html', **stats)


@admin_bp.route('/admin/users')
@admin_required
def list_users():
    """List all users with management options"""
    page = request.args.get('page', 1, type=int)
    per_page = 20

    # Filter options
    status_filter = request.args.get('status', 'all')
    role_filter = request.args.get('role', 'all')
    search_query = request.args.get('q', '')

    # Build query
    query = User.query

    if status_filter != 'all':
        query = query.filter_by(account_status=status_filter)

    if role_filter == 'admin':
        query = query.filter_by(is_admin=True)
    elif role_filter == 'user':
        query = query.filter_by(is_admin=False)

    if search_query:
        query = query.filter(
            (User.username.ilike(f'%{search_query}%')) |
            (User.email.ilike(f'%{search_query}%'))
        )

    # Paginate results
    pagination = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return render_template('admin/users.html',
                         users=pagination.items,
                         pagination=pagination,
                         status_filter=status_filter,
                         role_filter=role_filter,
                         search_query=search_query)


@admin_bp.route('/admin/users/<int:user_id>')
@admin_required
def view_user(user_id):
    """View detailed user information"""
    user = db.session.get(User, user_id)
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('admin.list_users'))

    # Get user's content counts
    from app.models.experiment import Experiment
    from app.models.document import Document
    from app.models.term import Term

    experiments_count = Experiment.query.filter_by(user_id=user_id).count()
    documents_count = Document.query.filter_by(user_id=user_id).count()
    terms_count = Term.query.filter_by(created_by=user_id).count()

    return render_template('admin/user_detail.html',
                         user=user,
                         experiments_count=experiments_count,
                         documents_count=documents_count,
                         terms_count=terms_count)


@admin_bp.route('/admin/users/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    """Edit user role and status"""
    user = db.session.get(User, user_id)
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('admin.list_users'))

    # Prevent editing yourself (safety check)
    if user.id == current_user.id:
        flash('You cannot edit your own account from this interface', 'warning')
        return redirect(url_for('admin.view_user', user_id=user_id))

    if request.method == 'POST':
        # Update role
        is_admin = request.form.get('is_admin') == 'true'
        user.is_admin = is_admin

        # Update status
        account_status = request.form.get('account_status')
        if account_status in ['active', 'suspended']:
            user.account_status = account_status
            # Sync is_active with account_status
            user.is_active = (account_status == 'active')

        db.session.commit()
        flash(f'User {user.username} updated successfully', 'success')
        return redirect(url_for('admin.view_user', user_id=user_id))

    return render_template('admin/edit_user.html', user=user)


@admin_bp.route('/admin/users/<int:user_id>/toggle-admin', methods=['POST'])
@admin_required
def toggle_admin(user_id):
    """Toggle user admin status (AJAX)"""
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    # Prevent removing your own admin status
    if user.id == current_user.id:
        return jsonify({'error': 'Cannot modify your own admin status'}), 400

    user.is_admin = not user.is_admin
    db.session.commit()

    return jsonify({
        'success': True,
        'is_admin': user.is_admin,
        'username': user.username
    })


@admin_bp.route('/admin/users/<int:user_id>/suspend', methods=['POST'])
@admin_required
def suspend_user(user_id):
    """Suspend user account"""
    user = db.session.get(User, user_id)
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('admin.list_users'))

    if user.id == current_user.id:
        flash('You cannot suspend your own account', 'error')
        return redirect(url_for('admin.view_user', user_id=user_id))

    user.account_status = 'suspended'
    user.is_active = False
    db.session.commit()

    flash(f'User {user.username} has been suspended', 'success')
    return redirect(url_for('admin.view_user', user_id=user_id))


@admin_bp.route('/admin/users/<int:user_id>/activate', methods=['POST'])
@admin_required
def activate_user(user_id):
    """Activate suspended user account"""
    user = db.session.get(User, user_id)
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('admin.list_users'))

    user.account_status = 'active'
    user.is_active = True
    db.session.commit()

    flash(f'User {user.username} has been activated', 'success')
    return redirect(url_for('admin.view_user', user_id=user_id))


@admin_bp.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    """Delete user and all their content"""
    user = db.session.get(User, user_id)
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('admin.list_users'))

    if user.id == current_user.id:
        flash('You cannot delete your own account', 'error')
        return redirect(url_for('admin.view_user', user_id=user_id))

    username = user.username

    try:
        # Delete user (cascade will handle related content)
        db.session.delete(user)
        db.session.commit()

        flash(f'User {username} and all their content have been deleted', 'success')
        return redirect(url_for('admin.list_users'))

    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting user: {str(e)}', 'error')
        return redirect(url_for('admin.view_user', user_id=user_id))


@admin_bp.route('/admin/make-admin/<username>', methods=['POST'])
@admin_required
def make_admin(username):
    """Quick route to make a user admin (for manual setup)"""
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    user.is_admin = True
    db.session.commit()

    return jsonify({
        'success': True,
        'message': f'{username} is now an admin',
        'username': username
    })
