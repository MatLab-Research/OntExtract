"""Add 'cleaned' to version_type constraint

Revision ID: 20251207_add_cleaned_version_type
Revises: 20251207_fix_prov_relationships_case_constraints
Create Date: 2025-12-07

Adds 'cleaned' as a valid version_type for documents.
This supports the LLM text cleanup workflow where cleaned versions
are created independently of experiments and can be used as the
source for experimental versions.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251207_add_cleaned_version_type'
down_revision = '20251207_fix_case'
branch_labels = None
depends_on = None


def upgrade():
    # Drop the existing constraint
    op.drop_constraint('check_version_type', 'documents', type_='check')

    # Add the new constraint with 'cleaned' included
    op.create_check_constraint(
        'check_version_type',
        'documents',
        "version_type IN ('original', 'processed', 'experimental', 'composite', 'cleaned')"
    )


def downgrade():
    # Drop the new constraint
    op.drop_constraint('check_version_type', 'documents', type_='check')

    # Restore the original constraint (without 'cleaned')
    op.create_check_constraint(
        'check_version_type',
        'documents',
        "version_type IN ('original', 'processed', 'experimental', 'composite')"
    )
