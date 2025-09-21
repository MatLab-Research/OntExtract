"""Experiment-centric processing architecture

Revision ID: 20241221_experiment_centric
Revises: a7b9c2d4e5f6
Create Date: 2024-12-21

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20241221_experiment_centric'
down_revision = 'a7b9c2d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    # Add term_id to experiments table
    op.add_column('experiments', sa.Column('term_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index(op.f('ix_experiments_term_id'), 'experiments', ['term_id'], unique=False)
    op.create_foreign_key('fk_experiments_term_id', 'experiments', 'terms', ['term_id'], ['id'])

    # Create experiment_document_processing table
    op.create_table('experiment_document_processing',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('experiment_document_id', sa.Integer(), nullable=False),
        sa.Column('processing_type', sa.String(length=50), nullable=False),
        sa.Column('processing_method', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('configuration_json', sa.Text(), nullable=True),
        sa.Column('results_summary_json', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['experiment_document_id'], ['experiment_documents_v2.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_experiment_document_processing_experiment_document_id'), 'experiment_document_processing', ['experiment_document_id'], unique=False)

    # Create processing_artifacts table
    op.create_table('processing_artifacts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('processing_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('artifact_type', sa.String(length=50), nullable=False),
        sa.Column('artifact_index', sa.Integer(), nullable=True),
        sa.Column('content_json', sa.Text(), nullable=True),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ),
        sa.ForeignKeyConstraint(['processing_id'], ['experiment_document_processing.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_processing_artifacts_document_id'), 'processing_artifacts', ['document_id'], unique=False)
    op.create_index(op.f('ix_processing_artifacts_processing_id'), 'processing_artifacts', ['processing_id'], unique=False)

    # Create document_processing_index table
    op.create_table('document_processing_index',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('experiment_id', sa.Integer(), nullable=False),
        sa.Column('processing_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('processing_type', sa.String(length=50), nullable=False),
        sa.Column('processing_method', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ),
        sa.ForeignKeyConstraint(['experiment_id'], ['experiments.id'], ),
        sa.ForeignKeyConstraint(['processing_id'], ['experiment_document_processing.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('document_id', 'processing_id', name='unique_doc_processing')
    )
    op.create_index('idx_document_processing_lookup', 'document_processing_index', ['document_id', 'processing_type', 'status'], unique=False)
    op.create_index(op.f('ix_document_processing_index_document_id'), 'document_processing_index', ['document_id'], unique=False)
    op.create_index(op.f('ix_document_processing_index_experiment_id'), 'document_processing_index', ['experiment_id'], unique=False)
    op.create_index(op.f('ix_document_processing_index_processing_id'), 'document_processing_index', ['processing_id'], unique=False)
    op.create_index(op.f('ix_document_processing_index_processing_type'), 'document_processing_index', ['processing_type'], unique=False)
    op.create_index(op.f('ix_document_processing_index_status'), 'document_processing_index', ['status'], unique=False)


def downgrade():
    # Drop new tables
    op.drop_table('document_processing_index')
    op.drop_table('processing_artifacts')
    op.drop_table('experiment_document_processing')

    # Remove term_id from experiments
    op.drop_constraint('fk_experiments_term_id', 'experiments', type_='foreignkey')
    op.drop_index(op.f('ix_experiments_term_id'), table_name='experiments')
    op.drop_column('experiments', 'term_id')