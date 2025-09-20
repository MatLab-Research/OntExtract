"""Add composite_sources and composite_metadata columns to documents table

Revision ID: f1a2b3c4d5e6
Revises: 526974d6041c
Create Date: 2025-09-20 17:50:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'f1a2b3c4d5e6'
down_revision = '526974d6041c'
branch_labels = None
depends_on = None


def upgrade():
    # Add composite_sources column
    op.add_column('documents', sa.Column('composite_sources', postgresql.JSONB(), nullable=True))
    # Add composite_metadata column
    op.add_column('documents', sa.Column('composite_metadata', postgresql.JSONB(), nullable=True))


def downgrade():
    # Remove composite_metadata column
    op.drop_column('documents', 'composite_metadata')
    # Remove composite_sources column
    op.drop_column('documents', 'composite_sources')