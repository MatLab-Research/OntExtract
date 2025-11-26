# Upload Agent Documents - OntExtract Document Upload Agent

Specialized agent for uploading the 7 "agent" semantic evolution source documents with proper metadata, text extraction, and processing.

## Agent Purpose

This agent programmatically uploads source documents for the "agent" temporal evolution experiment, ensuring:
1. Correct document type classification (always `document_type='document'`)
2. Complete metadata including all extended bibliographic fields (Session 30)
3. Pre-extracted and cleaned text content
4. Idempotent operation (skips documents that already exist)
5. Standalone document creation (no experiment association yet)

## Prerequisites

**Environment**: OntExtract
**Database**: ontextract_db (PostgreSQL)
**Source Directory**: `/home/chris/onto/OntExtract/experiments/documents/`
**Preprocessed Directory**: `/home/chris/onto/OntExtract/experiments/documents/preprocessed/`
**User**: demo (user_id: 10)
**Virtual Environment**: `venv-ontextract`

## Source Documents

| # | Filename | Year | Domain | Type |
|---|----------|------|--------|------|
| 1 | Henry Campbell Black - 1910 - Blacks Law Agent 1910.pdf | 1910 | Law | Dictionary |
| 2 | Anscombe - 1956 - Intention.pdf | 1956 | Philosophy | Journal Article |
| 3 | Wooldridge and Jennings - 1995 - Intelligent agents theory and practice.pdf | 1995 | AI/CS | Journal Article |
| 4 | Blacks Law 2019 Agent.pdf | 2019 | Law | Dictionary |
| 5 | Russell and Norvig - 2022 - Intelligent Agents.pdf | 2022 | AI/CS | Book Chapter |
| 6 | Brian A. Garner - 2024 - Blacks Law Agent 2024.pdf | 2024 | Law | Dictionary |
| 7 | agent, n.1 & adj..pdf | 2024 | Lexicography | OED Entry |

## Two-Stage Workflow

### Stage 1: Preprocessing (Run Once)

The preprocessing script extracts text from PDFs and saves cleaned content with metadata as JSON files.

```bash
cd /home/chris/onto/OntExtract
source venv-ontextract/bin/activate
python scripts/preprocess_experiment_documents.py
```

**Output**: Creates 7 JSON files in `experiments/documents/preprocessed/`:
- `blacks_law_1910.json`
- `anscombe_1956.json`
- `wooldridge_jennings_1995.json`
- `blacks_law_2019.json`
- `russell_norvig_2022.json`
- `blacks_law_2024.json`
- `oed_agent_2024.json`

Each JSON file contains:
```json
{
  "metadata": {
    "original_filename": "...",
    "title": "...",
    "authors": "...",
    "publication_date": "YYYY-MM-DD",
    "document_type": "document",
    "detected_language": "en",
    "language_confidence": 0.98,
    "container_title": "...",
    "edition": "...",
    "publisher": "...",
    "place": "...",
    "pages": "...",
    "isbn": "...",
    "doi": "...",
    "entry_term": "...",
    "notes": "..."
  },
  "content": "...(cleaned text)...",
  "preprocessing": {
    "extracted_chars": 16286,
    "cleaned_chars": 16280,
    "source_file": "/path/to/pdf"
  }
}
```

### Stage 2: Upload (Run As Needed)

The upload script reads preprocessed JSON files and creates Document records.

```bash
cd /home/chris/onto/OntExtract
source venv-ontextract/bin/activate
python scripts/upload_experiment_documents.py
```

**Behavior**:
- Checks if document already exists (by `original_filename`)
- Skips existing documents
- Creates new Document records with all metadata
- Uses demo user (id=10) as owner
- Sets `status='uploaded'`
- Sets `source_metadata.upload_source='system'`

## Extended Bibliographic Fields

The upload includes all Session 30 extended fields:

| Field | Example |
|-------|---------|
| `title` | Agent (Black's Law Dictionary, 11th ed.) |
| `authors` | Bryan A. Garner |
| `publication_date` | 2019-01-01 |
| `container_title` | Black's Law Dictionary |
| `editor` | Bryan A. Garner |
| `edition` | 11th |
| `publisher` | Thomson Reuters |
| `place` | St. Paul, MN |
| `volume` | 10 |
| `issue` | 2 |
| `pages` | 115-152 |
| `isbn` | 978-1539229735 |
| `issn` | (for journals) |
| `doi` | 10.1017/S0269888900007797 |
| `url` | https://www.oed.com/view/Entry/3851 |
| `access_date` | 2024-10-09 |
| `journal` | The Knowledge Engineering Review |
| `abstract` | (for academic papers) |
| `entry_term` | agent |
| `notes` | Definition entry for "agent" from legal dictionary |

## Verification

After upload, verify documents in database:

```sql
-- Check all uploaded documents
SELECT id, title, authors, publication_date, status, entry_term
FROM documents
WHERE user_id = 10
  AND original_filename LIKE '%Agent%' OR original_filename LIKE '%agent%'
ORDER BY publication_date;

-- Check extended metadata
SELECT id, title, container_title, edition, publisher, place
FROM documents
WHERE user_id = 10
  AND container_title IS NOT NULL
ORDER BY publication_date;

-- Verify content extraction
SELECT id, title, LENGTH(content) as content_length, detected_language
FROM documents
WHERE user_id = 10
ORDER BY publication_date;
```

## Expected Results

**Success Criteria**:
- 7 documents uploaded with correct metadata
- All extended bibliographic fields populated where applicable
- Text content present for all documents
- `document_type='document'` (not 'reference')
- `status='uploaded'`
- `source_metadata.upload_source='system'`
- Documents accessible via web interface at `/input/documents`

## Troubleshooting

**Issue**: Preprocessing fails
- Check PDF exists: `ls -la experiments/documents/*.pdf`
- Check pdftotext works: `pdftotext "file.pdf" -`
- Check permissions: `ls -la experiments/documents/preprocessed/`

**Issue**: Upload fails with user not found
- Verify demo user exists: `SELECT * FROM users WHERE id = 10;`
- Create demo user if missing via admin interface

**Issue**: Document already exists
- This is expected behavior for idempotency
- To re-upload: Delete existing document first
- Or modify script to update instead of skip

**Issue**: Missing metadata
- Check preprocessed JSON file has all fields
- Run preprocessing again if needed
- Manually edit JSON file if necessary

## Files

| File | Purpose |
|------|---------|
| `scripts/preprocess_experiment_documents.py` | Extract text from PDFs, save as JSON |
| `scripts/upload_experiment_documents.py` | Create Document records from JSON |
| `experiments/documents/*.pdf` | Source PDF files |
| `experiments/documents/preprocessed/*.json` | Preprocessed text + metadata |
| `experiments/documents/DOCUMENT_METADATA.txt` | Human-readable metadata reference |

## Future Improvements

1. **Path A Implementation**: Add HTTP POST to `/upload/document` endpoint to test full upload flow
2. **LLM Cleanup Integration**: Tag content with LLM cleanup metadata when that feature is added
3. **Provenance Source Types**: Distinguish 'system', 'manual', 'user' upload sources
4. **Semantic Scholar Integration**: Auto-fetch metadata for academic papers

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0 | 2025-11-26 | Rewritten with two-stage workflow, extended bibliographic fields |
| 1.0 | 2025-11-23 | Initial version with direct ORM upload |

**Maintained By**: Project team
