"""Regression coverage for administrative user management."""

import pytest


def _user(db_session, suffix, **kwargs):
    from app.models.user import User

    user = User(
        username=f'admin-managed-{suffix}',
        email=f'admin-managed-{suffix}@example.com',
        password='initial-password',
        account_status=kwargs.pop('account_status', 'active'),
        is_active=kwargs.pop('is_active', True),
        **kwargs,
    )
    db_session.add(user)
    db_session.commit()
    return user


def test_admin_user_routes_remain_canonical(app):
    expected = 'app.routes.admin.users'
    endpoints = (
        'admin.list_users',
        'admin.view_user',
        'admin.edit_user',
        'admin.set_user_password',
        'admin.toggle_admin',
        'admin.suspend_user',
        'admin.activate_user',
        'admin.delete_user',
        'admin.make_admin',
    )
    assert all(
        app.view_functions[endpoint].__module__ == expected
        for endpoint in endpoints
    )


def test_list_context_filters_status_role_and_search(db_session):
    from app.services.admin_user_service import AdminUserService

    target = _user(db_session, 'search-target', is_admin=True)
    _user(
        db_session,
        'search-other',
        account_status='suspended',
        is_active=False,
    )

    context = AdminUserService.list_context(
        1,
        status_filter='active',
        role_filter='admin',
        search_query='search-target',
    )

    assert [user.id for user in context['users']] == [target.id]
    assert context['status_filter'] == 'active'
    assert context['role_filter'] == 'admin'
    assert context['search_query'] == 'search-target'


def test_detail_context_counts_owned_content(
    db_session, test_user, sample_document, temporal_experiment, sample_term
):
    from app.services.admin_user_service import AdminUserService

    sample_term.created_by = test_user.id
    db_session.commit()
    context = AdminUserService.detail_context(test_user.id)

    assert context['user'] is test_user
    assert context['documents_count'] >= 1
    assert context['experiments_count'] >= 1
    assert context['terms_count'] >= 1


def test_update_user_synchronizes_status_and_role(
    db_session, admin_user
):
    from app.services.admin_user_service import AdminUserService

    managed = _user(db_session, 'update')
    updated = AdminUserService.update_user(
        managed.id,
        admin_user.id,
        True,
        'suspended',
    )

    assert updated.is_admin is True
    assert updated.account_status == 'suspended'
    assert updated.is_active is False


@pytest.mark.parametrize(
    ('operation', 'message'),
    [
        ('edit', 'cannot edit your own account'),
        ('password', 'cannot set your own password'),
        ('toggle', 'Cannot modify your own admin status'),
        ('suspend', 'cannot suspend your own account'),
        ('delete', 'cannot delete your own account'),
    ],
)
def test_admin_self_protection(admin_user, operation, message):
    from app.services.admin_user_service import AdminUserService
    from app.services.base_service import PermissionError

    actions = {
        'edit': lambda: AdminUserService.get_edit_context(
            admin_user.id,
            admin_user.id,
        ),
        'password': lambda: AdminUserService.set_password(
            admin_user.id,
            admin_user.id,
            'new-password',
            'new-password',
        ),
        'toggle': lambda: AdminUserService.toggle_admin(
            admin_user.id,
            admin_user.id,
        ),
        'suspend': lambda: AdminUserService.suspend(
            admin_user.id,
            admin_user.id,
        ),
        'delete': lambda: AdminUserService.delete_user(
            admin_user.id,
            admin_user.id,
        ),
    }

    with pytest.raises(PermissionError, match=message):
        actions[operation]()


@pytest.mark.parametrize(
    ('password', 'confirmation', 'message'),
    [
        ('short', 'short', 'at least 6 characters'),
        ('long-enough', 'different', 'Passwords do not match'),
    ],
)
def test_password_validation(
    db_session, admin_user, password, confirmation, message
):
    from app.services.admin_user_service import AdminUserService
    from app.services.base_service import ValidationError

    managed = _user(db_session, f'password-{len(password)}')
    with pytest.raises(ValidationError, match=message):
        AdminUserService.set_password(
            managed.id,
            admin_user.id,
            password,
            confirmation,
        )


def test_password_toggle_suspend_activate_and_promote(
    db_session, admin_user
):
    from app.services.admin_user_service import AdminUserService

    managed = _user(db_session, 'transitions')
    AdminUserService.set_password(
        managed.id,
        admin_user.id,
        'replacement-password',
        'replacement-password',
    )
    assert managed.check_password('replacement-password') is True

    assert AdminUserService.toggle_admin(
        managed.id,
        admin_user.id,
    ).is_admin is True
    suspended = AdminUserService.suspend(managed.id, admin_user.id)
    assert suspended.account_status == 'suspended'
    assert suspended.is_active is False
    activated = AdminUserService.activate(managed.id)
    assert activated.account_status == 'active'
    assert activated.is_active is True

    managed.is_admin = False
    db_session.commit()
    assert AdminUserService.make_admin(managed.username).is_admin is True


def test_delete_empty_user(db_session, admin_user):
    from app.models.user import User
    from app.services.admin_user_service import AdminUserService

    managed = _user(db_session, 'delete-empty')
    managed_id = managed.id
    username = AdminUserService.delete_user(managed_id, admin_user.id)

    assert username == 'admin-managed-delete-empty'
    assert db_session.get(User, managed_id) is None


def test_admin_user_routes_apply_transitions(admin_client, db_session):
    managed = _user(db_session, 'route-transition')

    edit = admin_client.post(
        f'/admin/users/{managed.id}/edit',
        data={'is_admin': 'true', 'account_status': 'suspended'},
    )
    toggle = admin_client.post(f'/admin/users/{managed.id}/toggle-admin')
    activate = admin_client.post(f'/admin/users/{managed.id}/activate')

    assert edit.status_code == 302
    assert toggle.status_code == 200
    assert toggle.get_json() == {
        'success': True,
        'is_admin': False,
        'username': managed.username,
    }
    assert activate.status_code == 302
    assert managed.account_status == 'active'
    assert managed.is_active is True


def test_admin_user_routes_preserve_error_contracts(
    admin_client, admin_user
):
    missing_toggle = admin_client.post('/admin/users/999999/toggle-admin')
    self_toggle = admin_client.post(
        f'/admin/users/{admin_user.id}/toggle-admin'
    )
    missing_view = admin_client.get('/admin/users/999999')
    missing_promote = admin_client.post('/admin/make-admin/no-such-user')

    assert missing_toggle.status_code == 404
    assert missing_toggle.get_json()['error'] == 'User not found'
    assert self_toggle.status_code == 400
    assert self_toggle.get_json()['error'] == (
        'Cannot modify your own admin status'
    )
    assert missing_view.status_code == 302
    assert missing_view.headers['Location'].endswith('/admin/users')
    assert missing_promote.status_code == 404


def test_non_admin_cannot_manage_users(auth_client, test_user):
    response = auth_client.post(f'/admin/users/{test_user.id}/activate')

    assert response.status_code == 403
