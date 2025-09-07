#!/usr/bin/env python3

from app import create_app, db

app = create_app()

with app.app_context():
    try:
        from sqlalchemy import text
        
        # Drop and recreate the constraint
        with db.engine.connect() as conn:
            conn.execute(text("ALTER TABLE documents DROP CONSTRAINT check_version_type"))
            print("Dropped old constraint")
            
            conn.execute(text("ALTER TABLE documents ADD CONSTRAINT check_version_type CHECK (version_type IN ('original', 'processed', 'experimental', 'composite'))"))
            print("Added new constraint with 'composite' support")
            
            conn.commit()
        
        print("SUCCESS: Database constraint updated")
        
    except Exception as e:
        print(f"ERROR: {e}")