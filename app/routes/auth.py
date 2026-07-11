"""Authentication, registration, logout, and password-reset routes."""

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.services.auth_service import (
    AuthenticationError,
    AuthService,
    ExpiredResetTokenError,
    InvalidResetTokenError,
)
from app.services.base_service import ServiceError, ValidationError
from app.services.email_service import EmailService


auth_bp = Blueprint('auth', __name__)


def _service():
    return AuthService(EmailService)


def _anonymous_redirect():
    return redirect(url_for('index')) if current_user.is_authenticated else None


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    authenticated = _anonymous_redirect()
    if authenticated:
        return authenticated
    if request.method == 'POST':
        try:
            result = _service().authenticate(
                request.form.get('username'),
                request.form.get('password'),
                remember=request.form.get('remember'),
                next_url=request.args.get('next'),
                host_url=request.host_url,
            )
            login_user(result.user, remember=result.remember)
            return redirect(result.redirect_target or url_for('index'))
        except (ValidationError, AuthenticationError) as exc:
            flash(str(exc), 'error')
        except ServiceError as exc:
            flash(str(exc), 'error')
    return render_template('auth/login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    authenticated = _anonymous_redirect()
    if authenticated:
        return authenticated
    if request.method == 'POST':
        try:
            _service().register(
                request.form.get('username'),
                request.form.get('email'),
                request.form.get('password'),
                request.form.get('confirm_password'),
            )
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('auth.login'))
        except (ValidationError, ServiceError) as exc:
            flash(str(exc), 'error')
    return render_template('auth/register.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    authenticated = _anonymous_redirect()
    if authenticated:
        return authenticated
    if request.method == 'POST':
        try:
            _service().request_password_reset(request.form.get('email'))
            flash(
                'If an account exists with this email, password reset '
                'instructions have been sent.',
                'info',
            )
        except ValidationError as exc:
            flash(str(exc), 'error')
        except ServiceError:
            flash(
                'If an account exists with this email, password reset '
                'instructions have been sent.',
                'info',
            )
    return render_template('auth/forgot_password.html')


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    authenticated = _anonymous_redirect()
    if authenticated:
        return authenticated
    try:
        service = _service()
        if request.method == 'POST':
            service.reset_password(
                token,
                request.form.get('password'),
                request.form.get('confirm_password'),
            )
            flash('Password reset successful! You can now log in.', 'success')
            return redirect(url_for('auth.login'))
        service.get_reset_user(token)
    except (InvalidResetTokenError, ExpiredResetTokenError) as exc:
        flash(str(exc), 'error')
        return redirect(url_for('auth.forgot_password'))
    except ValidationError as exc:
        flash(str(exc), 'error')
    except ServiceError as exc:
        flash(str(exc), 'error')
    return render_template('auth/reset_password.html', token=token)
