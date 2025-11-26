"""Add extended bibliographic metadata columns (Zotero-aligned)

Revision ID: 20251125_extended_bibliographic
Revises: 20251120_expand_term_context_column
Create Date: 2025-11-25

This migration adds additional bibliographic fields aligned with Zotero's schema:
- editor: For reference works, edited volumes
- edition: Edition number/name
- volume, issue: Journal article identifiers
- pages: Page range in source
- container_title: Title of containing work (book, dictionary, anthology)
- place: Publication place
- series: Series name
- access_date: For online sources
- entry_term: Headword for dictionary/encyclopedia entries
- notes: General notes
- issn: Journal ISSN
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251125_extended_bibliographic'
down_revision = '20251120_expand_term_context'
branch_labels = None
depends_on = None


def upgrade():
    """Add extended bibliographic metadata columns to documents table"""

    # Core reference work fields
    op.add_column('documents', sa.Column('editor', sa.Text, nullable=True))
    op.add_column('documents', sa.Column('edition', sa.String(50), nullable=True))

    # Journal article fields
    op.add_column('documents', sa.Column('volume', sa.String(20), nullable=True))
    op.add_column('documents', sa.Column('issue', sa.String(20), nullable=True))
    op.add_column('documents', sa.Column('pages', sa.String(50), nullable=True))
    op.add_column('documents', sa.Column('issn', sa.String(20), nullable=True))

    # Book section / anthology fields
    op.add_column('documents', sa.Column('container_title', sa.String(300), nullable=True))
    op.add_column('documents', sa.Column('place', sa.String(100), nullable=True))
    op.add_column('documents', sa.Column('series', sa.String(200), nullable=True))

    # Dictionary / encyclopedia entry fields
    op.add_column('documents', sa.Column('entry_term', sa.String(200), nullable=True))
    op.add_column('documents', sa.Column('access_date', sa.Date, nullable=True))

    # General
    op.add_column('documents', sa.Column('notes', sa.Text, nullable=True))

    # Create indexes for commonly queried fields
    op.create_index('ix_documents_entry_term', 'documents', ['entry_term'])
    op.create_index('ix_documents_container_title', 'documents', ['container_title'])
    op.create_index('ix_documents_edition', 'documents', ['edition'])


def downgrade():
    """Remove extended bibliographic metadata columns from documents table"""

    # Drop indexes
    op.drop_index('ix_documents_edition', table_name='documents')
    op.drop_index('ix_documents_container_title', table_name='documents')
    op.drop_index('ix_documents_entry_term', table_name='documents')

    # Drop columns
    op.drop_column('documents', 'notes')
    op.drop_column('documents', 'access_date')
    op.drop_column('documents', 'entry_term')
    op.drop_column('documents', 'series')
    op.drop_column('documents', 'place')
    op.drop_column('documents', 'container_title')
    op.drop_column('documents', 'issn')
    op.drop_column('documents', 'pages')
    op.drop_column('documents', 'issue')
    op.drop_column('documents', 'volume')
    op.drop_column('documents', 'edition')
    op.drop_column('documents', 'editor')
