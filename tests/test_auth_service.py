"""Regression coverage for authentication and password-reset workflows."""

from datetime import datetime, timedelta

import pytest


class EmailRecorder:
    def __init__(self, sent=True):
        self.sent = sent
        self.calls = []

    def send_password_reset_email(self, user, token):
        self.calls.append((user.id, token))
        return self.sent


def _service(email=None, clock=None):
    from app.services.auth_service import AuthService

    return AuthService(
        email or EmailRecorder(),
        clock=clock or (lambda: datetime(2026, 1, 1, 12, 0, 0)),
        token_factory=lambda: 'deterministic-reset-token',
    )


def _user(db_session, suffix, **kwargs):
    from app.models.user import User

    user = User(
        username=f'auth-{suffix}',
        email=f'auth-{suffix}@example.com',
        password=kwargs.pop('password', 'password123'),
        account_status=kwargs.pop('account_status', 'active'),
        is_active=kwargs.pop('is_active', True),
        **kwargs,
    )
    db_session.add(user)
    db_session.commit()
    return user


def test_auth_routes_remain_canonical(app):
    for endpoint in (
        'auth.login',
        'auth.register',
        'auth.logout',
        'auth.forgot_password',
        'auth.reset_password',
    ):
        assert app.view_functions[endpoint].__module__ == 'app.routes.auth'


def test_authenticate_updates_last_login_and_returns_safe_redirect(
    db_session, test_user
):
    clock = datetime(2026, 2, 3, 4, 5, 6)
    result = _service(clock=lambda: clock).authenticate(
        f'  {test_user.username}  ',
        'testpass123',
        remember='on',
        next_url='/experiments/?page=2#recent',
        host_url='http://localhost/',
    )

    assert result.user is test_user
    assert result.remember is True
    assert result.redirect_target == '/experiments/?page=2#recent'
    assert test_user.last_login == clock


@pytest.mark.parametrize(
    ('next_url', 'expected'),
    [
        ('/upload/', '/upload/'),
        ('http://localhost/input/documents', '/input/documents'),
        ('https://attacker.example/phish', None),
        ('//attacker.example/phish', None),
        ('javascript:alert(1)', None),
        (None, None),
    ],
)
def test_safe_redirect_rejects_external_targets(next_url, expected):
    from app.services.auth_service import AuthService

    assert AuthService.safe_redirect(next_url, 'http://localhost/') == expected


def test_authenticate_rejects_missing_invalid_and_suspended_accounts(
    db_session, test_user
):
    from app.services.auth_service import AuthenticationError, SuspendedAccountError
    from app.services.base_service import ValidationError

    service = _service()
    with pytest.raises(ValidationError, match='both username and password'):
        service.authenticate('', '')
    with pytest.raises(AuthenticationError, match='Invalid username or password'):
        service.authenticate(test_user.username, 'incorrect')

    test_user.account_status = 'suspended'
    db_session.commit()
    with pytest.raises(SuspendedAccountError, match='suspended'):
        service.authenticate(test_user.username, 'testpass123')


def test_register_normalizes_email_and_hashes_password(db_session):
    from app.services.auth_service import AuthService

    user = _service().register(
        '  new-researcher  ',
        '  NEW.RESEARCHER@Example.COM  ',
        'secure-password',
        'secure-password',
    )

    assert user.username == 'new-researcher'
    assert user.email == 'new.researcher@example.com'
    assert user.account_status == 'active'
    assert user.email_verified is True
    assert user.password_hash != 'secure-password'
    assert user.check_password('secure-password') is True
    assert db_session.get(type(user), user.id) is user


@pytest.mark.parametrize(
    ('values', 'message'),
    [
        (('', 'a@example.com', 'password', 'password'), 'All fields are required'),
        (
            ('researcher', 'a@example.com', 'password', 'different'),
            'Passwords do not match',
        ),
        (
            ('researcher', 'a@example.com', 'short', 'short'),
            'Password must be at least 6 characters',
        ),
    ],
)
def test_register_validates_fields(values, message):
    from app.services.base_service import ValidationError

    with pytest.raises(ValidationError, match=message):
        _service().register(*values)


def test_register_rejects_duplicate_username_and_case_insensitive_email(
    db_session, test_user
):
    from app.services.auth_service import DuplicateEmailError, DuplicateUsernameError

    service = _service()
    with pytest.raises(DuplicateUsernameError, match='Username already exists'):
        service.register(
            test_user.username,
            'different@example.com',
            'password',
            'password',
        )
    with pytest.raises(DuplicateEmailError, match='Email already registered'):
        service.register(
            'different-user',
            test_user.email.upper(),
            'password',
            'password',
        )


def test_reset_request_is_deterministic_for_existing_and_missing_email(
    db_session, test_user
):
    email = EmailRecorder()
    clock = datetime(2026, 3, 1, 9, 0, 0)
    service = _service(email, clock=lambda: clock)

    existing = service.request_password_reset(test_user.email.upper())
    missing = service.request_password_reset('missing@example.com')

    assert existing.email_sent is True
    assert missing.email_sent is False
    assert test_user.email_verification_token == 'deterministic-reset-token'
    assert test_user.email_verification_sent_at == clock
    assert email.calls == [(test_user.id, 'deterministic-reset-token')]


def test_reset_request_preserves_token_when_email_delivery_fails(
    db_session, test_user
):
    result = _service(EmailRecorder(sent=False)).request_password_reset(
        test_user.email
    )
    assert result.email_sent is False
    assert test_user.email_verification_token == 'deterministic-reset-token'


def test_reset_password_changes_password_and_invalidates_token(
    db_session, test_user
):
    clock = datetime(2026, 4, 1, 10, 0, 0)
    test_user.email_verification_token = 'valid-token'
    test_user.email_verification_sent_at = clock - timedelta(minutes=30)
    db_session.commit()

    service = _service(clock=lambda: clock)
    user = service.reset_password(
        'valid-token',
        'new-password',
        'new-password',
    )

    assert user.check_password('new-password') is True
    assert user.email_verification_token is None
    assert user.email_verification_sent_at is None
    from app.services.auth_service import InvalidResetTokenError
    with pytest.raises(InvalidResetTokenError):
        service.get_reset_user('valid-token')


def test_expired_reset_token_is_invalidated(db_session, test_user):
    from app.services.auth_service import ExpiredResetTokenError

    clock = datetime(2026, 4, 1, 10, 0, 0)
    test_user.email_verification_token = 'expired-token'
    test_user.email_verification_sent_at = clock - timedelta(hours=2)
    db_session.commit()

    with pytest.raises(ExpiredResetTokenError, match='Reset link expired'):
        _service(clock=lambda: clock).get_reset_user('expired-token')
    assert test_user.email_verification_token is None
    assert test_user.email_verification_sent_at is None


def test_login_route_rejects_open_redirect(app, db_session, test_user):
    external = app.test_client().post(
        '/auth/login?next=https://attacker.example/phish',
        data={'username': test_user.username, 'password': 'testpass123'},
    )
    assert external.status_code == 302
    assert external.headers['Location'].endswith('/')
    assert 'attacker.example' not in external.headers['Location']


def test_login_route_accepts_local_redirect(app, db_session, test_user):
    local = app.test_client().post(
        '/auth/login?next=/input/documents?type=document',
        data={'username': test_user.username, 'password': 'testpass123'},
    )
    assert local.status_code == 302
    assert local.headers['Location'].endswith(
        '/input/documents?type=document'
    )


def test_login_route_handles_invalid_and_suspended_credentials(
    app, db_session, test_user
):
    invalid = app.test_client().post(
        '/auth/login',
        data={'username': test_user.username, 'password': 'wrong'},
        follow_redirects=True,
    )
    assert invalid.status_code == 200
    assert b'Invalid username or password' in invalid.data

    test_user.account_status = 'suspended'
    db_session.commit()
    suspended = app.test_client().post(
        '/auth/login',
        data={'username': test_user.username, 'password': 'testpass123'},
        follow_redirects=True,
    )
    assert suspended.status_code == 200
    assert b'account has been suspended' in suspended.data


def test_registration_route_creates_user_and_maps_duplicates(app, db_session):
    client = app.test_client()
    created = client.post('/auth/register', data={
        'username': 'route-user',
        'email': 'ROUTE@Example.COM',
        'password': 'password123',
        'confirm_password': 'password123',
    })
    duplicate = client.post(
        '/auth/register',
        data={
            'username': 'route-user',
            'email': 'other@example.com',
            'password': 'password123',
            'confirm_password': 'password123',
        },
        follow_redirects=True,
    )

    assert created.status_code == 302
    assert created.headers['Location'].endswith('/auth/login')
    from app.models.user import User
    user = User.query.filter_by(username='route-user').one()
    assert user.email == 'route@example.com'
    assert duplicate.status_code == 200
    assert b'Username already exists' in duplicate.data


def test_forgot_password_route_does_not_reveal_account_existence(
    app, db_session, test_user, monkeypatch
):
    from app.routes import auth

    monkeypatch.setattr(
        auth.EmailService,
        'send_password_reset_email',
        lambda user, token: False,
    )
    existing = app.test_client().post(
        '/auth/forgot-password',
        data={'email': test_user.email},
        follow_redirects=True,
    )
    missing = app.test_client().post(
        '/auth/forgot-password',
        data={'email': 'missing@example.com'},
        follow_redirects=True,
    )
    generic = (
        b'If an account exists with this email, password reset '
        b'instructions have been sent.'
    )
    assert generic in existing.data
    assert generic in missing.data


def test_reset_password_route_handles_valid_expired_and_invalid_tokens(
    app, db_session, test_user
):
    now = datetime.utcnow()
    test_user.email_verification_token = 'route-valid'
    test_user.email_verification_sent_at = now
    db_session.commit()
    page = app.test_client().get('/auth/reset-password/route-valid')
    assert page.status_code == 200
    assert b'Choose New Password' in page.data
    success = app.test_client().post(
        '/auth/reset-password/route-valid',
        data={
            'password': 'route-new-password',
            'confirm_password': 'route-new-password',
        },
    )
    assert success.status_code == 302
    assert success.headers['Location'].endswith('/auth/login')
    assert test_user.check_password('route-new-password') is True

    invalid = app.test_client().get('/auth/reset-password/not-valid')
    assert invalid.status_code == 302
    assert invalid.headers['Location'].endswith('/auth/forgot-password')

    test_user.email_verification_token = 'route-expired'
    test_user.email_verification_sent_at = now - timedelta(hours=2)
    db_session.commit()
    expired = app.test_client().get('/auth/reset-password/route-expired')
    assert expired.status_code == 302
    assert expired.headers['Location'].endswith('/auth/forgot-password')


def test_authenticated_users_are_redirected_from_anonymous_auth_pages(
    auth_client, test_user
):
    for path in ('/auth/login', '/auth/register', '/auth/forgot-password'):
        response = auth_client.get(path)
        assert response.status_code == 302
        assert response.headers['Location'].endswith('/')


def test_logout_route_clears_session(auth_client):
    logout = auth_client.get('/auth/logout')
    assert logout.status_code == 302
    assert logout.headers['Location'].endswith('/auth/login')
    with auth_client.session_transaction() as session:
        assert '_user_id' not in session
