"""Add experiment orchestration runs table

Revision ID: 20250104_orchestration
Revises: 20241221_experiment_centric
Create Date: 2025-01-04

This migration adds support for experiment-level orchestration where
an LLM recommends processing strategies across all documents in an experiment.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20250104_orchestration'
down_revision = '20241221_experiment_centric'
branch_labels = None
depends_on = None


def upgrade():
    # Create experiment_orchestration_runs table
    op.create_table('experiment_orchestration_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('experiment_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),

        # Timestamps
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),

        # Workflow status
        sa.Column('status', sa.String(length=50), nullable=False),  # analyzing, recommending, reviewing, executing, synthesizing, completed, failed
        sa.Column('current_stage', sa.String(length=50), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),

        # Stage 1: Experiment Understanding
        sa.Column('experiment_goal', sa.Text(), nullable=True),
        sa.Column('term_context', sa.String(length=200), nullable=True),  # Focus term if present

        # Stage 2: Strategy Recommendation
        sa.Column('recommended_strategy', postgresql.JSONB(astext_type=sa.Text()), nullable=True),  # {doc_id: [tools]}
        sa.Column('strategy_reasoning', sa.Text(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),

        # Stage 3: Human Review
        sa.Column('strategy_approved', sa.Boolean(), nullable=True, default=False),
        sa.Column('modified_strategy', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('review_notes', sa.Text(), nullable=True),
        sa.Column('reviewed_by', sa.Integer(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),

        # Stage 4: Execution
        sa.Column('processing_results', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('execution_trace', postgresql.JSONB(astext_type=sa.Text()), nullable=True),  # PROV-O provenance

        # Stage 5: Synthesis
        sa.Column('cross_document_insights', sa.Text(), nullable=True),
        sa.Column('term_evolution_analysis', sa.Text(), nullable=True),  # If focus term exists
        sa.Column('comparative_summary', sa.Text(), nullable=True),

        # Foreign keys
        sa.ForeignKeyConstraint(['experiment_id'], ['experiments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], ),

        sa.PrimaryKeyConstraint('id')
    )

    # Indexes for common queries
    op.create_index(op.f('ix_experiment_orchestration_runs_experiment_id'),
                    'experiment_orchestration_runs', ['experiment_id'], unique=False)
    op.create_index(op.f('ix_experiment_orchestration_runs_user_id'),
                    'experiment_orchestration_runs', ['user_id'], unique=False)
    op.create_index(op.f('ix_experiment_orchestration_runs_status'),
                    'experiment_orchestration_runs', ['status'], unique=False)
    op.create_index('idx_orchestration_lookup',
                    'experiment_orchestration_runs',
                    ['experiment_id', 'status', 'started_at'],
                    unique=False)


def downgrade():
    op.drop_index('idx_orchestration_lookup', table_name='experiment_orchestration_runs')
    op.drop_index(op.f('ix_experiment_orchestration_runs_status'), table_name='experiment_orchestration_runs')
    op.drop_index(op.f('ix_experiment_orchestration_runs_user_id'), table_name='experiment_orchestration_runs')
    op.drop_index(op.f('ix_experiment_orchestration_runs_experiment_id'), table_name='experiment_orchestration_runs')
    op.drop_table('experiment_orchestration_runs')
