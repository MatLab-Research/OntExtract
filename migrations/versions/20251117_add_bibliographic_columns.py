"""Add normalized bibliographic metadata columns to documents table

Revision ID: 20251117_bibliographic_columns
Revises: 20251117_auth_system_enhancement
Create Date: 2025-11-17

This migration implements a hybrid metadata approach:
- Standard bibliographic fields as indexed columns (better performance, validation)
- Flexible custom metadata retained in source_metadata JSONB field
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = '20251117_bibliographic_columns'
down_revision = '20251117_auth_system_enhancement'
branch_labels = None
depends_on = None


def upgrade():
    """Add bibliographic metadata columns to documents table"""

    # Add standard bibliographic metadata columns
    op.add_column('documents', sa.Column('authors', sa.Text, nullable=True))
    op.add_column('documents', sa.Column('publication_date', sa.Date, nullable=True))
    op.add_column('documents', sa.Column('journal', sa.String(200), nullable=True))
    op.add_column('documents', sa.Column('publisher', sa.String(200), nullable=True))
    op.add_column('documents', sa.Column('doi', sa.String(100), nullable=True))
    op.add_column('documents', sa.Column('isbn', sa.String(20), nullable=True))
    op.add_column('documents', sa.Column('document_subtype', sa.String(50), nullable=True))  # article, book, etc.
    op.add_column('documents', sa.Column('abstract', sa.Text, nullable=True))
    op.add_column('documents', sa.Column('url', sa.String(500), nullable=True))
    op.add_column('documents', sa.Column('citation', sa.Text, nullable=True))

    # Create indexes for common queries
    op.create_index('ix_documents_doi', 'documents', ['doi'], unique=True)
    op.create_index('ix_documents_isbn', 'documents', ['isbn'])
    op.create_index('ix_documents_publication_date', 'documents', ['publication_date'])
    op.create_index('ix_documents_journal', 'documents', ['journal'])

    # Change source_metadata from JSON to JSONB for better performance
    # (PostgreSQL specific - provides indexing and better query support)
    op.execute("ALTER TABLE documents ALTER COLUMN source_metadata TYPE JSONB USING source_metadata::jsonb")


def downgrade():
    """Remove bibliographic metadata columns from documents table"""

    # Drop indexes
    op.drop_index('ix_documents_journal', table_name='documents')
    op.drop_index('ix_documents_publication_date', table_name='documents')
    op.drop_index('ix_documents_isbn', table_name='documents')
    op.drop_index('ix_documents_doi', table_name='documents')

    # Drop columns
    op.drop_column('documents', 'citation')
    op.drop_column('documents', 'url')
    op.drop_column('documents', 'abstract')
    op.drop_column('documents', 'document_subtype')
    op.drop_column('documents', 'isbn')
    op.drop_column('documents', 'doi')
    op.drop_column('documents', 'publisher')
    op.drop_column('documents', 'journal')
    op.drop_column('documents', 'publication_date')
    op.drop_column('documents', 'authors')

    # Revert source_metadata back to JSON
    op.execute("ALTER TABLE documents ALTER COLUMN source_metadata TYPE JSON USING source_metadata::json")
