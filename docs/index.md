# OntExtract Documentation

<div style="float: right; margin-left: 1em; margin-bottom: 0.5em;">
  <img src="assets/images/llm-attribution-dark.png" alt="Written with Claude" width="120">
</div>

Welcome to the OntExtract user manual.

## About OntExtract

OntExtract is a digital humanities platform for analyzing historical documents. The system supports period-aware document processing, temporal evolution tracking, and semantic change annotation.

## Quick Links

- [Getting Started](getting-started/installation.md) - Installation and initial configuration
- [First Login](getting-started/first-login.md) - Initial setup after installation
- [FAQ](faq.md) - Frequently asked questions

## How-To Guides

Step-by-step guides for common tasks:

| Guide | Description |
|-------|-------------|
| [Upload Documents](how-to/upload-documents.md) | Add historical documents for analysis |
| [Create Anchor Terms](how-to/create-anchor-terms.md) | Define terms to track across periods |
| [Create Temporal Experiment](how-to/create-temporal-experiment.md) | Set up semantic evolution analysis |

## Core Features

### Document Management
Upload and manage historical documents with metadata including publication dates, authors, and chapter information. Supports PDF, plain text, Word, and HTML formats.

### Anchor Terms
Define key concepts to track across your document corpus. Anchor terms serve as reference points for analyzing semantic change.

### Temporal Evolution Analysis
Track how term meanings change across historical periods using timeline visualizations and ontology-backed semantic change events.

### Document Processing
- **LLM Text Cleanup** - Fix OCR errors and formatting issues using Claude
- **Segmentation** - Split documents into paragraphs or sentences
- **Embeddings** - Generate vector representations for similarity analysis
- **Entity Extraction** - Identify named entities and concepts

### Ontology-Informed Design
Event types derived from a formally validated Semantic Change Ontology with 34 classes and 33 academic citations.

### Provenance Tracking
Complete W3C PROV-O provenance capture for all analysis steps, enabling reproducibility and transparency.

## Typical Workflow

1. **Create an Experiment** - Define your research scope and temporal periods
2. **Upload Documents** - Add historical sources spanning your time range
3. **Create Anchor Terms** - Define the concepts you want to track
4. **Process Documents** - Run text cleanup, segmentation, and embeddings
5. **Analyze Results** - Explore semantic evolution across periods

## Getting Help

- Check the [FAQ](faq.md) for common questions
- Report issues at [GitHub](https://github.com/MatLab-Research/OntExtract/issues)

## About This Documentation

This manual covers installation, configuration, and usage of OntExtract features. Pages are organized by task and feature area.
