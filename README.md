# OntExtract

PROV-O Provenance Tracking for Document Analysis Workflows

Presented at JCDL 2025 (Joint Conference on Digital Libraries), December 15-19, 2025

---

## Overview

OntExtract provides a unified interface for document processing with integrated provenance tracking. PROV-O provenance concepts are embedded directly in the database schema, and each processing operation creates a versioned output with corresponding provenance records. The system operates in two modes: API-enhanced mode uses large language models to orchestrate tool selection, while standalone mode relies on established NLP libraries (spaCy, NLTK, sentence-transformers). Users can apply different processing strategies to the same documents and compare results while the system tracks complete analytical provenance.

---

## Approach

OntExtract implements a 5-stage workflow for document analysis.

1. **Analyze** - The LLM examines documents to identify research goals and document characteristics
2. **Recommend** - The system proposes tool combinations for each document with rationale
3. **Review** - Researchers approve or modify the recommended strategy
4. **Execute** - Tools process documents in parallel with progress tracking
5. **Synthesize** - The LLM generates cross-document insights and patterns

---

## Available NLP Tools

| Tool | Purpose | Implementation |
|------|---------|----------------|
| Named Entity Recognition | Extract people, places, organizations, dates | SpaCy en_core_web_sm with noun phrase extraction |
| Temporal Expression Extraction | Identify dates, periods, durations | SpaCy DATE entities + regex patterns for decades/periods |
| Definition Extraction | Find concept definitions | Pattern matching for 8 definition types with strict acronym validation |
| Text Segmentation | Break documents into paragraphs/sentences | NLTK sentence tokenizer, paragraph splitting |
| Embedding Generation | Create semantic vectors for similarity search | Period-aware model selection based on document year |
| LLM Text Cleanup | Modernize OCR errors and archaic spelling | Claude-based with change tracking and review UI |

---

## Operational Modes

**Standalone Mode** operates without external API dependencies. Users select tools manually through the interface. Available features include entity extraction, temporal analysis, definition extraction, text segmentation, embedding generation, ontology-backed semantic change annotation, OED integration, and PROV-O provenance tracking.

**API-Enhanced Mode** adds LLM orchestration when an Anthropic API key is provided. Features include automated tool selection, cross-document synthesis, LLM-generated event suggestions, and enhanced context extraction. Human-in-the-loop review applies to all LLM recommendations.

---

## Try It Out

### Option 1: Live Demo (Easiest)
Access the live system at **https://ontextract.ontorealm.net**
- Demo credentials: `demo` / `demo123`
- Pre-loaded experiment: Agent Temporal Evolution (1910-2024)
- No installation required

### Option 2: Docker (Recommended)
One-command local installation with Docker Compose:

```bash
cd OntExtract
docker-compose up -d
# Access at http://localhost:8765
# Default login: admin / admin123
```

**See [DOCKER_SETUP.md](DOCKER_SETUP.md) for complete Docker setup guide.**

### Option 3: Manual Installation
For advanced users and contributors who need to modify the code.

**Requirements**: PostgreSQL 14+ with pgvector, Redis 6+, Python 3.12+

See [DOCKER_SETUP.md](DOCKER_SETUP.md#manual-installation-alternative) for manual setup instructions.

---

## Documentation

Full user documentation is available at the [OntExtract Documentation Site](https://ontextract.ontorealm.net/docs/).

---

## Research Workflow

OntExtract guides researchers through a 6-step workflow for semantic change analysis:

| Step | Task | Description |
|------|------|-------------|
| 1 | **Define Terms** | Create anchor terms to track semantic evolution |
| 2 | **Upload Sources** | Add documents from different historical periods |
| 3 | **Create Experiment** | Link terms to document sets with temporal periods |
| 4 | **LLM Orchestration** | AI suggests processing pipelines (optional) |
| 5 | **Execute Pipeline** | Process documents with selected tools |
| 6 | **View Results** | Explore extracted data and provenance |

---

## System Architecture

The backend uses Flask with PostgreSQL, LangGraph for workflow state management, Claude Sonnet 4 for LLM orchestration, and SQLAlchemy ORM with PROV-O schema. The frontend provides a Bootstrap 5 interface with real-time progress tracking. The provenance layer implements W3C PROV-O compliant tracking with exportable graphs.

---

## Ontology
Semantic change event types derive from a Pellet reasoner validated ontology with 34 classes developed from 12 papers.  Event types include pejoration, amelioration, linguistic drift, intension drift, extension drift, lexical emergence, and obsolescence.

See [semantic-change-ontology-v2.ttl](ontologies/semantic-change-ontology-v2.ttl) for the ontology file.

---

## Publications

[OntExtract_JCDL2025.pdf](papers/OntExtract_JCDL2025.pdf) - "OntExtract: PROV-O Provenance Tracking for Document Analysis Workflows" (JCDL 2025)
