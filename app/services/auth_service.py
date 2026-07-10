"""Authentication, registration, and password-reset workflows."""

import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlsplit

from sqlalchemy.exc import IntegrityError

from app import db
from app.models.user import User
from app.services.base_service import ServiceError, ValidationError


class AuthenticationError(ServiceError):
    """Credentials are invalid or the account cannot authenticate."""


class SuspendedAccountError(AuthenticationError):
    """The supplied credentials belong to a suspended account."""


class DuplicateUsernameError(ValidationError):
    """A registration username is already in use."""


class DuplicateEmailError(ValidationError):
    """A registration email is already in use."""


class InvalidResetTokenError(ValidationError):
    """A password-reset token is missing or invalid."""


class ExpiredResetTokenError(ValidationError):
    """A password-reset token is expired."""


@dataclass(frozen=True)
class LoginResult:
    user: User
    remember: bool
    redirect_target: str | None


@dataclass(frozen=True)
class ResetRequestResult:
    email_sent: bool


class AuthService:
    """Manage authentication state transitions independently of Flask routes."""

    MIN_PASSWORD_LENGTH = 6
    RESET_EXPIRY_HOURS = 1

    def __init__(
        self,
        email_service,
        clock=None,
        token_factory=None,
    ):
        self.email_service = email_service
        self.clock = clock or datetime.utcnow
        self.token_factory = token_factory or (lambda: secrets.token_urlsafe(32))

    def authenticate(
        self,
        username,
        password,
        remember=False,
        next_url=None,
        host_url=None,
    ):
        username = self._clean(username)
        if not username or not password:
            raise ValidationError('Please enter both username and password')
        user = User.query.filter_by(username=username).first()
        if not user or not user.check_password(password):
            raise AuthenticationError('Invalid username or password')
        if not user.is_active or user.account_status == 'suspended':
            raise SuspendedAccountError(
                'Your account has been suspended. Please contact an administrator.'
            )
        user.last_login = self.clock()
        try:
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            raise ServiceError('Unable to complete login') from exc
        return LoginResult(
            user=user,
            remember=bool(remember),
            redirect_target=self.safe_redirect(next_url, host_url),
        )

    def register(self, username, email, password, confirm_password):
        username = self._clean(username)
        email = self._clean(email).lower()
        self._validate_registration(username, email, password, confirm_password)
        if User.query.filter_by(username=username).first():
            raise DuplicateUsernameError('Username already exists')
        if User.query.filter(func_lower(User.email) == email).first():
            raise DuplicateEmailError('Email already registered')
        user = User(
            username=username,
            email=email,
            password=password,
            account_status='active',
            email_verified=True,
        )
        try:
            db.session.add(user)
            db.session.commit()
        except IntegrityError as exc:
            db.session.rollback()
            self._raise_duplicate_after_race(username, email, exc)
        except Exception as exc:
            db.session.rollback()
            raise ServiceError('An error occurred during registration') from exc
        return user

    def request_password_reset(self, email):
        email = self._clean(email).lower()
        if not email:
            raise ValidationError('Please enter your email address')
        user = User.query.filter(func_lower(User.email) == email).first()
        if not user:
            return ResetRequestResult(email_sent=False)
        token = self.token_factory()
        user.email_verification_token = token
        user.email_verification_sent_at = self.clock()
        try:
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            raise ServiceError('Unable to create password reset request') from exc
        sent = bool(self.email_service.send_password_reset_email(user, token))
        return ResetRequestResult(email_sent=sent)

    def get_reset_user(self, token):
        if not token:
            raise InvalidResetTokenError('Invalid or expired reset link')
        user = User.query.filter_by(email_verification_token=token).first()
        if not user:
            raise InvalidResetTokenError('Invalid or expired reset link')
        sent_at = user.email_verification_sent_at
        if not sent_at or self.clock() > (
            sent_at + timedelta(hours=self.RESET_EXPIRY_HOURS)
        ):
            self._invalidate_token(user)
            raise ExpiredResetTokenError(
                'Reset link expired. Please request a new one.'
            )
        return user

    def reset_password(self, token, password, confirm_password):
        user = self.get_reset_user(token)
        self._validate_password_pair(password, confirm_password)
        user.set_password(password)
        user.email_verification_token = None
        user.email_verification_sent_at = None
        try:
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            raise ServiceError('Unable to reset password') from exc
        return user

    @staticmethod
    def safe_redirect(next_url, host_url):
        if not next_url or not host_url:
            return None
        host = urlsplit(host_url)
        target = urlsplit(urljoin(host_url, next_url))
        if target.scheme not in ('http', 'https'):
            return None
        if target.netloc != host.netloc:
            return None
        if next_url.startswith('//'):
            return None
        return target.path + (
            f'?{target.query}' if target.query else ''
        ) + (
            f'#{target.fragment}' if target.fragment else ''
        )

    @classmethod
    def _validate_registration(cls, username, email, password, confirmation):
        if not all((username, email, password, confirmation)):
            raise ValidationError('All fields are required')
        cls._validate_password_pair(password, confirmation)

    @classmethod
    def _validate_password_pair(cls, password, confirmation):
        if not password or not confirmation:
            raise ValidationError('Please enter both password fields')
        if password != confirmation:
            raise ValidationError('Passwords do not match')
        if len(password) < cls.MIN_PASSWORD_LENGTH:
            raise ValidationError(
                f'Password must be at least {cls.MIN_PASSWORD_LENGTH} characters long'
            )

    @staticmethod
    def _clean(value):
        return value.strip() if isinstance(value, str) else ''

    @staticmethod
    def _raise_duplicate_after_race(username, email, original):
        if User.query.filter_by(username=username).first():
            raise DuplicateUsernameError('Username already exists') from original
        if User.query.filter(func_lower(User.email) == email).first():
            raise DuplicateEmailError('Email already registered') from original
        raise ServiceError('An error occurred during registration') from original

    @staticmethod
    def _invalidate_token(user):
        user.email_verification_token = None
        user.email_verification_sent_at = None
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()


def func_lower(column):
    """Keep case-insensitive identity queries explicit and testable."""
    return db.func.lower(column)
