"""Fix prov_relationships type constraints to accept both cases

The initial migration created check constraints for subject_type and object_type
that only accepted capitalized values ('Agent', 'Activity', 'Entity'). The code
uses lowercase values ('agent', 'activity', 'entity'). This migration updates
the constraints to accept both cases for backward compatibility.

Revision ID: 20251207_fix_case
Revises: 8ab4b2ec15be
Create Date: 2025-12-07
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20251207_fix_case'
down_revision = '8ab4b2ec15be'
branch_labels = None
depends_on = None


def upgrade():
    # Drop existing constraints
    op.drop_constraint('prov_relationships_object_type_check', 'prov_relationships', type_='check')
    op.drop_constraint('prov_relationships_subject_type_check', 'prov_relationships', type_='check')

    # Recreate constraints accepting both lowercase and capitalized values
    op.create_check_constraint(
        'prov_relationships_object_type_check',
        'prov_relationships',
        "object_type IN ('entity', 'activity', 'agent', 'Entity', 'Activity', 'Agent')"
    )
    op.create_check_constraint(
        'prov_relationships_subject_type_check',
        'prov_relationships',
        "subject_type IN ('entity', 'activity', 'agent', 'Entity', 'Activity', 'Agent')"
    )


def downgrade():
    # Revert to original constraints (capitalized only)
    op.drop_constraint('prov_relationships_object_type_check', 'prov_relationships', type_='check')
    op.drop_constraint('prov_relationships_subject_type_check', 'prov_relationships', type_='check')

    op.create_check_constraint(
        'prov_relationships_object_type_check',
        'prov_relationships',
        "object_type::text = ANY (ARRAY['Agent'::character varying, 'Activity'::character varying, 'Entity'::character varying]::text[])"
    )
    op.create_check_constraint(
        'prov_relationships_subject_type_check',
        'prov_relationships',
        "subject_type::text = ANY (ARRAY['Agent'::character varying, 'Activity'::character varying, 'Entity'::character varying]::text[])"
    )
