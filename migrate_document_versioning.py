#!/usr/bin/env python3
"""
Database migration script to add document versioning support
Run this from the OntExtract directory: python migrate_document_versioning.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from sqlalchemy import text

def run_migration():
    app = create_app()
    
    with app.app_context():
        try:
            print("Starting document versioning migration...")
            
            # Add versioning fields to documents table
            migration_sql = [
                # Add new columns
                "ALTER TABLE documents ADD COLUMN IF NOT EXISTS version_number INTEGER DEFAULT 1;",
                "ALTER TABLE documents ADD COLUMN IF NOT EXISTS version_type VARCHAR(20) DEFAULT 'original';",
                "ALTER TABLE documents ADD COLUMN IF NOT EXISTS experiment_id INTEGER;",
                "ALTER TABLE documents ADD COLUMN IF NOT EXISTS source_document_id INTEGER;",
                "ALTER TABLE documents ADD COLUMN IF NOT EXISTS processing_notes TEXT;",
                
                # Add foreign key constraints
                """ALTER TABLE documents ADD CONSTRAINT IF NOT EXISTS fk_documents_experiment 
                   FOREIGN KEY (experiment_id) REFERENCES experiments(id) ON DELETE SET NULL;""",
                   
                """ALTER TABLE documents ADD CONSTRAINT IF NOT EXISTS fk_documents_source 
                   FOREIGN KEY (source_document_id) REFERENCES documents(id) ON DELETE CASCADE;""",
                
                # Create indexes for performance
                "CREATE INDEX IF NOT EXISTS idx_documents_version_number ON documents(version_number);",
                "CREATE INDEX IF NOT EXISTS idx_documents_version_type ON documents(version_type);",
                "CREATE INDEX IF NOT EXISTS idx_documents_experiment_id ON documents(experiment_id);",
                "CREATE INDEX IF NOT EXISTS idx_documents_source_document_id ON documents(source_document_id);",
                
                # Update existing documents to have proper version information
                """UPDATE documents 
                   SET version_number = 1, version_type = 'original' 
                   WHERE version_number IS NULL OR version_type IS NULL;""",
            ]
            
            # Execute each SQL statement
            for sql in migration_sql:
                print(f"Executing: {sql[:50]}...")
                try:
                    db.session.execute(text(sql))
                    db.session.commit()
                    print("✓ Success")
                except Exception as e:
                    print(f"✗ Error: {e}")
                    db.session.rollback()
                    # Continue with other statements
            
            # Create the view separately since it's more complex
            view_sql = """
            CREATE OR REPLACE VIEW document_version_chains AS
            SELECT 
                COALESCE(d.source_document_id, d.id) as root_document_id,
                d.id as document_id,
                d.title,
                d.version_number,
                d.version_type,
                d.experiment_id,
                d.created_at,
                d.status,
                e.name as experiment_name
            FROM documents d
            LEFT JOIN experiments e ON d.experiment_id = e.id
            ORDER BY COALESCE(d.source_document_id, d.id), d.version_number;
            """
            
            print("Creating document_version_chains view...")
            try:
                db.session.execute(text(view_sql))
                db.session.commit()
                print("✓ View created successfully")
            except Exception as e:
                print(f"✗ View creation error: {e}")
                db.session.rollback()
            
            print("\nMigration completed! Testing with a sample query...")
            
            # Test the migration
            test_query = "SELECT COUNT(*) as total_docs, version_type, COUNT(DISTINCT COALESCE(source_document_id, id)) as doc_families FROM documents GROUP BY version_type;"
            result = db.session.execute(text(test_query)).fetchall()
            
            print("Document versioning summary:")
            for row in result:
                print(f"  {row.version_type}: {row.total_docs} documents, {row.doc_families} families")
                
            print("\n✓ Document versioning migration completed successfully!")
            
        except Exception as e:
            print(f"Migration failed: {e}")
            db.session.rollback()
            return False
            
        return True

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)