#!/usr/bin/env python3
"""
Data Migration: DocumentTemporalMetadata.publication_year → Document.publication_date

This script migrates existing publication year data from the deprecated
DocumentTemporalMetadata.publication_year field to the consolidated
Document.publication_date field.

Usage:
    PYTHONPATH=/home/chris/OntExtract venv-ontextract/bin/python migrations/migrate_publication_dates.py
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import Document
from app.models.temporal_experiment import DocumentTemporalMetadata
from app.utils.date_parser import parse_flexible_date
from datetime import date


def migrate_publication_dates(dry_run=False):
    """
    Migrate publication years from DocumentTemporalMetadata to Document.publication_date

    Args:
        dry_run: If True, show what would be migrated without making changes
    """
    app = create_app()

    with app.app_context():
        print("=" * 70)
        print("Publication Date Migration")
        print("From: DocumentTemporalMetadata.publication_year (deprecated)")
        print("To:   Document.publication_date (consolidated)")
        print("=" * 70)
        print()

        # Find all temporal metadata records with publication years
        temporal_records = DocumentTemporalMetadata.query.filter(
            DocumentTemporalMetadata.publication_year.isnot(None)
        ).all()

        print(f"Found {len(temporal_records)} records with publication years\n")

        if len(temporal_records) == 0:
            print("No data to migrate. Exiting.")
            return

        migrated_count = 0
        skipped_count = 0
        updated_count = 0

        for record in temporal_records:
            document = Document.query.get(record.document_id)

            if not document:
                print(f"⚠️  Warning: Document {record.document_id} not found, skipping")
                skipped_count += 1
                continue

            # Convert year to date (year-only format → YYYY-01-01)
            new_date = parse_flexible_date(record.publication_year)

            if not new_date:
                print(f"⚠️  Warning: Could not parse year {record.publication_year} for document {document.id}, skipping")
                skipped_count += 1
                continue

            # Check if document already has a publication_date
            if document.publication_date:
                existing_year = document.publication_date.year

                if existing_year == record.publication_year:
                    print(f"✓  Document {document.id}: Already has correct date ({existing_year}), skipping")
                    skipped_count += 1
                else:
                    print(f"⚠️  Document {document.id}: Has different date ({existing_year} vs {record.publication_year})")
                    print(f"    Keeping existing: {document.publication_date}")
                    skipped_count += 1
                continue

            # Migrate the data
            action = "[DRY RUN]" if dry_run else "✓"
            print(f"{action} Document {document.id} ({document.title[:50]}...)")
            print(f"    Setting publication_date: {new_date} (from year {record.publication_year})")

            if not dry_run:
                document.publication_date = new_date
                migrated_count += 1

        # Commit changes
        if not dry_run and migrated_count > 0:
            try:
                db.session.commit()
                print(f"\n✅ Successfully migrated {migrated_count} records")
            except Exception as e:
                db.session.rollback()
                print(f"\n❌ Error committing changes: {e}")
                return

        print()
        print("=" * 70)
        print("Migration Summary")
        print("=" * 70)
        print(f"Total records found:  {len(temporal_records)}")
        print(f"Migrated:            {migrated_count}")
        print(f"Skipped:             {skipped_count}")
        print()

        if dry_run:
            print("This was a DRY RUN. No changes were made.")
            print("Run again without dry_run=True to apply changes.")
        else:
            print("Migration complete!")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Migrate publication dates from temporal metadata to documents')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be migrated without making changes')

    args = parser.parse_args()

    migrate_publication_dates(dry_run=args.dry_run)
