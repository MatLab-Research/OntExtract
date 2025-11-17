"""Add email verification and account status fields to users

Revision ID: 20251117_auth_system_enhancement
Revises: 20250920_adding_processing_artifact_group
Create Date: 2025-11-17

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic.
revision = '20251117_auth_system_enhancement'
down_revision = '20250920_adding_processing_artifact_group'
branch_labels = None
depends_on = None


def upgrade():
    """Add email verification and account status fields"""

    # Add new columns to users table
    op.add_column('users', sa.Column('account_status', sa.String(20), server_default='pending', nullable=False))
    op.add_column('users', sa.Column('email_verified', sa.Boolean, server_default='0', nullable=False))
    op.add_column('users', sa.Column('email_verification_token', sa.String(100), nullable=True))
    op.add_column('users', sa.Column('email_verification_sent_at', sa.DateTime, nullable=True))

    # Create index on email_verification_token for faster lookups
    op.create_index('ix_users_email_verification_token', 'users', ['email_verification_token'], unique=True)

    # Update existing users to have active status and verified email (grandfather them in)
    # First, update user 'chris' to be admin with verified email
    op.execute("""
        UPDATE users
        SET account_status='active',
            email_verified=1,
            is_admin=1
        WHERE username='chris'
    """)

    # Then set all other existing users to active with verified email
    op.execute("""
        UPDATE users
        SET account_status='active',
            email_verified=1
        WHERE username != 'chris'
    """)


def downgrade():
    """Remove email verification and account status fields"""

    # Drop index
    op.drop_index('ix_users_email_verification_token', table_name='users')

    # Drop columns
    op.drop_column('users', 'email_verification_sent_at')
    op.drop_column('users', 'email_verification_token')
    op.drop_column('users', 'email_verified')
    op.drop_column('users', 'account_status')
