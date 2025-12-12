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

1. Go to **Experiments** > Select the experiment > **Document Pipeline**
2. Select documents to process using the checkboxes
3. Under the **Embeddings** section, check **Period-Aware Embeddings**
4. Click **Run Selected Tools**

The service will:

- Check the document's publication date metadata
- Analyze text for archaic language patterns (if no date available)
- Select and apply the appropriate model

### Via LLM Orchestration

When using LLM orchestration, the system may automatically recommend period-aware embeddings for:

- Historical documents (based on publication date)
- Documents with detected archaic language
- Domain-specific technical papers

Recommendations can be approved or modified during the Review stage.

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

When no publication date is available, the service uses a heuristic approach to detect archaic language, based on lexical markers established in historical linguistics research.

### Linguistic Basis

The detection approach uses two categories of markers that are well-documented in the literature on Early Modern English (c. 1500-1700):

**1. Archaic Second-Person Pronouns and Verb Forms**

- **thou, thee, thy, thine** — The singular second-person pronoun system that fell out of standard use by the 17th century. The shift from "thou" to "you" is one of the most studied changes in English historical linguistics (see Burnley, 2000; Wales, 1996).
- **hath, doth** — Third-person singular verb forms with the archaic *-eth* ending, replaced by modern *-s* forms ("has," "does") during the Early Modern period.

**2. Pronominal Adverbs**

- **whence, wherefore, wherein, whereby, heretofore, hereunto** — These are pronominal adverbs formed from wh-/h-/th- stems combined with prepositions. They form systematic patterns (hither/thither/whither for direction-to; hence/thence/whence for direction-from) and are characteristic of both archaic and legal English.

These markers are used in corpus normalization research for Early Modern English texts (see Archer et al., 2015, "Guidelines for normalising Early Modern English corpora") and are recognized as reliable indicators of historical text in computational historical linguistics.

### Detection Method

**Archaic indicators detected:**

- Historical pronouns: thou, thee, thy, thine
- Archaic verbs: hath, doth
- Pronominal adverbs: whence, wherefore, wherein, whereby, heretofore, hereunto, notwithstanding

**Technical indicators detected:**

- Academic vocabulary: hypothesis, methodology, parameter
- Scientific terms: coefficient, algorithm, paradigm, empirical

If archaic language is detected, the historical model is automatically selected.

### Limitations

This is a heuristic approach based on lexical markers rather than a trained classifier. It works well for:

- Texts containing Early Modern English features (pre-1700)
- Legal documents with formal/archaic register
- Religious texts (e.g., King James Bible style)

For more sophisticated period detection, future versions may incorporate trained classifiers on dated corpora.

### References

- Archer, D., Kytö, M., Baron, A., & Rayson, P. (2015). Guidelines for normalising Early Modern English corpora: Decisions and justifications. *ICAME Journal*, 39, 5-24.
- Burnley, D. (2000). *The History of the English Language: A Source Book* (2nd ed.). Longman.
- Wales, K. (1996). *Personal Pronouns in Present-Day English*. Cambridge University Press.
- Piotrowski, M. (2012). *Natural Language Processing for Historical Texts*. Morgan & Claypool (Synthesis Lectures on Human Language Technologies, vol. 17).

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
