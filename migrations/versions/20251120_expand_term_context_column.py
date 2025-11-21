"""Expand term_context column from VARCHAR(200) to TEXT

Revision ID: 20251120_expand_term_context
Revises: 20251120_card_fields
Create Date: 2025-11-20 23:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20251120_expand_term_context'
down_revision = '20251120_card_fields'
branch_labels = None
depends_on = None


def upgrade():
    # Change term_context from VARCHAR(200) to TEXT to accommodate longer LLM responses
    op.alter_column('experiment_orchestration_runs', 'term_context',
                    existing_type=sa.VARCHAR(length=200),
                    type_=sa.Text(),
                    existing_nullable=True)


def downgrade():
    # Revert term_context back to VARCHAR(200)
    # WARNING: This may truncate data if any values exceed 200 characters
    op.alter_column('experiment_orchestration_runs', 'term_context',
                    existing_type=sa.Text(),
                    type_=sa.VARCHAR(length=200),
                    existing_nullable=True)
