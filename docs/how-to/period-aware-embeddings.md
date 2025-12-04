# How to Use Period-Aware Embeddings

This guide covers OntExtract's period-aware embedding feature for historical and domain-specific text analysis.

## Overview

Historical texts use different vocabulary, spelling, and linguistic patterns than contemporary texts. Using a modern embedding model on archaic text can result in poor semantic representations.

The period-aware embedding service addresses this by:

- Selecting models trained on corpora from similar time periods
- Using domain-specific models for specialized vocabularies
- Detecting archaic language patterns when metadata is unavailable

## When to Use Period-Aware Embeddings

Use period-aware embeddings when:

- Analyzing documents spanning multiple historical periods
- Working with archaic or historical language
- Processing domain-specific texts (scientific, legal, biomedical)
- Comparing semantic similarity across time periods

## Model Selection

The service selects embedding models based on this priority:

1. **Domain** (if specified) - Takes precedence for specialized vocabularies
2. **Year** (if specified) - Selects period-appropriate model
3. **Text Analysis** (fallback) - Detects archaic/technical language patterns
4. **Default** - Falls back to modern model

### Period-Based Models

| Period | Era | Handles Archaic |
|--------|-----|-----------------|
| Pre-1850 | Pre-industrial | Yes |
| 1850-1950 | Industrial | Yes |
| 1950-2000 | Modern | No |
| 2000+ | Contemporary | No |

### Domain-Specific Models

| Domain | Use Case |
|--------|----------|
| **Scientific** | Scientific papers, technical documentation |
| **Legal** | Legal documents, contracts, case law |
| **Biomedical** | Medical literature, clinical texts |

## Using Period-Aware Embeddings

### From the Document Pipeline

1. Go to your experiment's **Document Pipeline**
2. Select a document to process
3. Choose **Embeddings** from the processing operations
4. Select **Period Aware** from the embedding method dropdown
5. Click **Run**

The service will:

- Check the document's publication date metadata
- Analyze text for archaic language patterns (if no date available)
- Select and apply the appropriate model

### Via LLM Orchestration

When using LLM orchestration, the system may automatically recommend period-aware embeddings for:

- Historical documents (based on publication date)
- Documents with detected archaic language
- Domain-specific technical papers

You can approve or modify this recommendation during the Review stage.

## Setup Requirements

Period-aware models must be downloaded before use. Run the download script:

```bash
# Download core models (~500MB)
python scripts/download_embedding_models.py --core

# Download all models (~2GB)
python scripts/download_embedding_models.py --all

# Check download status
python scripts/download_embedding_models.py --check
```

## Archaic Language Detection

When no publication date is available, the service analyzes text for archaic patterns:

**Archaic indicators detected:**

- Historical pronouns: thou, thee, thy
- Archaic verbs: hath, doth
- Historical adverbs: whence, wherefore, wherein, heretofore

**Technical indicators detected:**

- Academic vocabulary: hypothesis, methodology, parameter
- Scientific terms: coefficient, algorithm, paradigm, empirical

If archaic language is detected, the historical model is automatically selected.

## Understanding Results

### Embedding Metadata

When period-aware embeddings are generated, the processing artifact includes metadata showing:

| Field | Description |
|-------|-------------|
| **Selected Model** | Which embedding model was used |
| **Selection Reason** | Why this model was chosen |
| **Selection Confidence** | Confidence score (0-1) |
| **Era** | Detected time period category |
| **Handles Archaic** | Whether the model handles historical language |

### Semantic Drift Classification

When comparing embeddings across periods, drift is classified as:

| Classification | Drift Value | Meaning |
|----------------|-------------|---------|
| **Stable** | < 0.2 | Minimal semantic change |
| **Minor Change** | 0.2 - 0.4 | Some evolution in meaning |
| **Moderate Drift** | 0.4 - 0.7 | Notable semantic shift |
| **Major Shift** | ≥ 0.7 | Substantial meaning change |

## Tips for Best Results

### Document Metadata

- Ensure documents have accurate **publication dates** for best model selection
- Add **domain** metadata (scientific, legal, biomedical) when applicable

### Corpus Considerations

- Use consistent embedding methods within a single experiment for valid comparisons
- When comparing across periods, process all documents with period-aware embeddings
- Include multiple documents per period for reliable drift calculations

### Model Downloads

- Download models before batch processing to avoid delays
- Core models are sufficient for most historical text analysis
- Domain-specific models (scientific, legal, biomedical) are included in the full download

## Related Guides

- [Process Documents](document-processing.md)
- [Create Temporal Experiment](create-temporal-experiment.md)
- [View Results](view-results.md)
