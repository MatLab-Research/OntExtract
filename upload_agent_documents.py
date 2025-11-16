#!/usr/bin/env python3
"""
Upload Agent Semantic Evolution Documents
Programmatically upload the 7 documents for the Agent experiment with proper metadata
"""

import os
import sys
from datetime import datetime

# Add the app to path
sys.path.insert(0, '/home/chris/OntExtract')

from app import create_app, db
from app.models import Document, User
from app.utils.file_handler import FileHandler
from sqlalchemy import text

# Document mapping with metadata
DOCUMENTS = [
    {
        'filename': 'AGENT 1910.pdf',
        'title': "Black's Law Dictionary 1910 - Agent",
        'year': 1910,
        'description': 'Legal definition of "agent" from Black\'s Law Dictionary, 1st Edition (1910)',
        'domain': 'law'
    },
    {
        'filename': 'anscombe_1957_intention.pdf',
        'title': 'Anscombe - Intention (1957)',
        'year': 1957,
        'description': 'Philosophical work on intentional action and agency by G.E.M. Anscombe',
        'domain': 'philosophy'
    },
    {
        'filename': 'Wooldridge and Jennings - 1995 - Intelligent agents theory and practice.pdf',
        'title': 'Wooldridge & Jennings - Intelligent Agents (1995)',
        'year': 1995,
        'description': 'Foundational AI paper on intelligent agent theory',
        'domain': 'computer_science'
    },
    {
        'filename': 'Chapter 2 (Agents) Artificial Intelligence_ A Modern Approach-Prentice Hall (2020).pdf',
        'title': 'Russell & Norvig - AI: A Modern Approach (2020) - Agents Chapter',
        'year': 2020,
        'description': 'Agent chapter from Artificial Intelligence: A Modern Approach, 4th Edition',
        'domain': 'computer_science'
    },
    {
        'filename': 'AGENT 2024.pdf',
        'title': "Black's Law Dictionary 2024 - Agent",
        'year': 2024,
        'description': 'Most recent legal definition of "agent" from Black\'s Law Dictionary',
        'domain': 'law'
    },
    {
        'filename': 'agent, n.¹ & adj. meanings, etymology and more _ Oxford English Dictionary.pdf',
        'title': 'Oxford English Dictionary 2024 - Agent',
        'year': 2024,
        'description': 'OED entry for "agent" with historical quotations and definitions',
        'domain': 'lexicography'
    },
    # Optional: Black's 2019 (we can skip if we have 1910 and 2024)
    # {
    #     'filename': 'BlacksAgentPortfolio.pdf',
    #     'title': "Black's Law Dictionary 2019 - Agent",
    #     'year': 2019,
    #     'description': 'Updated legal definition of "agent"',
    #     'domain': 'law'
    # },
]

SOURCE_DIR = '/home/chris/onto/OntExtract/docs/References/'

def upload_documents():
    """Upload all agent documents"""
    app = create_app()

    with app.app_context():
        # Get first user (should be the one we preserved)
        user = User.query.first()
        if not user:
            print("❌ No user found in database. Please create a user first.")
            return

        print(f"📤 Uploading documents as user: {user.username}")
        print(f"📁 Source directory: {SOURCE_DIR}")
        print(f"📊 Documents to upload: {len(DOCUMENTS)}")
        print("-" * 80)

        uploaded_docs = []
        file_handler = FileHandler()

        for i, doc_info in enumerate(DOCUMENTS, 1):
            filepath = os.path.join(SOURCE_DIR, doc_info['filename'])

            if not os.path.exists(filepath):
                print(f"⚠️  [{i}/{len(DOCUMENTS)}] SKIP: {doc_info['filename']} - File not found")
                continue

            print(f"\n📄 [{i}/{len(DOCUMENTS)}] Uploading: {doc_info['title']}")
            print(f"   File: {doc_info['filename']}")
            print(f"   Year: {doc_info['year']}")
            print(f"   Size: {os.path.getsize(filepath) / 1024:.1f} KB")

            try:
                # Extract text using FileHandler (works directly with file path)
                extracted_text = file_handler.extract_text_from_file(
                    filepath,
                    doc_info['filename']
                )

                if not extracted_text:
                    print(f"   ⚠️  Warning: No text extracted from PDF")
                    extracted_text = ""

                # Create document record
                document = Document(
                    title=doc_info['title'],
                    content=extracted_text[:50000],  # Limit content size
                    content_type='file',  # Required field: 'file' or 'text'
                    file_type='pdf',
                    document_type='document',  # Not 'reference' - these are source documents
                    user_id=user.id,
                    version_type='original',
                    version_number=1,
                    created_at=datetime.utcnow(),

                    # Temporal metadata (crucial for temporal evolution)
                    publication_year=doc_info['year'],

                    # Additional metadata
                    processing_notes=doc_info['description'],

                    # Store original filename
                    original_filename=doc_info['filename']
                )

                db.session.add(document)
                db.session.flush()  # Get the ID

                # Create temporal metadata record (crucial for temporal evolution experiments)
                from app.models import DocumentTemporalMetadata
                temporal_metadata = DocumentTemporalMetadata(
                    document_id=document.id,
                    publication_year=doc_info['year'],
                    discipline=doc_info.get('domain'),  # Store domain as discipline
                    key_definition=doc_info.get('description'),  # Store description as key definition
                    created_at=datetime.utcnow()
                )
                db.session.add(temporal_metadata)

                db.session.commit()

                uploaded_docs.append({
                    'id': document.id,
                    'title': document.title,
                    'year': doc_info['year'],
                    'filename': doc_info['filename']
                })

                print(f"   ✅ SUCCESS - Document ID: {document.id}")
                print(f"   Text extracted: {len(extracted_text)} characters")

            except Exception as e:
                db.session.rollback()
                print(f"   ❌ ERROR: {str(e)}")
                import traceback
                traceback.print_exc()
                continue

        print("\n" + "=" * 80)
        print("📊 UPLOAD SUMMARY")
        print("=" * 80)
        print(f"✅ Successfully uploaded: {len(uploaded_docs)}/{len(DOCUMENTS)} documents")
        print()

        if uploaded_docs:
            print("📋 Uploaded Documents:")
            print()
            for doc in uploaded_docs:
                print(f"  ID {doc['id']:3d} | {doc['year']} | {doc['title']}")

            print()
            print("=" * 80)
            print("NEXT STEPS:")
            print("=" * 80)
            print("1. Navigate to: http://localhost:8765/experiments/new")
            print("2. Select 'Temporal Evolution' type")
            print("3. Select focus term: 'agent'")
            print("4. Select these document IDs:")
            for doc in uploaded_docs:
                print(f"   - [{doc['id']}] {doc['title']}")
            print()
            print("Document IDs for easy copy/paste:")
            print(", ".join(str(doc['id']) for doc in uploaded_docs))
            print("=" * 80)

if __name__ == '__main__':
    upload_documents()
