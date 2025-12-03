# How to View Results

This guide covers exploring analysis results and provenance in OntExtract.

## Overview

After processing documents, OntExtract provides several ways to explore results:

- Processing artifacts for individual documents
- Experiment-level analysis and timelines
- Provenance graphs showing processing history
- Export options for further analysis

## Viewing Processing Artifacts

Each document's processing results are stored as artifacts.

### Access Document Artifacts

1. Go to **Documents** > Select a document
2. Click the **Processing Artifacts** tab
3. View artifacts grouped by operation type

### Artifact Types

| Type | Contents |
|------|----------|
| **Text Segments** | Paragraphs or sentences with character positions |
| **Entities** | Named entities with types and confidence scores |
| **Embeddings** | Vector representations (viewable as similarity scores) |
| **Temporal Expressions** | Dates, periods, and durations found in text |
| **Definitions** | Extracted concept definitions |

### Artifact Details

Each artifact shows:

- Operation type and timestamp
- Source document reference
- Processing parameters used
- Tool version (for reproducibility)
- Structured results

## Experiment Results

### Timeline View

For temporal evolution experiments:

1. Go to **Experiments** > Select experiment
2. View the timeline showing documents by period
3. See term usage patterns across time

### LLM Synthesis Results

If you used LLM Orchestration:

1. Go to **LLM Orchestration** tab
2. View the **Synthesis** section
3. See cross-document patterns and term cards

**Note**: The synthesis organizes findings but does not interpret them. Analytical conclusions remain with the researcher.

## Provenance Tracking

OntExtract records complete PROV-O provenance for all operations.

### Viewing Provenance

Each artifact links to its provenance chain showing:

- **wasDerivedFrom** - Source document(s)
- **wasGeneratedBy** - Processing activity
- **wasAssociatedWith** - Tool and version used
- **used** - Input entities consumed

### Why Provenance Matters

- **Reproducibility** - Recreate exact processing conditions
- **Transparency** - Understand how results were generated
- **Debugging** - Trace unexpected results to their source
- **Scholarly citation** - Document analytical methodology

## Semantic Similarity Search

With embeddings generated, you can search for similar content:

1. Select a text segment
2. Click **Find Similar**
3. View segments ranked by semantic similarity

This enables discovering related passages across your document corpus.

## Export Options

### Export Formats

| Format | Use Case |
|--------|----------|
| **CSV** | Tabular data for spreadsheets |
| **JSON** | Structured data for programming |
| **Report** | Formatted summary document |

### What Can Be Exported

- Processing artifacts with metadata
- Entity extraction results
- Segment text with positions
- Provenance records

## Results Dashboard

Access the Results area from the main navigation:

1. Click **Results** in the top menu
2. View aggregate statistics
3. Browse recent processing activities

## Coming Soon

Additional results features planned for future releases:

- Interactive timeline visualizations
- Semantic drift graphs
- Comparative period analysis
- Ontology-based event annotation

## Troubleshooting

### No results showing

- Verify processing operations completed
- Check the Processing Artifacts tab
- Review experiment status

### Missing artifacts

- Ensure the operation was selected during processing
- Check for errors in the processing log
- Verify document had extractable content

## Related Guides

- [Process Documents](document-processing.md)
- [LLM Orchestration](llm-orchestration.md)
- [Create Temporal Experiment](create-temporal-experiment.md)
