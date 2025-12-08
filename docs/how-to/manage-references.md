# How to Manage References

This guide explains how to add, manage, and use reference documents in OntExtract for canonical term definitions and authoritative sources.

## What Are References?

References are canonical source materials that provide authoritative definitions and context for your terminology analysis. Unlike regular documents (primary sources for analysis), references serve as:

- **Authoritative definitions** - Dictionary and encyclopedia entries
- **Standard terminology** - Technical specifications and glossaries
- **Supporting literature** - Academic papers and books that define key concepts

## Reference Types

OntExtract supports several reference subtypes:

| Type | Icon | Use Case |
|------|------|----------|
| **Academic Paper** | Graduation cap | Peer-reviewed articles defining terminology |
| **Book** | Book | Monographs and edited volumes |
| **Conference Proceeding** | Users | Conference papers and presentations |
| **Standard/Specification** | Certificate | Technical standards (ISO, IEEE, etc.) |
| **Encyclopedia Entry** | Book open | Encyclopedia definitions |
| **OED Dictionary Entry** | External link | Oxford English Dictionary entries |
| **Glossary/Terminology** | List | Domain-specific term lists |
| **Technical Report** | File code | Technical documentation |
| **White Paper** | File alt | Industry white papers |
| **Patent** | Lightbulb | Patent documents |
| **Web Resource** | Globe | Online resources |

## Adding References

### Access the References Section

References can be added from multiple locations:

1. **Library → Sources** (filter by References tab)
2. **Direct URL**: Navigate to `/references/`
3. **During experiment creation** via Quick Add

### Upload a General Reference

1. Go to **References** and click **Upload Reference**
2. Select the **General Reference** tab
3. Upload your file (PDF, Word, Text, Markdown, or HTML)
4. Select the **Reference Type**
5. Fill in metadata (or let automatic extraction fill it for PDFs)
6. Click **Upload Reference**

![Reference Upload Page](../assets/images/screenshots/reference-upload-content.png)

#### Automatic Metadata Extraction

For PDF files, OntExtract automatically extracts:

- DOI
- Title
- Authors
- Publication date
- Journal name

The extraction status shows progress and results in real-time.

### Add an OED Dictionary Entry

Oxford English Dictionary entries are especially valuable for tracking historical term evolution.

1. Go to **References** and click **Upload Reference**
2. Select the **OED Dictionary Entry** tab
3. **Option A**: Upload an OED PDF
   - Select the PDF file
   - Click **Parse PDF** to auto-populate fields
4. **Option B**: Enter manually
   - Enter the **Term/Headword**
   - Paste the **Complete OED Entry Text**
   - Add **Historical Quotations** for temporal tracking
   - Note the **First Recorded Use** date
5. Click **Save OED Entry**

#### OED Entry Components

The system captures:

- **Headword** - The main term being defined
- **Full text** - Complete entry including all definitions and senses
- **Historical quotations** - Chronologically ordered usage examples
- **First recorded use** - The earliest documented usage date
- **Temporal data** - Century distribution and semantic shifts

### Add Other Dictionary Entries

For dictionaries other than OED:

1. Select the **Other Dictionary** tab
2. Enter the **Dictionary Source** (e.g., Merriam-Webster, Cambridge)
3. Enter the **Term** and **Definition**
4. Optionally add:
   - Context/Domain
   - Synonyms
   - Source URL
5. Click **Save Dictionary Entry**

## Viewing References

### Reference List

The reference list shows:

- **Title** with type icon
- **Reference type** badge
- **Source** (journal, dictionary name, etc.)
- **Uploaded by** user
- **Date** (publication or creation date)
- **Status** (Processed, Processing, Error)
- **Used in** count of experiments

### Reference Detail View

Click any reference to see:

- Full content or definition
- Complete metadata
- Source information
- Experiments using this reference
- Download link (for uploaded files)

## Managing References

### Edit Reference Metadata

1. Navigate to the reference detail page
2. Click the **Edit** button
3. Update any metadata fields:
   - Title and type
   - Authors, editor, edition
   - Publication details
   - Identifiers (DOI, ISBN, ISSN)
   - Abstract and notes
4. Click **Save Changes**

### Delete a Reference

1. Navigate to the reference detail page
2. Click the **Delete** button (trash icon)
3. Confirm the deletion

> **Note**: Deleting a reference removes it from all associated experiments.

## Using References in Experiments

### During Experiment Creation

When creating a new experiment, you can:

1. Select existing references from your library
2. Use **Quick Add** to create new references inline
3. Link OED entries for temporal analysis

### After Experiment Creation

1. Go to **Experiments** → Select your experiment
2. Navigate to the **References** tab
3. Click **Add Reference** to link existing references
4. Or **Upload Reference** to add new ones

### References and LLM Orchestration

References provide context for LLM analysis:

- Dictionary definitions inform term interpretation
- Academic sources provide domain context
- Historical quotations support temporal analysis

## Best Practices

### Choosing References

- Select authoritative sources for your domain
- Include historical references for temporal analysis
- Add OED entries for terms you want to track across time

### OED Entries for Temporal Analysis

When adding OED entries:

1. Include the complete entry text (don't summarize)
2. Preserve all historical quotations with dates
3. Note the first recorded use date
4. Include century distribution information

### Metadata Quality

- Fill in as much metadata as possible
- Use consistent author name formats
- Include DOIs when available for citation

### Organization

- Use descriptive titles
- Select accurate reference types
- Add notes explaining why you included each reference

## Related Guides

- [Manage Your Library](manage-library.md)
- [Upload Documents](upload-documents.md)
- [Create Temporal Experiment](create-temporal-experiment.md)
- [LLM Orchestration](llm-orchestration.md)
