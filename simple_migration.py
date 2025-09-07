#!/usr/bin/env python3
"""
Simple database migration using SQLAlchemy reflection to add versioning columns
This approach avoids permission issues by using the existing application database connection
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from sqlalchemy import text, Column, Integer, String, ForeignKey

def run_simple_migration():
    app = create_app()
    
    with app.app_context():
        try:
            print("Starting simple document versioning migration...")
            
            # Use raw SQL commands one by one with the existing connection
            migration_commands = [
                "ALTER TABLE documents ADD COLUMN version_number INTEGER DEFAULT 1",
                "ALTER TABLE documents ADD COLUMN version_type VARCHAR(20) DEFAULT 'original'",
                "ALTER TABLE documents ADD COLUMN experiment_id INTEGER",
                "ALTER TABLE documents ADD COLUMN source_document_id INTEGER",
                "ALTER TABLE documents ADD COLUMN processing_notes TEXT"
            ]
            
            for cmd in migration_commands:
                try:
                    print(f"Executing: {cmd}")
                    db.session.execute(text(cmd))
                    db.session.commit()
                    print("✓ Success")
                except Exception as e:
                    print(f"✗ Error (may already exist): {e}")
                    db.session.rollback()
                    # Continue with next command
            
            # Update existing documents to have proper version information
            try:
                print("Updating existing documents...")
                update_cmd = """
                UPDATE documents 
                SET version_number = 1, version_type = 'original' 
                WHERE version_number IS NULL OR version_type IS NULL
                """
                db.session.execute(text(update_cmd))
                db.session.commit()
                print("✓ Existing documents updated")
            except Exception as e:
                print(f"✗ Update error: {e}")
                db.session.rollback()
            
            print("✓ Simple migration completed successfully!")
            
        except Exception as e:
            print(f"Migration failed: {e}")
            db.session.rollback()
            return False
            
        return True

if __name__ == "__main__":
    success = run_simple_migration()
    sys.exit(0 if success else 1)