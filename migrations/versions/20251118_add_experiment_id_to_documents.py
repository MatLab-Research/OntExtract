"""Add experiment_id column to documents table for experiment versioning

Revision ID: 20251118_experiment_versioning
Revises: 20251117_bibliographic_columns
Create Date: 2025-11-18

Part of: Experiment Versioning Refactor (Phase 1)
Purpose: Enable one version per experiment instead of version-per-operation
Tracking: docs/planning/EXPERIMENT_VERSIONING_REFACTOR.md
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251118_experiment_versioning'
down_revision = '20251117_bibliographic_columns'
branch_labels = None
depends_on = None


def upgrade():
    # Add experiment_id column to documents table
    # Nullable for now to allow existing documents without experiment association
    op.add_column('documents', sa.Column('experiment_id', sa.Integer(), nullable=True))

    # Add foreign key constraint to experiments table with CASCADE on delete
    op.create_foreign_key(
        'fk_documents_experiment_id',
        'documents',
        'experiments',
        ['experiment_id'],
        ['id'],
        ondelete='CASCADE'
    )

    # Create index for better query performance
    op.create_index(
        'idx_documents_experiment_id',
        'documents',
        ['experiment_id']
    )

    # Add check constraint: experimental versions must have experiment_id
    # This ensures data integrity for experiment-specific document versions
    op.create_check_constraint(
        'check_experimental_version_has_experiment',
        'documents',
        "version_type != 'experimental' OR (version_type = 'experimental' AND experiment_id IS NOT NULL)"
    )


def downgrade():
    # Remove check constraint
    op.drop_constraint('check_experimental_version_has_experiment', 'documents', type_='check')

    # Drop index
    op.drop_index('idx_documents_experiment_id', table_name='documents')

    # Drop foreign key
    op.drop_constraint('fk_documents_experiment_id', 'documents', type_='foreignkey')

    # Drop column
    op.drop_column('documents', 'experiment_id')
