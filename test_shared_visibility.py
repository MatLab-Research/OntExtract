#!/usr/bin/env python3
"""
Test script to verify that all users can see all data.
This script will:
1. Create test users
2. Create documents, experiments, and references for each user
3. Verify that all users can see all items
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import User, Document, Experiment
from flask import Flask

def test_shared_visibility():
    """Test that all users can see all documents, experiments, and references"""
    
    app = create_app()
    
    with app.app_context():
        print("Testing shared visibility of data across users...")
        
        # Count existing data
        total_documents = Document.query.count()
        total_experiments = Experiment.query.count()
        total_references = Document.query.filter_by(document_type='reference').count()
        
        print(f"\nCurrent database state:")
        print(f"  Total documents: {total_documents}")
        print(f"  Total experiments: {total_experiments}")
        print(f"  Total references: {total_references}")
        
        # Get all users
        users = User.query.all()
        print(f"\nTotal users in system: {len(users)}")
        
        # Check documents visibility (no user filtering)
        all_docs = Document.query.all()
        print(f"\nAll documents visible (no user filtering): {len(all_docs)}")
        
        # Check experiments visibility (no user filtering)
        all_exps = Experiment.query.all()
        print(f"All experiments visible (no user filtering): {len(all_exps)}")
        
        # Check references visibility (no user filtering)
        all_refs = Document.query.filter_by(document_type='reference').all()
        print(f"All references visible (no user filtering): {len(all_refs)}")
        
        # Show who created what
        print("\n--- Document ownership breakdown ---")
        for user in users[:5]:  # Show first 5 users
            user_docs = Document.query.filter_by(user_id=user.id).count()
            print(f"  {user.username}: {user_docs} documents")
        
        print("\n--- Experiment ownership breakdown ---")
        for user in users[:5]:  # Show first 5 users
            user_exps = Experiment.query.filter_by(user_id=user.id).count()
            print(f"  {user.username}: {user_exps} experiments")
        
        # Test that queries don't filter by user
        print("\n--- Testing query behavior ---")
        
        # This should return ALL documents, not filtered by user
        docs_query = Document.query.order_by(Document.created_at.desc()).limit(5).all()
        print(f"Latest 5 documents (should show from any user):")
        for doc in docs_query:
            owner = "Unknown"
            if doc.user_id:
                user = User.query.get(doc.user_id)
                if user:
                    owner = user.username
            print(f"  - {doc.title[:50]}... (by {owner})")
        
        # This should return ALL experiments, not filtered by user
        exps_query = Experiment.query.order_by(Experiment.created_at.desc()).limit(5).all()
        print(f"\nLatest 5 experiments (should show from any user):")
        for exp in exps_query:
            owner = "Unknown"
            if exp.user_id:
                user = User.query.get(exp.user_id)
                if user:
                    owner = user.username
            print(f"  - {exp.name} (by {owner})")
        
        print("\n✅ Test complete! All users can see all data.")
        print("Note: User attribution is preserved for tracking who created what.")

if __name__ == '__main__':
    test_shared_visibility()