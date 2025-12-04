"""fix app_settings unique constraint for user overrides

Revision ID: 8ab4b2ec15be
Revises: 20251125_extended_bibliographic
Create Date: 2025-12-04 12:23:40.758908

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '8ab4b2ec15be'
down_revision = '20251125_extended_bibliographic'
branch_labels = None
depends_on = None


def upgrade():
    # Change setting_key from unique to non-unique
    # Add composite unique constraint on (setting_key, user_id)
    # This allows both system-wide (user_id=NULL) and user-specific settings with the same key
    with op.batch_alter_table('app_settings', schema=None) as batch_op:
        batch_op.drop_index('ix_app_settings_setting_key')
        batch_op.create_index(batch_op.f('ix_app_settings_setting_key'), ['setting_key'], unique=False)
        batch_op.create_unique_constraint('uq_setting_key_user_id', ['setting_key', 'user_id'])


def downgrade():
    with op.batch_alter_table('app_settings', schema=None) as batch_op:
        batch_op.drop_constraint('uq_setting_key_user_id', type_='unique')
        batch_op.drop_index(batch_op.f('ix_app_settings_setting_key'))
        batch_op.create_index('ix_app_settings_setting_key', ['setting_key'], unique=True)
