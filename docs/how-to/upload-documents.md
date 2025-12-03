# How to Upload Documents

This guide covers uploading historical documents to OntExtract for analysis.

## Overview

Documents are the foundation of temporal evolution analysis. OntExtract supports various document formats and captures metadata essential for period-aware processing.

## Supported Formats

- **PDF** - Scanned or digital PDFs (OCR extracted automatically)
- **Plain Text** (.txt) - Raw text files
- **Word Documents** (.docx) - Microsoft Word format
- **HTML** - Web pages with text content

## Upload Methods

### Method 1: Single Document Upload

1. Navigate to **Documents** in the main menu
2. Click **Upload Document**
3. Select or drag-and-drop your file
4. Fill in the metadata form:
   - **Title** - Document title (required)
   - **Author** - Primary author name
   - **Publication Date** - When the document was published (important for temporal analysis)
   - **Source** - Where the document came from (journal, book, archive)
   - **File Type** - Auto-detected, can be overridden
5. Click **Upload**

### Method 2: Upload via Experiment

When creating or editing an experiment:

1. Go to **Experiments** > Select your experiment
2. Click **Document Pipeline**
3. Use the **Add Documents** section
4. Upload documents directly to the experiment

## Document Metadata

### Required Fields

| Field | Description |
|-------|-------------|
| Title | Document title for identification |
| Content | The actual text content (extracted automatically from uploads) |

### Recommended Fields

| Field | Description | Why It Matters |
|-------|-------------|----------------|
| Publication Date | Year/date of publication | Determines temporal period assignment |
| Author | Document author(s) | Attribution and provenance |
| Source | Publication venue | Academic context |
| Chapter/Section | Location within larger work | Fine-grained citation |

### Publication Date Formats

OntExtract accepts various date formats:
- **Year only**: `1910`, `1856`
- **Month and year**: `March 1910`, `1910-03`
- **Full date**: `1910-03-15`, `March 15, 1910`

The system extracts the year for temporal period assignment.

## After Upload

Once uploaded, documents appear in:

1. **Documents list** - All uploaded documents
2. **Experiment documents** - If uploaded to an experiment

### Processing Options

After upload, you can process documents with:

- **LLM Text Cleanup** - Fix OCR errors, formatting issues (recommended for scanned documents)
- **Segmentation** - Split into paragraphs or sentences
- **Embeddings** - Generate vector representations for similarity search
- **Entity Extraction** - Identify named entities and concepts

## Tips for Historical Documents

### OCR Quality

Scanned historical documents often have OCR errors. Use the **LLM Text Cleanup** feature to:
- Fix character recognition mistakes (rn → m, l → I)
- Correct archaic spelling normalization
- Remove scanning artifacts (headers, page numbers)

### Temporal Periods

Documents are automatically assigned to temporal periods based on publication date. For an experiment tracking 1910-2024:
- A document from 1910 goes in the earliest period
- A document from 2020 goes in the latest period

### Batch Processing

For multiple documents:
1. Upload all documents first
2. Use the **Document Pipeline** view for batch operations
3. Run LLM cleanup on documents that need it
4. Process remaining operations in batch

## Troubleshooting

### Upload Fails

- Check file size (max 50MB default)
- Verify file format is supported
- Ensure you're logged in

### No Text Extracted

- PDF may be image-only (scanned without OCR)
- Try re-uploading with a different format
- Contact administrator if OCR service is unavailable

### Wrong Publication Date

- Edit the document metadata after upload
- Go to **Documents** > Select document > **Edit**

## Related Guides

- [Creating Temporal Experiments](create-temporal-experiment.md)
- [Creating Anchor Terms](create-anchor-terms.md)
- [Document Processing Pipeline](document-processing.md)
