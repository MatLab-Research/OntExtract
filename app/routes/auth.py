from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime
from app import db
from app.models.user import User
from app.services.email_service import EmailService

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = bool(request.form.get('remember'))

        if not username or not password:
            flash('Please enter both username and password', 'error')
            return render_template('auth/login.html')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            # Check if account is active (not suspended)
            if not user.is_active or user.account_status == 'suspended':
                flash('Your account has been suspended. Please contact an administrator.', 'error')
                return render_template('auth/login.html')

            # Successful login
            login_user(user, remember=remember)

            # Update last login
            user.last_login = datetime.utcnow()
            db.session.commit()

            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'error')

    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # Basic validation
        if not all([username, email, password, confirm_password]):
            flash('All fields are required', 'error')
            return render_template('auth/register.html')

        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('auth/register.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters long', 'error')
            return render_template('auth/register.html')

        # Check if username or email already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return render_template('auth/register.html')

        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return render_template('auth/register.html')

        # Create new user - active immediately (email used for password reset only)
        try:
            user = User(
                username=username,
                email=email,
                password=password,
                account_status='active',
                email_verified=True  # No verification needed - email for password reset only
            )
            db.session.add(user)
            db.session.commit()

            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('auth.login'))

        except Exception as e:
            db.session.rollback()
            flash('An error occurred during registration', 'error')
            return render_template('auth/register.html')

    return render_template('auth/register.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Request password reset"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email')

        if not email:
            flash('Please enter your email address', 'error')
            return render_template('auth/forgot_password.html')

        user = User.query.filter_by(email=email).first()

        if user:
            # Generate reset token (reuse email_verification_token field)
            import secrets
            reset_token = secrets.token_urlsafe(32)
            user.email_verification_token = reset_token
            user.email_verification_sent_at = datetime.utcnow()
            db.session.commit()

            # Send password reset email
            if EmailService.send_password_reset_email(user, reset_token):
                flash('Password reset instructions sent to your email.', 'info')
            else:
                flash('Error sending reset email. Please try again later.', 'error')
        else:
            # Don't reveal if email exists (security)
            flash('If an account exists with this email, password reset instructions have been sent.', 'info')

        return render_template('auth/forgot_password.html')

    return render_template('auth/forgot_password.html')


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Reset password with token"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    user = User.query.filter_by(email_verification_token=token).first()

    if not user:
        flash('Invalid or expired reset link', 'error')
        return redirect(url_for('auth.forgot_password'))

    # Check if token expired (1 hour for password reset)
    if EmailService.is_token_expired(user, expiry_hours=1):
        flash('Reset link expired. Please request a new one.', 'error')
        return redirect(url_for('auth.forgot_password'))

    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if not password or not confirm_password:
            flash('Please enter both password fields', 'error')
            return render_template('auth/reset_password.html', token=token)

        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('auth/reset_password.html', token=token)

        if len(password) < 6:
            flash('Password must be at least 6 characters long', 'error')
            return render_template('auth/reset_password.html', token=token)

        # Reset password
        user.set_password(password)
        user.email_verification_token = None
        user.email_verification_sent_at = None
        db.session.commit()

        flash('Password reset successful! You can now log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/reset_password.html', token=token)
