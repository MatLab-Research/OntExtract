# OntExtract

Historical Document Analysis with Optional LLM Orchestration

Presented at JCDL 2025 (Joint Conference on Digital Libraries), December 15-19, 2025

---

## Overview

OntExtract is a digital humanities platform for analyzing historical documents. The platform supports period-aware document processing along with temporal evolution tracking and semantic change annotation. Users retain manual control over tool selection while optional LLM enhancements provide automated suggestions when API access is available.

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

| Tool | Purpose | Historical Text Adaptation |
|------|---------|---------------------------|
| Named Entity Recognition | Extract people, places, organizations | SpaCy with historical text models |
| Temporal Expression Extraction | Identify dates, periods, durations | Historical date format handling |
| Definition Extraction | Find concept definitions | Pattern matching for archaic phrasing |
| Text Segmentation | Break documents into logical sections | Structure-aware splitting |
| Embedding Generation | Create semantic vectors | Period-specific embedding models |
| LLM Text Cleanup | Modernize OCR errors and spelling | Preservation of historical terminology |
| Sentiment Analysis | Detect emotional tone | Calibrated for formal historical writing |
| Keyword Extraction | Identify important terms | Domain-specific weighting |

---

## Operational Modes

**Standalone Mode** operates without external API dependencies. Users select tools manually through the interface. Available features include entity extraction, temporal analysis, definition extraction, text segmentation, embedding generation, ontology-backed semantic change annotation, OED integration, and PROV-O provenance tracking.

**API-Enhanced Mode** adds LLM orchestration when an Anthropic API key is provided. Features include automated tool selection, cross-document synthesis, LLM-generated event suggestions, and enhanced context extraction. Human-in-the-loop review applies to all LLM recommendations.

---

## Installation

Live system available at https://ontextract.ontorealm.net

For local installation:

```bash
cd OntExtract

python -m venv venv
source venv/bin/activate

pip install -r requirements.txt

cp .env.template .env
# Edit .env and add ANTHROPIC_API_KEY for API-enhanced mode (optional)

FLASK_ENV=development python run.py
# Access at http://localhost:8765
```

---

## System Architecture

The backend uses Flask with PostgreSQL, LangGraph for workflow state management, Claude Sonnet 4 for LLM orchestration, and SQLAlchemy ORM with PROV-O schema. The frontend provides a Bootstrap 5 interface with real-time progress tracking and strategy review. The provenance layer implements W3C PROV-O compliant tracking with exportable graphs.

---

## Ontology

Semantic change event types derive from a validated ontology with 34 classes developed from 12 papers. The ontology includes 33 embedded academic citations and passes Pellet reasoner validation. Event types include pejoration, amelioration, linguistic drift, intension drift, extension drift, lexical emergence, and obsolescence.

See [semantic-change-ontology-v2.ttl](ontologies/semantic-change-ontology-v2.ttl) for the ontology file.

---

## Publications

[OntExtract_JCDL2025.pdf](papers/OntExtract_JCDL2025.pdf) - "LLM-Orchestrated Document Processing for Historical Text Analysis" (JCDL 2025)
