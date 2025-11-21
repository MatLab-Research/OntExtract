"""Add generated card fields to ExperimentOrchestrationRun

Revision ID: 20251120_add_generated_card_fields
Revises: 20251118_experiment_versioning
Create Date: 2025-11-20 23:05:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251120_card_fields'
down_revision = '20251118_experiment_versioning'
branch_labels = None
depends_on = None


def upgrade():
    # Add new JSONB columns for structured card outputs
    op.add_column('experiment_orchestration_runs',
                  sa.Column('generated_term_cards', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('experiment_orchestration_runs',
                  sa.Column('generated_domain_cards', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('experiment_orchestration_runs',
                  sa.Column('generated_entity_cards', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade():
    # Remove the card columns
    op.drop_column('experiment_orchestration_runs', 'generated_entity_cards')
    op.drop_column('experiment_orchestration_runs', 'generated_domain_cards')
    op.drop_column('experiment_orchestration_runs', 'generated_term_cards')
