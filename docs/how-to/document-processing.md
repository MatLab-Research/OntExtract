# How to Process Documents

This guide covers the document processing operations available in OntExtract.

## Overview

After uploading documents, various processing operations can be applied to extract structured information. OntExtract preserves original documents unchanged—all results are stored as ProcessingArtifacts linked to source documents through PROV-O relationships.

## Processing Operations

| Operation | Purpose | Mode |
|-----------|---------|------|
| **LLM Text Cleanup** | Fix OCR errors, normalize spelling | API-enhanced |
| **Segmentation** | Split into paragraphs or sentences | Standalone |
| **Embeddings** | Generate vector representations | Both |
| **Entity Extraction** | Identify people, places, organizations | Standalone |
| **Temporal Extraction** | Find dates, periods, durations | Standalone |
| **Definition Extraction** | Locate concept definitions | Standalone |

## LLM Text Cleanup

Use this for scanned or OCR'd historical documents with recognition errors.

### When to Use

- Documents with OCR character errors (rn → m, l → I)
- Archaic spelling that needs normalization
- Scanning artifacts (headers, page numbers in text)

### How to Run

1. Navigate to the document detail page
2. Click the menu button (three dots) in the top-right
3. Select **Clean with LLM**
4. Review the suggested corrections
5. Accept or modify changes
6. Save the cleaned version

**Note**: LLM cleanup creates a new document version. The original is preserved. This operation requires an Anthropic API key configured in settings.

### From Document Pipeline

Cleanup can also be triggered from the experiment's Document Pipeline:

1. Go to **Experiments** > Select experiment > **Document Pipeline**
2. Click the broom icon next to any document
3. Follow the cleanup workflow

## Segmentation

Split documents into logical sections for analysis.

### Segmentation Methods

| Method | Description | Best For |
|--------|-------------|----------|
| **Paragraph** | NLTK-enhanced paragraph detection | Most documents |
| **Sentence** | NLTK Punkt tokenizer | Fine-grained analysis |

### How to Run

1. Go to the document or experiment's **Document Pipeline**
2. Select documents to process
3. Check **Segmentation** in Processing Operations
4. Choose a segmentation method
5. Click **Run Selected Tools**

### Results

Segmentation creates TextSegment artifacts with:
- Segment text content
- Character-level position (start/end offsets)
- Segment index within document

### Auto-Dependency

When selecting **Embeddings** or **Definition Extraction**, the system automatically selects **Paragraph Segmentation** if it hasn't been run. This is because:

- Embeddings create segment-level vectors when segments exist (more granular similarity search)
- All extraction tools produce better results with structured text segments

Segmentation can be deselected for document-level processing only.

## Embedding Generation

Create vector representations for semantic similarity search.

### Embedding Methods

| Method | Description | Best For |
|--------|-------------|----------|
| **Local** | Standard sentence-transformers model | General modern text |
| **Period Aware** | Selects model based on document era/domain | Historical or domain-specific text |
| **OpenAI** | text-embedding-3-large (3072 dims) | Highest accuracy (requires API key) |

### How to Run

1. Go to **Document Pipeline** or document detail
2. Check **Embeddings** in Processing Operations
3. Select embedding method
4. Click **Run Selected Tools**

### Period-Aware Embeddings

For historical documents or specialized domains, use **Period Aware** embeddings. This automatically selects appropriate models based on:

- Document publication date
- Domain (scientific, legal, biomedical)
- Detected archaic language patterns

See [Period-Aware Embeddings](period-aware-embeddings.md) for detailed information.

### Results

Embeddings enable:
- Semantic similarity search across segments
- Finding related passages across documents
- Clustering similar content

Vectors are stored in PostgreSQL using pgvector for efficient similarity queries.

## Entity Extraction

Identify named entities using spaCy NLP models.

### Entity Types

- **PERSON** - People, including fictional
- **ORG** - Organizations, companies, agencies
- **GPE** - Geopolitical entities (countries, cities)
- **DATE** - Dates and periods
- **WORK_OF_ART** - Titles of works

### How to Run

1. Select documents in Document Pipeline
2. Check **Entity Extraction** in Processing Operations
3. Click **Run Selected Tools**

### Results

Entity extraction creates artifacts with:
- Entity text and type
- Character positions in source
- Confidence scores

**Note**: Accuracy depends on domain alignment with training corpora. Historical and technical texts may require validation.

## Definition Extraction

Extract term definitions using pattern matching with strict validation.

### Approach

OntExtract uses pattern matching to identify definitions in text:

1. **Zero-shot classification** (optional, disabled by default)
   - Uses `facebook/bart-large-mnli` model (~1.6GB)
   - Too slow on CPU for large documents (10+ minutes per document)
   - Enable with environment variable: `ENABLE_ZERO_SHOT_DEFINITIONS=true`
   - When enabled, scores sentences for confidence boosting

2. **Pattern matching** (default, fast) - Detects 8 definition types:
   - **explicit_definition**: "X is defined as Y"
   - **explicit_reference**: "X refers to Y"
   - **meaning**: "X means Y"
   - **copula**: "X is a Y"
   - **acronym**: "IRA (Information Retrieval Agent)" with strict validation
   - **also_known_as**: "X (also known as Y)"
   - **ie_explanation**: "X (i.e., Y)"
   - **appositive**: Dependency parsing for noun appositives

3. **Strict acronym validation**:
   - Pattern: 2-6 uppercase letters with capitalized word expansion
   - Requires expansion first letters to match acronym (e.g., "IRA" must expand to words starting with I, R, A)
   - Rejects expansions containing years (likely citations)
   - Eliminates nonsense patterns

4. **Quality filters**:
   - Reject academic citations (e.g., "et al., 2015")
   - Reject reference lists (year ranges, multiple years)
   - Reject terms with more than 3 words
   - Length validation (10-200 characters)

### How to Run

1. Select documents in Document Pipeline
2. Check **Definition Extraction** in Processing Operations
3. Click **Run Selected Tools**

### Results

Definition extraction creates artifacts with:
- Term being defined
- Definition text
- Pattern type (explicit, acronym, etc.)
- Confidence score (0.65-0.90 depending on pattern)
- Character positions in source document
- Source sentence for context

Results are labeled "Auto" in the UI with a "Pattern" source badge. If zero-shot is enabled, definitions may show "ZeroShot" badge.

**Note**: Definition extraction works best on documents that explicitly define terminology, such as glossaries, textbook introductions, or standards documents. Research papers that use but do not define terms may return few or no results.

## Batch Processing

Process multiple documents efficiently:

1. Go to **Experiments** > Select experiment > **Document Pipeline**
2. Use checkboxes to select multiple documents
3. Choose operations to apply
4. Click **Run Selected Tools**

![Document Pipeline](../assets/images/screenshots/experiment-pipeline-content.png)

Operations run in parallel where possible. Progress is tracked in the interface.

## Processing Without API Costs

**Run Local Tools** processes documents using only local NLP libraries:
- spaCy for entity extraction
- NLTK for sentence tokenization
- sentence-transformers for embeddings

No external API calls are made, enabling offline operation.

## Viewing Results

After processing, view results from the experiment detail page:

1. Go to **Experiments** > Select the experiment
2. Expand the **View Results** section
3. Click a result type:
   - **Definitions** - Extracted term definitions
   - **Entities** - Named entities and concepts
   - **Embeddings** - Generated vectors and similarity data
   - **Segments** - Document segments
   - **Temporal** - Extracted dates and periods

### Result Details

Each result page shows:
- Extracted items grouped by document
- Source text and character positions
- Confidence scores and extraction method
- Links back to source documents

## PROV-O Provenance

All processing operations create PROV-O provenance records:

- **wasDerivedFrom** - Links artifacts to source documents
- **wasGeneratedBy** - Connects artifacts to generating activities
- **wasAssociatedWith** - Maps operations to tool versions

This enables complete reproducibility—any result can be traced back to its source to understand exactly how it was generated.

## Troubleshooting

### Processing Stuck

- Check Celery worker status
- Verify Redis connection
- Review application logs

### No Results Generated

- Ensure document has text content
- Check that source document exists
- Verify processing completed (no errors in logs)

### Embedding Errors

- For OpenAI: verify API key in settings
- For local: check sentence-transformers installation
- Ensure document has been segmented first

## Related Guides

- [Upload Documents](upload-documents.md)
- [Create Temporal Experiment](create-temporal-experiment.md)
- [Create Anchor Terms](create-anchor-terms.md)
