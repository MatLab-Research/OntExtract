#!/usr/bin/env python3
"""
Upload documents for Agent Semantic Evolution experiment.

This script uploads the 7 required documents to experiment ID 30 in the correct order.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models.document import Document
from app.models.experiment import Experiment
from app.models.experiment_document import ExperimentDocument
from app.utils.file_handler import FileHandler
from app.services.text_processing import TextProcessingService
import shutil
from datetime import datetime

# Document specifications
DOCUMENTS = [
    {
        "order": 1,
        "filename": "AGENT 1910.pdf",
        "title": "Black's Law Dictionary 2nd Edition (1910) - Agent",
        "year": 1910,
        "discipline": "Law",
        "document_type": "reference",
        "reference_subtype": "legal_dictionary"
    },
    {
        "order": 2,
        "filename": "Anscombe-Intention-1956.pdf",
        "title": "Intention - G.E.M. Anscombe (1957)",
        "year": 1957,
        "discipline": "Philosophy",
        "document_type": "reference",
        "reference_subtype": "academic"
    },
    {
        "order": 3,
        "filename": "Wooldridge and Jennings - 1995 - Intelligent agents theory and practice.pdf",
        "title": "Intelligent Agents: Theory and Practice - Wooldridge & Jennings (1995)",
        "year": 1995,
        "discipline": "Artificial Intelligence",
        "document_type": "reference",
        "reference_subtype": "academic"
    },
    {
        "order": 4,
        "filename": "AGENT.pdf",
        "title": "Black's Law Dictionary 11th Edition (2019) - Agent",
        "year": 2019,
        "discipline": "Law",
        "document_type": "reference",
        "reference_subtype": "legal_dictionary"
    },
    {
        "order": 5,
        "filename": "Chapter 2 (Agents) Artificial Intelligence_ A Modern Approach-Prentice Hall (2020).pdf",
        "title": "Intelligent Agents - Russell & Norvig AI: A Modern Approach (2020)",
        "year": 2020,
        "discipline": "Artificial Intelligence",
        "document_type": "reference",
        "reference_subtype": "academic"
    },
    {
        "order": 6,
        "filename": "AGENT 2024.pdf",
        "title": "Black's Law Dictionary 12th Edition (2024) - Agent",
        "year": 2024,
        "discipline": "Law",
        "document_type": "reference",
        "reference_subtype": "legal_dictionary"
    },
    {
        "order": 7,
        "filename": "agent, n.¹ & adj. meanings, etymology and more _ Oxford English Dictionary.pdf",
        "title": "OED Entry: agent, n.¹ & adj. (2024)",
        "year": 2024,
        "discipline": "Lexicography",
        "document_type": "reference",
        "reference_subtype": "dictionary"
    }
]

EXPERIMENT_ID = 30
USER_ID = 1  # chris
SOURCE_DIR = "/home/chris/onto/OntExtract/docs/References"


def main():
    app = create_app()

    with app.app_context():
        # Verify experiment exists
        experiment = Experiment.query.get(EXPERIMENT_ID)
        if not experiment:
            print(f"ERROR: Experiment {EXPERIMENT_ID} not found!")
            return 1

        print(f"Uploading documents to experiment: {experiment.name}")
        print(f"Total documents to upload: {len(DOCUMENTS)}\n")

        file_handler = FileHandler()
        processing_service = TextProcessingService()
        upload_folder = app.config.get('UPLOAD_FOLDER', '/home/chris/onto/OntExtract/uploads')

        for doc_spec in DOCUMENTS:
            print(f"[{doc_spec['order']}/7] Processing: {doc_spec['title']}")

            # Find source file
            source_path = os.path.join(SOURCE_DIR, doc_spec['filename'])
            if not os.path.exists(source_path):
                print(f"  ERROR: File not found: {source_path}")
                continue

            # Get file size
            file_size = os.path.getsize(source_path)
            print(f"  File size: {file_size / 1024:.1f} KB")

            # Create unique filename for uploads folder
            import uuid
            unique_id = str(uuid.uuid4()).replace('-', '')[:16]
            file_ext = os.path.splitext(doc_spec['filename'])[1]
            upload_filename = f"{unique_id}_{doc_spec['filename']}"
            upload_path = os.path.join(upload_folder, upload_filename)

            # Copy file to uploads folder
            shutil.copy2(source_path, upload_path)
            print(f"  Copied to: {upload_path}")

            # Extract text content
            print(f"  Extracting text content...")
            content = file_handler.extract_text_from_file(upload_path, doc_spec['filename'])
            word_count = len(content.split()) if content else 0
            char_count = len(content) if content else 0
            print(f"  Extracted: {word_count} words, {char_count} characters")

            # Create document record
            document = Document(
                title=doc_spec['title'],
                content_type='file',
                document_type=doc_spec['document_type'],
                reference_subtype=doc_spec['reference_subtype'],
                file_type=file_ext[1:] if file_ext else 'pdf',
                original_filename=doc_spec['filename'],
                file_path=upload_path,
                file_size=file_size,
                content=content,
                content_preview=content[:500] if content else None,
                detected_language='en',
                language_confidence=0.9,
                source_metadata={
                    'year': doc_spec['year'],
                    'discipline': doc_spec['discipline'],
                    'upload_order': doc_spec['order']
                },
                word_count=word_count,
                character_count=char_count,
                user_id=USER_ID,
                status='uploaded',
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )

            db.session.add(document)
            db.session.flush()  # Get document ID

            print(f"  Created document ID: {document.id}")

            # Link to experiment
            experiment_doc = ExperimentDocument(
                experiment_id=EXPERIMENT_ID,
                document_id=document.id
            )
            db.session.add(experiment_doc)

            print(f"  Linked to experiment")

            # Commit after each document
            db.session.commit()
            print(f"  ✓ Document {doc_spec['order']} uploaded successfully\n")

        print(f"\n{'='*60}")
        print(f"SUCCESS: All {len(DOCUMENTS)} documents uploaded!")
        print(f"Experiment ID: {EXPERIMENT_ID}")
        print(f"Experiment: {experiment.name}")
        print(f"{'='*60}\n")

        return 0


if __name__ == '__main__':
    sys.exit(main())
