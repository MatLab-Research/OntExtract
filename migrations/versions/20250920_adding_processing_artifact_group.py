"""Add ProcessingArtifactGroup table and extend text_segments for multi-method processing

Revision ID: a7b9c2d4e5f6
Revises: f1a2b3c4d5e6
Create Date: 2025-09-20 20:05:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'a7b9c2d4e5f6'
down_revision = 'f1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Create processing_artifact_groups table
    op.create_table(
        'processing_artifact_groups',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('document_id', sa.Integer(), nullable=False, index=True),
        sa.Column('artifact_type', sa.String(length=40), nullable=False, index=True),
        sa.Column('method_key', sa.String(length=100), nullable=False),
        sa.Column('processing_job_id', sa.Integer(), nullable=True, index=True),
        sa.Column('parent_method_keys', postgresql.JSON(), nullable=True),
        sa.Column('metadata', postgresql.JSON(), nullable=True),
        sa.Column('include_in_composite', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('status', sa.String(length=20), nullable=False, server_default=sa.text("'completed'")),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ),
        sa.ForeignKeyConstraint(['processing_job_id'], ['processing_jobs.id'], ),
        sa.UniqueConstraint('document_id', 'artifact_type', 'method_key', name='uq_artifact_group_method')
    )
    op.create_index('ix_processing_artifact_groups_document', 'processing_artifact_groups', ['document_id'])
    op.create_index('ix_processing_artifact_groups_type', 'processing_artifact_groups', ['artifact_type'])
    op.create_index('ix_processing_artifact_groups_status', 'processing_artifact_groups', ['status'])

    # 2. Extend text_segments with processing_method and group_id
    op.add_column('text_segments', sa.Column('processing_method', sa.String(length=100), nullable=True))
    op.add_column('text_segments', sa.Column('group_id', sa.Integer(), nullable=True))
    op.create_index('ix_text_segments_processing_method', 'text_segments', ['processing_method'])
    op.create_index('ix_text_segments_group_id', 'text_segments', ['group_id'])
    op.create_foreign_key(None, 'text_segments', 'processing_artifact_groups', ['group_id'], ['id'])

    # 3. (Optional) Backfill existing segments with legacy method keys
    # NOTE: This raw SQL assumes legacy segments distinguished only by segment_type.
    op.execute("""
        UPDATE text_segments
        SET processing_method = CASE
            WHEN segment_type = 'sentence' THEN 'sentence_legacy'
            WHEN segment_type = 'paragraph' THEN 'paragraph_legacy'
            ELSE segment_type || '_legacy'
        END
        WHERE processing_method IS NULL;
    """)

    # 4. (Future) Potential artifact group creation for legacy data (left as guidance comment)
    # Example (pseudo-SQL): insert one artifact group per (document_id, processing_method) for segmentation
    # INSERT INTO processing_artifact_groups (document_id, artifact_type, method_key, include_in_composite)
    # SELECT DISTINCT document_id, 'segmentation', processing_method, true
    # FROM text_segments;


def downgrade():
    # Drop foreign key and indices
    op.drop_constraint(None, 'text_segments', type_='foreignkey')
    op.drop_index('ix_text_segments_group_id', table_name='text_segments')
    op.drop_index('ix_text_segments_processing_method', table_name='text_segments')
    op.drop_column('text_segments', 'group_id')
    op.drop_column('text_segments', 'processing_method')

    # Drop processing_artifact_groups table
    op.drop_index('ix_processing_artifact_groups_status', table_name='processing_artifact_groups')
    op.drop_index('ix_processing_artifact_groups_type', table_name='processing_artifact_groups')
    op.drop_index('ix_processing_artifact_groups_document', table_name='processing_artifact_groups')
    op.drop_table('processing_artifact_groups')
