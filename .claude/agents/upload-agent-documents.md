# Upload Agent Documents - OntExtract Document Upload Agent

Specialized agent for uploading the 7 "agent" semantic evolution source documents with proper metadata, text extraction, and processing.

## Agent Purpose

This agent programmatically uploads source documents for the "agent" temporal evolution experiment, ensuring:
1. Correct document type classification (dictionary, article, book_chapter)
2. Complete metadata (title, authors, dates, domains, chapter info)
3. Full text extraction from PDFs
4. Document processing through normal OntExtract workflow
5. Standalone document creation (no experiment association yet)

## Prerequisites

**Environment**: OntExtract
**Database**: ontextract_db (PostgreSQL)
**Source Directory**: /home/chris/onto/OntExtract/experiments/documents/source_documents/
**User**: demo (user_id: 10)
**Required Tools**: Python, psycopg2, pypdf/pdftotext

## Source Documents

| # | Filename | Year | Domain | Type | Chapter Info |
|---|----------|------|--------|------|--------------|
| 1 | agent, n.¹ & adj..pdf | Historical | Lexicography | dictionary | Full OED entry |
| 2 | Henry Campbell Black - 1910 - Blacks Law Agent 1910.pdf | 1910 | Law | dictionary | Definition excerpt |
| 3 | Anscombe - 1956 - Intention.pdf | 1956 | Philosophy | book_chapter | Chapter from "Intention" |
| 4 | Wooldridge and Jennings - 1995 - Intelligent agents theory and practice.pdf | 1995 | AI/CS | article | Full paper |
| 5 | Blacks Law 2019 Agent.pdf | 2019 | Law | dictionary | 11th ed. definition |
| 6 | Russell and Norvig - 2022 - Intelligent Agents.pdf | 2022 | AI/CS | book_chapter | Ch 2 from AI: A Modern Approach |
| 7 | Brian A. Garner - 2024 - Blacks Law Agent 2024.pdf | 2024 | Law | dictionary | 12th ed. definition |

## Document Upload Workflow

### Step 1: Import Required Modules

```python
import os
import sys
from datetime import datetime
from pathlib import Path

# Add OntExtract to path
sys.path.insert(0, '/home/chris/onto/OntExtract')

from app import create_app, db
from app.models.document import Document
from app.utils.file_handler import FileHandler
from app.services.text_processing import TextProcessingService

app = create_app()
app.app_context().push()
```

### Step 2: Define Document Metadata

```python
DOCUMENTS_METADATA = [
    {
        'filename': 'agent, n.¹ & adj..pdf',
        'title': 'Agent (Oxford English Dictionary)',
        'authors': 'Oxford English Dictionary',
        'publication_date': '2024-01-01',  # OED is continuously updated
        'domain': 'Lexicography',
        'document_type': 'dictionary',
        'description': 'Full OED entry for "agent" with historical quotations',
        'chapter_info': None
    },
    {
        'filename': 'Henry Campbell Black - 1910 - Blacks Law Agent 1910.pdf',
        'title': 'Agent (Black\'s Law Dictionary, 1st ed.)',
        'authors': 'Black, Henry Campbell',
        'publication_date': '1910-01-01',
        'domain': 'Law',
        'document_type': 'dictionary',
        'description': 'Legal definition of agent from first edition',
        'chapter_info': None
    },
    {
        'filename': 'Anscombe - 1956 - Intention.pdf',
        'title': 'Intention (Chapter)',
        'authors': 'Anscombe, G. E. M.',
        'publication_date': '1956-01-01',
        'domain': 'Philosophy',
        'document_type': 'book_chapter',
        'description': 'Philosophical analysis of intention and agency',
        'chapter_info': {
            'chapter_number': 'Introduction',
            'chapter_title': 'Intention',
            'source_book': 'Intention',
            'source_book_pages': '94'
        }
    },
    {
        'filename': 'Wooldridge and Jennings - 1995 - Intelligent agents theory and practice.pdf',
        'title': 'Intelligent Agents: Theory and Practice',
        'authors': 'Wooldridge, Michael; Jennings, Nicholas R.',
        'publication_date': '1995-01-01',
        'domain': 'AI/Computer Science',
        'document_type': 'article',
        'description': 'Foundational paper on intelligent agent theory',
        'chapter_info': None
    },
    {
        'filename': 'Blacks Law 2019 Agent.pdf',
        'title': 'Agent (Black\'s Law Dictionary, 11th ed.)',
        'authors': 'Garner, Bryan A.',
        'publication_date': '2019-01-01',
        'domain': 'Law',
        'document_type': 'dictionary',
        'description': 'Modern legal definition of agent',
        'chapter_info': None
    },
    {
        'filename': 'Russell and Norvig - 2022 - Intelligent Agents.pdf',
        'title': 'Intelligent Agents (Chapter 2)',
        'authors': 'Russell, Stuart; Norvig, Peter',
        'publication_date': '2022-01-01',
        'domain': 'AI/Computer Science',
        'document_type': 'book_chapter',
        'description': 'Modern AI agent theory from leading textbook',
        'chapter_info': {
            'chapter_number': '2',
            'chapter_title': 'Intelligent Agents',
            'source_book': 'Artificial Intelligence: A Modern Approach (4th ed.)',
            'source_book_pages': '1132'
        }
    },
    {
        'filename': 'Brian A. Garner - 2024 - Blacks Law Agent 2024.pdf',
        'title': 'Agent (Black\'s Law Dictionary, 12th ed.)',
        'authors': 'Garner, Bryan A.',
        'publication_date': '2024-01-01',
        'domain': 'Law',
        'document_type': 'dictionary',
        'description': 'Latest legal definition of agent',
        'chapter_info': None
    }
]
```

### Step 3: Upload and Process Each Document

```python
SOURCE_DIR = '/home/chris/onto/OntExtract/experiments/documents/source_documents'
USER_ID = 10  # demo user

file_handler = FileHandler()
processing_service = TextProcessingService()

uploaded_docs = []

for doc_meta in DOCUMENTS_METADATA:
    try:
        print(f"\nProcessing: {doc_meta['filename']}")

        # Full file path
        file_path = os.path.join(SOURCE_DIR, doc_meta['filename'])

        if not os.path.exists(file_path):
            print(f"  ERROR: File not found: {file_path}")
            continue

        # Extract text content using FileHandler
        content = file_handler.extract_text_from_file(file_path, doc_meta['filename'])

        if not content:
            print(f"  WARNING: No text extracted from {doc_meta['filename']}")
        else:
            print(f"  Extracted {len(content)} characters")

        # Build source_metadata with chapter info if applicable
        source_metadata = {
            'domain': doc_meta['domain'],
            'description': doc_meta['description']
        }

        if doc_meta['chapter_info']:
            source_metadata['chapter_metadata'] = doc_meta['chapter_info']

        # Create Document record
        # IMPORTANT: Use document_type='document' for source documents (not 'reference')
        # References are bibliographic entries; documents are source content for experiments
        document = Document(
            title=doc_meta['title'],
            content_type='file',
            document_type='document',  # Always 'document' for experiment sources
            reference_subtype=doc_meta.get('subtype'),  # Keep subtype for classification
            file_type='pdf',
            original_filename=doc_meta['filename'],
            file_path=file_path,
            file_size=os.path.getsize(file_path),
            content=content,
            authors=doc_meta['authors'],
            publication_date=datetime.strptime(doc_meta['publication_date'], '%Y-%m-%d').date(),
            detected_language='en',
            language_confidence=0.95,
            source_metadata=source_metadata,
            user_id=USER_ID,
            status='uploaded'
        )

        db.session.add(document)
        db.session.commit()

        print(f"  Created document ID: {document.id}")
        print(f"  UUID: {document.uuid}")

        # Process document through normal workflow
        try:
            processing_service.process_document(document)
            print(f"  Document processed successfully")
        except Exception as e:
            print(f"  WARNING: Processing failed: {str(e)}")

        uploaded_docs.append({
            'id': document.id,
            'uuid': document.uuid,
            'title': document.title,
            'type': document.document_type,
            'filename': doc_meta['filename']
        })

    except Exception as e:
        print(f"  ERROR: Failed to upload {doc_meta['filename']}: {str(e)}")
        import traceback
        traceback.print_exc()

# Summary
print("\n" + "="*80)
print("UPLOAD SUMMARY")
print("="*80)
print(f"Successfully uploaded: {len(uploaded_docs)}/{len(DOCUMENTS_METADATA)} documents")
print("\nDocument IDs:")
for doc in uploaded_docs:
    print(f"  [{doc['id']}] {doc['title']} ({doc['type']})")
print("\n")
```

### Step 4: Verification Queries

After upload, verify documents in database:

```sql
-- Check all uploaded documents
SELECT id, title, document_type, authors, publication_date,
       LENGTH(content) as content_length, status
FROM documents
WHERE user_id = 10
ORDER BY publication_date;

-- Check chapter metadata
SELECT id, title, document_type,
       source_metadata->'chapter_metadata'->>'chapter_number' as chapter_num,
       source_metadata->'chapter_metadata'->>'chapter_title' as chapter_title,
       source_metadata->'chapter_metadata'->>'source_book' as source_book
FROM documents
WHERE document_type = 'book_chapter'
AND user_id = 10;

-- Check text extraction success
SELECT title, document_type,
       CASE WHEN content IS NOT NULL THEN 'YES' ELSE 'NO' END as has_content,
       LENGTH(content) as content_length
FROM documents
WHERE user_id = 10
ORDER BY publication_date;
```

## Execution Instructions

1. **Create Python Script**: Save the upload code as `/home/chris/onto/OntExtract/scripts/upload_agent_documents.py`

2. **Run Script**:
   ```bash
   cd /home/chris/onto/OntExtract
   source venv-ontextract/bin/activate
   python scripts/upload_agent_documents.py
   ```

3. **Verify Upload**: Run SQL queries to confirm all 7 documents uploaded successfully

4. **Check Document Detail Pages**: Visit http://localhost:8765/input/documents to verify documents appear

## Expected Results

**Success Criteria**:
- ✅ All 7 documents uploaded with correct metadata
- ✅ Full text extracted from each PDF
- ✅ Chapter metadata present for Anscombe and Russell & Norvig
- ✅ Document types correctly classified
- ✅ Publication dates accurate
- ✅ All documents accessible via web interface
- ✅ Processing completed without errors

**Document IDs**: Will be auto-generated, track for experiment association later

## Troubleshooting

**Issue**: Text extraction fails
- Check PDF is not corrupted: `pdfinfo <file.pdf>`
- Verify file permissions: `ls -l <file.pdf>`
- Try manual extraction: `pdftotext <file.pdf> -`

**Issue**: Chapter metadata not saved
- Verify source_metadata is JSONB type in database
- Check chapter_info dictionary structure matches expected format

**Issue**: Import errors
- Ensure virtual environment activated
- Check PYTHONPATH includes OntExtract directory
- Verify all dependencies installed: `pip list | grep -i pdf`

## Maintenance Notes

**When to Update This Agent**:
- Adding new documents to the collection
- Changing document type classifications
- Updating chapter metadata format
- Fixing text extraction issues
- Modifying upload workflow in main application

**Version**: 1.0
**Last Updated**: 2025-11-23
**Maintained By**: Project team
