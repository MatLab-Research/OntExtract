"""fix app_settings unique constraint for user overrides

Revision ID: 8ab4b2ec15be
Revises: 20251125_extended_bibliographic
Create Date: 2025-12-04 12:23:40.758908

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = '8ab4b2ec15be'
down_revision = '20251125_extended_bibliographic'
branch_labels = None
depends_on = None


def upgrade():
    # Change setting_key from unique to non-unique
    # Add composite unique constraint on (setting_key, user_id)
    # This allows both system-wide (user_id=NULL) and user-specific settings with the same key
    conn = op.get_bind()
    inspector = inspect(conn)

    # Get existing indexes on app_settings
    indexes = inspector.get_indexes('app_settings')
    index_names = [idx['name'] for idx in indexes]

    # Get existing unique constraints
    unique_constraints = inspector.get_unique_constraints('app_settings')
    constraint_names = [uc['name'] for uc in unique_constraints]

    with op.batch_alter_table('app_settings', schema=None) as batch_op:
        # Only drop index if it exists
        if 'ix_app_settings_setting_key' in index_names:
            batch_op.drop_index('ix_app_settings_setting_key')
            batch_op.create_index(batch_op.f('ix_app_settings_setting_key'), ['setting_key'], unique=False)

        # Only create constraint if it doesn't exist
        if 'uq_setting_key_user_id' not in constraint_names:
            batch_op.create_unique_constraint('uq_setting_key_user_id', ['setting_key', 'user_id'])


def downgrade():
    with op.batch_alter_table('app_settings', schema=None) as batch_op:
        batch_op.drop_constraint('uq_setting_key_user_id', type_='unique')
        batch_op.drop_index(batch_op.f('ix_app_settings_setting_key'))
        batch_op.create_index('ix_app_settings_setting_key', ['setting_key'], unique=True)
