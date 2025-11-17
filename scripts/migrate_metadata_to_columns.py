#!/usr/bin/env python3
"""
Data migration: Move bibliographic metadata from JSONB to normalized columns

This script migrates existing source_metadata JSONB data to the new normalized
bibliographic columns added in migration 20251117_bibliographic_columns.

IMPORTANT: Run this AFTER applying the schema migration (flask db upgrade)

Usage:
    python scripts/migrate_metadata_to_columns.py [--dry-run]
"""

import sys
import os
from pathlib import Path
from datetime import datetime
from dateutil import parser as date_parser

# Add parent directory to path so we can import app
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app, db
from app.models.document import Document
from sqlalchemy.orm.attributes import flag_modified


def parse_date(date_str):
    """Parse date string to date object, handling various formats"""
    if not date_str:
        return None

    try:
        # Try parsing as YYYY-MM-DD or other ISO formats
        parsed = date_parser.parse(str(date_str))
        return parsed.date()
    except:
        try:
            # Try parsing as just year (YYYY)
            year = int(str(date_str)[:4])
            return datetime(year, 1, 1).date()
        except:
            return None


def migrate_metadata_to_columns(dry_run=False):
    """
    Migrate source_metadata JSONB fields to normalized columns.

    Args:
        dry_run: If True, only print what would be done without making changes
    """
    app = create_app()

    with app.app_context():
        # Find all documents with source_metadata
        documents = Document.query.filter(
            Document.source_metadata.isnot(None)
        ).all()

        print(f"Found {len(documents)} documents with source_metadata")

        migrated_count = 0
        skipped_count = 0

        for doc in documents:
            if not doc.source_metadata:
                skipped_count += 1
                continue

            meta = doc.source_metadata
            changes = {}

            # Map JSONB fields to column fields
            if 'authors' in meta and meta['authors']:
                # Handle both list and string formats
                if isinstance(meta['authors'], list):
                    changes['authors'] = ', '.join(meta['authors'])
                else:
                    changes['authors'] = str(meta['authors'])

            if 'publication_date' in meta and meta['publication_date']:
                parsed_date = parse_date(meta['publication_date'])
                if parsed_date:
                    changes['publication_date'] = parsed_date

            if 'journal' in meta and meta['journal']:
                changes['journal'] = str(meta['journal'])[:200]  # Truncate if needed

            if 'publisher' in meta and meta['publisher']:
                changes['publisher'] = str(meta['publisher'])[:200]

            if 'doi' in meta and meta['doi']:
                changes['doi'] = str(meta['doi'])[:100]

            if 'isbn' in meta and meta['isbn']:
                changes['isbn'] = str(meta['isbn'])[:20]

            if 'type' in meta and meta['type']:
                changes['document_subtype'] = str(meta['type'])[:50]

            if 'abstract' in meta and meta['abstract']:
                changes['abstract'] = str(meta['abstract'])

            if 'url' in meta and meta['url']:
                changes['url'] = str(meta['url'])[:500]

            if 'citation' in meta and meta['citation']:
                changes['citation'] = str(meta['citation'])

            # Also sync title from source_metadata if present
            if 'title' in meta and meta['title'] and meta['title'] != doc.title:
                changes['title'] = str(meta['title'])[:200]

            if not changes:
                skipped_count += 1
                continue

            if dry_run:
                print(f"\nWould migrate document {doc.id} ({doc.title}):")
                for field, value in changes.items():
                    display_value = str(value)[:50] + '...' if len(str(value)) > 50 else str(value)
                    print(f"  {field}: {display_value}")
            else:
                # Apply changes
                for field, value in changes.items():
                    setattr(doc, field, value)

                # Keep source_metadata for any non-standard fields
                # Remove standard fields that are now in columns
                standard_fields = {
                    'authors', 'publication_date', 'journal', 'publisher',
                    'doi', 'isbn', 'type', 'abstract', 'url', 'citation', 'title'
                }

                # Build new source_metadata with only non-standard fields
                new_source_metadata = {
                    k: v for k, v in meta.items()
                    if k not in standard_fields and v is not None
                }

                # Update source_metadata (keep it for custom fields)
                doc.source_metadata = new_source_metadata if new_source_metadata else None
                flag_modified(doc, 'source_metadata')

                migrated_count += 1

        if not dry_run and migrated_count > 0:
            try:
                db.session.commit()
                print(f"\nSuccessfully migrated {migrated_count} documents")
            except Exception as e:
                db.session.rollback()
                print(f"\nERROR during migration: {str(e)}")
                raise
        elif dry_run:
            print(f"\nDry run complete. Would migrate {migrated_count} documents")

        print(f"Skipped {skipped_count} documents (no metadata or no changes needed)")

        return migrated_count


if __name__ == '__main__':
    dry_run = '--dry-run' in sys.argv

    if dry_run:
        print("Running in DRY RUN mode - no changes will be made\n")
    else:
        print("WARNING: This will migrate source_metadata to normalized columns")
        print("Standard fields will be removed from source_metadata JSONB")
        print("Custom fields will be retained in source_metadata")
        response = input("Continue? (yes/no): ")
        if response.lower() != 'yes':
            print("Aborted")
            sys.exit(0)

    migrated = migrate_metadata_to_columns(dry_run=dry_run)

    if not dry_run and migrated > 0:
        print(f"\nMigration complete! {migrated} documents now have normalized bibliographic data")
        print("Standard fields are now in database columns for better performance")
        print("Custom metadata fields remain in source_metadata JSONB")
