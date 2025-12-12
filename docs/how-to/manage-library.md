# How to Manage the Library

This guide explains how to browse, search, and manage the document library in OntExtract.

## Overview

The **Library** section (accessible via **Library → Sources** in the navigation) serves as the central hub for managing all uploaded content. It displays both:

- **Documents** - Primary source materials for analysis (PDFs, text files, pasted content)
- **References** - Canonical reference materials like dictionary entries and academic papers

## Browsing Sources

### Access the Library

1. Click **Library** in the main navigation
2. Select **Sources** from the dropdown

### Filter by Type

Use the filter tabs at the top to show:

| Tab | Contents |
|-----|----------|
| **All** | Both documents and references |
| **Documents** | Primary source materials only |
| **References** | Reference documents only |

### Understanding the List View

Each source card displays:

- **Title** - Document name (clickable to view details)
- **Type badge** - Document or Reference
- **Version indicator** - Current version number
- **Bibliographic metadata** - Authors, publication date, journal, DOI (if available)
- **Content preview** - Abstract or first few lines of content

## Document Versions

OntExtract maintains version history for processed documents.

### Viewing Version History

1. If a document has multiple versions, click the **X versions** button on the card
2. The version list expands showing:
   - Version number
   - Version type (Original, Processed)
   - Creation timestamp

### Version Types

| Type | Description |
|------|-------------|
| **Original** | The initially uploaded document |
| **Processed** | A derived version after processing (e.g., language extraction, segmentation) |

## Viewing Document Details

Click any document title or the **View Latest** button to see:

- Full content or file preview
- Complete bibliographic metadata
- Temporal metadata (for historical documents)
- Experiments using this document
- Processing history and artifacts

### Document Detail Sections

| Section | Information |
|---------|-------------|
| **Overview** | Title, type, word count, creation date |
| **Metadata** | Authors, publication date, DOI, and other bibliographic fields |
| **Content** | Full text or file download |
| **Experiments** | List of experiments that include this document |
| **Processing** | Operations performed and their results |

## Editing Documents

### Edit Metadata

1. Navigate to the document detail page
2. Click **Edit** in the top-right
3. Modify any metadata fields:
   - Title
   - Authors, Editor, Edition
   - Publication date
   - Journal, Publisher, Place
   - DOI, ISBN, ISSN, URL
   - Abstract, Notes
4. Click **Save Changes**

### What Can Be Edited

- All bibliographic metadata fields
- Document title
- Notes and abstract

### What Cannot Be Edited

- Original file content (upload a new version instead)
- Processing results (re-run processing)
- Creation date and user ownership

## Deleting Documents

### Delete a Single Document

1. Navigate to the document detail page
2. Click the menu button (three dots) in the top-right
3. Select **Delete**
4. Confirm the deletion

> **Note**: Documents that are part of experiments cannot be deleted directly. Remove them from experiments first, or delete the experiment.

### Delete All Versions

If a document has multiple versions (original + processed):

1. Navigate to any version's detail page
2. Click the menu button (three dots) in the top-right
3. Select **Delete All Versions**
4. Confirm to remove all versions of this document family

This option only appears when a document has multiple versions.

### Delete All Documents (Admin Only)

Administrators can delete all documents at once:

1. Go to **Library → Sources**
2. Click **Delete All Documents**
3. Type `DELETE ALL` to confirm
4. Click **Delete Everything**

> **Warning**: This removes all documents, files, processing results, and experiment relationships. This action cannot be undone.

## Uploading New Documents

From the Library view, click **Upload Document** to add new sources.

See [Upload Documents](upload-documents.md) for detailed instructions.

## Tips for Library Management

### Organization

- Use consistent naming conventions for document titles
- Fill in bibliographic metadata for better searchability
- Add notes to documents explaining their significance

### Best Practices

- Delete test documents after experimentation
- Keep original versions for reference
- Use the type filter to focus on documents or references as needed

### Performance

- The library paginates automatically (10 items per page)
- Large libraries may take a moment to load
- Use filters to narrow down search results

## Related Guides

- [Upload Documents](upload-documents.md)
- [Create Temporal Experiment](create-temporal-experiment.md)
- [Process Documents](document-processing.md)
