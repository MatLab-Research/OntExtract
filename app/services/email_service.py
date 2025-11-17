"""
Email Service for OntExtract

Handles sending verification emails, password resets, and other notifications.
"""

import secrets
from datetime import datetime, timedelta
from flask import url_for, render_template, current_app
from flask_mail import Message
from app import db, mail
import logging

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails"""

    @staticmethod
    def send_verification_email(user):
        """
        Send email verification link to user

        Args:
            user: User object to send verification email to

        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            # Generate secure token
            token = secrets.token_urlsafe(32)
            user.email_verification_token = token
            user.email_verification_sent_at = datetime.utcnow()
            db.session.commit()

            # Generate verification URL
            verification_url = url_for('auth.verify_email', token=token, _external=True)

            # Create email message
            msg = Message(
                subject='Verify your OntExtract email',
                recipients=[user.email],
                sender=current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@ontextract.com')
            )

            # Render HTML template
            msg.html = render_template('emails/verify_email.html',
                                      user=user,
                                      verification_url=verification_url)

            # Send email
            mail.send(msg)

            logger.info(f"Verification email sent to {user.email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send verification email to {user.email}: {e}")
            return False

    @staticmethod
    def send_password_reset_email(user, reset_token):
        """
        Send password reset link to user

        Args:
            user: User object
            reset_token: Password reset token

        Returns:
            bool: True if email sent successfully
        """
        try:
            reset_url = url_for('auth.reset_password', token=reset_token, _external=True)

            msg = Message(
                subject='Reset your OntExtract password',
                recipients=[user.email],
                sender=current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@ontextract.com')
            )

            msg.html = render_template('emails/reset_password.html',
                                      user=user,
                                      reset_url=reset_url)

            mail.send(msg)

            logger.info(f"Password reset email sent to {user.email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send password reset email to {user.email}: {e}")
            return False

    @staticmethod
    def send_admin_notification(subject, message, user=None):
        """
        Send notification to admin

        Args:
            subject: Email subject
            message: Email message
            user: Optional user object for context

        Returns:
            bool: True if email sent successfully
        """
        try:
            # Get admin email from config
            admin_email = current_app.config.get('ADMIN_EMAIL')
            if not admin_email:
                logger.warning("ADMIN_EMAIL not configured, skipping admin notification")
                return False

            msg = Message(
                subject=f"[OntExtract Admin] {subject}",
                recipients=[admin_email],
                sender=current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@ontextract.com')
            )

            msg.body = message
            if user:
                msg.body += f"\n\nUser: {user.username} ({user.email})"

            mail.send(msg)

            logger.info(f"Admin notification sent: {subject}")
            return True

        except Exception as e:
            logger.error(f"Failed to send admin notification: {e}")
            return False

    @staticmethod
    def is_token_expired(user, expiry_hours=24):
        """
        Check if verification token is expired

        Args:
            user: User object
            expiry_hours: Hours until token expires (default 24)

        Returns:
            bool: True if token is expired
        """
        if not user.email_verification_sent_at:
            return True

        expiry_time = user.email_verification_sent_at + timedelta(hours=expiry_hours)
        return datetime.utcnow() > expiry_time
