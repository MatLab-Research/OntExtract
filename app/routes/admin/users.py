"""Administrative user-management routes."""

from flask import flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user

from app.services.admin_user_service import AdminUserService
from app.services.base_service import NotFoundError, PermissionError, ValidationError
from app.utils.auth_decorators import admin_required

from . import admin_bp


def _missing_user_redirect():
    flash('User not found', 'error')
    return redirect(url_for('admin.list_users'))


@admin_bp.route('/admin/users')
@admin_required
def list_users():
    context = AdminUserService.list_context(
        request.args.get('page', 1, type=int),
        request.args.get('status', 'all'),
        request.args.get('role', 'all'),
        request.args.get('q', ''),
    )
    return render_template('admin/users.html', **context)


@admin_bp.route('/admin/users/<int:user_id>')
@admin_required
def view_user(user_id):
    try:
        return render_template(
            'admin/user_detail.html',
            **AdminUserService.detail_context(user_id),
        )
    except NotFoundError:
        return _missing_user_redirect()


@admin_bp.route('/admin/users/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    try:
        if request.method == 'POST':
            user = AdminUserService.update_user(
                user_id,
                current_user.id,
                request.form.get('is_admin') == 'true',
                request.form.get('account_status'),
            )
            flash(f'User {user.username} updated successfully', 'success')
            return redirect(url_for('admin.view_user', user_id=user_id))
        return render_template(
            'admin/edit_user.html',
            **AdminUserService.get_edit_context(user_id, current_user.id),
        )
    except NotFoundError:
        return _missing_user_redirect()
    except PermissionError as exc:
        flash(str(exc), 'warning')
        return redirect(url_for('admin.view_user', user_id=user_id))


@admin_bp.route('/admin/users/<int:user_id>/set-password', methods=['POST'])
@admin_required
def set_user_password(user_id):
    try:
        user = AdminUserService.set_password(
            user_id,
            current_user.id,
            request.form.get('new_password'),
            request.form.get('confirm_password'),
        )
        flash(f'Password set successfully for user {user.username}', 'success')
    except NotFoundError:
        return _missing_user_redirect()
    except PermissionError as exc:
        flash(str(exc), 'warning')
    except ValidationError as exc:
        flash(str(exc), 'error')
    return redirect(url_for('admin.view_user', user_id=user_id))


@admin_bp.route('/admin/users/<int:user_id>/toggle-admin', methods=['POST'])
@admin_required
def toggle_admin(user_id):
    try:
        user = AdminUserService.toggle_admin(user_id, current_user.id)
        return jsonify({
            'success': True,
            'is_admin': user.is_admin,
            'username': user.username,
        })
    except NotFoundError:
        return jsonify({'error': 'User not found'}), 404
    except PermissionError as exc:
        return jsonify({'error': str(exc)}), 400


@admin_bp.route('/admin/users/<int:user_id>/suspend', methods=['POST'])
@admin_required
def suspend_user(user_id):
    try:
        user = AdminUserService.suspend(user_id, current_user.id)
        flash(f'User {user.username} has been suspended', 'success')
    except NotFoundError:
        return _missing_user_redirect()
    except PermissionError as exc:
        flash(str(exc), 'error')
    return redirect(url_for('admin.view_user', user_id=user_id))


@admin_bp.route('/admin/users/<int:user_id>/activate', methods=['POST'])
@admin_required
def activate_user(user_id):
    try:
        user = AdminUserService.activate(user_id)
        flash(f'User {user.username} has been activated', 'success')
    except NotFoundError:
        return _missing_user_redirect()
    return redirect(url_for('admin.view_user', user_id=user_id))


@admin_bp.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    try:
        username = AdminUserService.delete_user(user_id, current_user.id)
        flash(
            f'User {username} and all their content have been deleted',
            'success',
        )
        return redirect(url_for('admin.list_users'))
    except NotFoundError:
        return _missing_user_redirect()
    except PermissionError as exc:
        flash(str(exc), 'error')
    except Exception as exc:
        flash(f'Error deleting user: {exc}', 'error')
    return redirect(url_for('admin.view_user', user_id=user_id))


@admin_bp.route('/admin/make-admin/<username>', methods=['POST'])
@admin_required
def make_admin(username):
    try:
        user = AdminUserService.make_admin(username)
        return jsonify({
            'success': True,
            'message': f'{username} is now an admin',
            'username': user.username,
        })
    except NotFoundError:
        return jsonify({'error': 'User not found'}), 404
