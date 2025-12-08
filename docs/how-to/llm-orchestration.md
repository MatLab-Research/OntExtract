# How to Use LLM Orchestration

This guide covers the AI-assisted workflow for analyzing experiments.

## Overview

LLM Orchestration is available in API-enhanced mode (requires Anthropic API key). The system analyzes your experiment and recommends processing strategies for each document.

## Prerequisites

- Anthropic API key configured in Settings
- An experiment with associated documents
- Documents should have text content extracted

## The 5-Stage Workflow

LLM Orchestration follows a structured workflow with human review at each decision point:

### Stage 1: Analyze

The LLM examines your experiment to understand:

- Research goals and scope
- Document characteristics (length, format, historical period)
- Focus terms and their domains
- Temporal range of your corpus

### Stage 2: Recommend

Based on the analysis, the system recommends:

- Which tools to apply to each document
- Processing order and dependencies
- Confidence scores for each recommendation
- Rationale explaining the choices

**Example recommendations:**

| Document | Recommended Tools | Confidence |
|----------|-------------------|------------|
| Historical paper (1910) | Entity extraction, Definition extraction | 0.92 |
| Modern technical paper | Semantic segmentation, Entity extraction | 0.88 |
| Legal dictionary entry | Definition extraction, Temporal extraction | 0.95 |

### Stage 3: Review

You review the recommendations before execution:

- Approve recommendations as-is
- Modify tool selections for specific documents
- Add processing notes
- Reject and request re-analysis

**All LLM recommendations require human approval before execution.**

### Stage 4: Execute

After approval, the system processes documents:

- Tools run using local NLP libraries (spaCy, NLTK, sentence-transformers)
- Progress tracked in real-time
- Results stored as ProcessingArtifacts with PROV-O provenance

**Available Processing Tools:**

- **Entity Extraction** (spaCy): Named entities (PERSON, ORG, GPE) + noun phrase concepts
- **Temporal Extraction** (spaCy + regex): Dates, periods, historical markers, relative expressions
- **Definition Extraction** (hybrid):
  - Zero-shot classification (`facebook/bart-large-mnli`) for sentence scoring
  - Pattern matching for 8 definition types (explicit, copula, acronym, appositive, etc.)
  - Strict acronym validation requiring first-letter matching
  - Quality filters to reject citations, reference lists, and nonsense patterns
- **Text Segmentation**: Structure-aware document splitting
- **Embedding Generation** (sentence-transformers): Period-aware semantic vectors
- **LLM Text Cleanup** (Claude): Modernize OCR errors while preserving historical terminology

### Stage 5: Synthesize

The LLM analyzes results across all documents:

- Identifies patterns and themes
- Generates term cards with frequency data
- Organizes findings by temporal period
- **Does not interpret results** - preserves researcher authority

## Accessing LLM Orchestration

1. Go to **Experiments** > Select your experiment
2. Click **Document Pipeline**
3. Select **LLM** mode (toggle at top of page)
4. Click **LLM Analyze** to begin Stage 1

## Workflow States

| State | Description |
|-------|-------------|
| `not_started` | Orchestration not yet initiated |
| `analyzing` | Stage 1 in progress |
| `awaiting_approval` | Recommendations ready for review |
| `executing` | Processing documents |
| `synthesizing` | Generating cross-document insights |
| `completed` | All stages finished |
| `error` | Processing encountered an error |

## Manual Alternative

If you prefer not to use LLM orchestration:

1. Go to **Document Pipeline** in your experiment
2. Select documents manually
3. Choose processing operations
4. Click **Run Selected Operations**

Manual selections are recorded with the same PROV-O provenance structure.

## Tips

### When to Use LLM Orchestration

- Large document collections (10+ documents)
- Mixed document types requiring different tools
- When you want AI-generated synthesis of patterns

### When to Process Manually

- Small experiments (< 5 documents)
- When you know exactly which tools to apply
- When API costs are a concern

## Troubleshooting

### Orchestration stuck

- Check that Celery worker is running
- Verify API key is valid and has quota
- Review application logs for errors

### Recommendations seem wrong

- Ensure documents have metadata (especially publication date)
- Check that document text was extracted correctly
- Try providing more specific experiment description

## Related Guides

- [Create Temporal Experiment](create-temporal-experiment.md)
- [Process Documents](document-processing.md)
- [View Results](view-results.md)
