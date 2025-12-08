# Frequently Asked Questions

Common questions about OntExtract.

## General

### What is OntExtract?

OntExtract is a document processing system with integrated provenance tracking. It operates in two modes: standalone mode uses established NLP libraries without external dependencies, while API-enhanced mode adds LLM orchestration for automated tool selection.

### Do I need an API key to use OntExtract?

No. Core features work without an API key:

- Document upload and management
- Segmentation (paragraph, sentence, semantic)
- Entity extraction (spaCy)
- Temporal expression extraction
- Embedding generation (local sentence-transformers)
- PROV-O provenance tracking

LLM-enhanced features require an Anthropic API key:

- LLM text cleanup (OCR correction)
- Automated tool orchestration
- Cross-document synthesis

### What are the two operational modes?

**Standalone Mode**: All document processing uses local NLP libraries (spaCy, NLTK, sentence-transformers). No external API calls required.

**API-Enhanced Mode**: Adds LLM orchestration through a 5-stage workflow: Analyze → Recommend → Review → Execute → Synthesize. The LLM recommends tools and synthesizes results, but human review is required before execution.

## Document Processing

### What processing operations are available?

| Operation | Description | Mode |
|-----------|-------------|------|
| LLM Text Cleanup | Fix OCR errors and normalize text | API-enhanced |
| Segmentation | Split into paragraphs/sentences | Standalone |
| Embeddings | Generate vectors for similarity | Both |
| Entity Extraction | Identify people, places, orgs | Standalone |
| Temporal Extraction | Find dates and periods | Standalone |
| Definition Extraction | Hybrid zero-shot + pattern matching for definitions and acronyms | Standalone |

### Does processing modify my original documents?

No. OntExtract preserves original documents unchanged. All processing results are stored as separate ProcessingArtifacts linked to source documents through PROV-O relationships.

### What is PROV-O provenance?

PROV-O is the W3C standard for representing provenance information. OntExtract embeds PROV-O concepts directly in the database, tracking:

- Which tools processed each document (wasAssociatedWith)
- How artifacts were generated (wasGeneratedBy)
- What source documents were used (wasDerivedFrom)

This enables complete reproducibility—you can trace any result back to its source.

## Experiments

### What is a temporal evolution experiment?

Temporal evolution experiments analyze how term meanings change over time. You define anchor terms (key concepts to track) and upload historical documents spanning your time range. The system processes documents and organizes results by temporal period.

### How are documents assigned to periods?

Documents are assigned to temporal periods based on their publication date metadata. Ensure each document has a publication date when uploading.

## Troubleshooting

### Processing operations aren't running

- Verify Celery worker is running
- Check Redis connection
- Review application logs for errors

### No results after processing

- Ensure document has text content (not image-only PDF)
- Verify processing completed without errors
- Check the Processing Artifacts tab on document detail page

### LLM features not working

- Verify Anthropic API key is configured in settings
- Check API key has sufficient quota
- Review error messages in the interface
