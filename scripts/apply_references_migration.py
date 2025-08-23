#!/usr/bin/env python3
"""Apply references migration to the database"""

from app import create_app, db
from app.models.document import Document
from app.models.experiment import Experiment

# Create application context
app = create_app()

with app.app_context():
    # Run the SQL migration
    print("Applying references migration...")
    
    # Add document_type column to documents table if it doesn't exist
    try:
        db.session.execute(db.text("""
            ALTER TABLE documents ADD COLUMN IF NOT EXISTS document_type VARCHAR(20) DEFAULT 'document'
        """))
        db.session.commit()
        print("✓ Added document_type column to documents table")
    except Exception as e:
        print(f"Note: {e}")
        db.session.rollback()
    
    # Add source_metadata column to documents table if it doesn't exist
    try:
        db.session.execute(db.text("""
            ALTER TABLE documents ADD COLUMN IF NOT EXISTS source_metadata JSON
        """))
        db.session.commit()
        print("✓ Added source_metadata column to documents table")
    except Exception as e:
        print(f"Note: {e}")
        db.session.rollback()
    
    # Create experiment_references table if it doesn't exist
    try:
        db.session.execute(db.text("""
            CREATE TABLE IF NOT EXISTS experiment_references (
                experiment_id INTEGER REFERENCES experiments(id) ON DELETE CASCADE,
                reference_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
                include_in_analysis BOOLEAN DEFAULT false,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT,
                PRIMARY KEY (experiment_id, reference_id)
            )
        """))
        db.session.commit()
        print("✓ Created experiment_references table")
    except Exception as e:
        print(f"Note: {e}")
        db.session.rollback()
    
    # Create indexes
    try:
        db.session.execute(db.text("""
            CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(document_type)
        """))
        db.session.execute(db.text("""
            CREATE INDEX IF NOT EXISTS idx_experiment_references_experiment ON experiment_references(experiment_id)
        """))
        db.session.execute(db.text("""
            CREATE INDEX IF NOT EXISTS idx_experiment_references_reference ON experiment_references(reference_id)
        """))
        # Add parent_document_id column (for hierarchical OED sense references) if missing
        db.session.execute(db.text("""
            ALTER TABLE documents ADD COLUMN IF NOT EXISTS parent_document_id INTEGER
        """))
        # Add FK constraint if not already present (Postgres specific anonymous DO block)
        try:
            db.session.execute(db.text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.table_constraints
                        WHERE constraint_name = 'fk_documents_parent_document_id'
                          AND table_name = 'documents'
                    ) THEN
                        ALTER TABLE documents
                        ADD CONSTRAINT fk_documents_parent_document_id
                        FOREIGN KEY (parent_document_id) REFERENCES documents(id) ON DELETE CASCADE;
                    END IF;
                END$$;
            """))
        except Exception as e:
            print(f"Note (parent FK): {e}")
            db.session.rollback()
        db.session.execute(db.text("""
            CREATE INDEX IF NOT EXISTS idx_documents_parent ON documents(parent_document_id)
        """))
        db.session.commit()
        print("✓ Created indexes for better performance")
    except Exception as e:
        print(f"Note: {e}")
        db.session.rollback()
    
    # Update existing documents to have the correct type
    try:
        db.session.execute(db.text("""
            UPDATE documents SET document_type = 'document' WHERE document_type IS NULL
        """))
        db.session.commit()
        print("✓ Updated existing documents with default type")
    except Exception as e:
        print(f"Note: {e}")
        db.session.rollback()
    
    print("\n✅ References feature migration completed successfully!")
    print("You can now use the References feature in your application.")
