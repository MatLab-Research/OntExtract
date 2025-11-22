# OntExtract

User-Empowered Historical Document Analysis with Optional LLM Orchestration

Presented at JCDL 2025 (Joint Conference on Digital Libraries)
December 15-19, 2025

---

## Overview

OntExtract is a digital humanities platform for analyzing historical documents with full manual control and optional LLM enhancements. The system supports period-aware document processing, temporal evolution tracking, and semantic change annotation.

Researchers have complete control over document analysis through manual tool selection, period definition, and event annotation. For those with API access, an optional 5-stage LLM orchestration framework can suggest processing strategies and generate cross-document insights - but all core features work without any API keys.

---

## The Problem

Digital humanities researchers processing historical documents face three challenges:

1. Tool Selection Complexity - Dozens of NLP tools exist, each with specific capabilities and configuration requirements
2. Document Variability - Historical texts vary in language, structure, and content; no single tool configuration works universally
3. Cross-Document Synthesis - Manual synthesis of insights across document collections is time-consuming and error-prone

Existing approaches require researchers to:
- Manually select appropriate tools for each document
- Configure tool parameters based on document characteristics
- Separately analyze results from each tool and document
- Synthesize findings across the collection manually

---

## The OntExtract Approach

OntExtract implements a 5-stage workflow that automates tool selection, configuration, execution, and synthesis:

### Stage 1: Analyze
The LLM examines the experiment description and document collection to understand:
- Research goals and required information types
- Document characteristics (period, language, structure)
- Potential processing challenges

### Stage 2: Recommend
The LLM generates a customized processing strategy for each document:
- Selects appropriate NLP tools based on document content and research goals
- Configures tool parameters for optimal results
- Provides rationale for each recommendation

### Stage 3: Review
Researchers review and approve or modify the recommended strategy:
- Human-in-the-loop verification ensures alignment with research goals
- Strategy can be adjusted before execution
- Transparent decision-making process

### Stage 4: Execute
The system runs the approved tools across all documents:
- Parallel processing for efficiency
- Robust error handling with automatic retries
- Progress tracking with real-time updates

### Stage 5: Synthesize
The LLM analyzes results across the entire collection:
- Identifies patterns and themes across documents
- Generates cross-document insights
- Produces structured analysis reports

---

## Research Contributions

### 1. LLM-Mediated Tool Orchestration
Uses LLMs for intelligent NLP tool selection and configuration in digital humanities workflows.

### 2. W3C PROV-O Provenance Tracking
Complete provenance capture for all analysis steps:
- Entities: Documents, tool outputs, insights
- Activities: Tool executions, LLM analyses, human reviews
- Agents: Tools, LLMs, researchers
- Attributions: Clear lineage from source documents to final insights

Enables reproducibility, transparency, and audit trails for computational analysis in humanities research.

### 3. Period-Aware Historical Text Processing
Specialized handling for historical documents:
- Temporal expression extraction for dating events
- Period-specific embedding models (historical vs. contemporary)
- OED (Oxford English Dictionary) integration for historical definitions
- Context-aware citation tracking

### 4. Human-in-the-Loop Validation
Strategy review stage ensures:
- Researcher control over computational methods
- Alignment with domain expertise
- Trust in automated recommendations

---

## Available NLP Tools

The system provides 8 specialized processing tools:

| Tool | Purpose | Historical Text Adaptation |
|------|---------|---------------------------|
| Named Entity Recognition | Extract people, places, organizations | SpaCy with historical text models |
| Temporal Expression Extraction | Identify dates, periods, durations | Historical date format handling |
| Definition Extraction | Find concept definitions | Pattern matching for archaic phrasing |
| Text Segmentation | Break documents into logical sections | Structure-aware splitting |
| Embedding Generation | Create semantic vectors | Period-specific embedding models |
| LLM Text Cleanup | Modernize OCR errors, spelling | Preservation of historical terminology |
| Sentiment Analysis | Detect emotional tone | Calibrated for formal historical writing |
| Keyword Extraction | Identify important terms | Domain-specific weighting |

---

## Example Workflow

Research Question: "How do professional ethics concepts evolve in engineering publications from 1900-1950?"

Stage 1 - Analyze: LLM identifies need for temporal expressions, entity recognition, and definition extraction

Stage 2 - Recommend:
- Document A (1905 technical report): Temporal extraction, entity recognition, definition extraction
- Document B (1920 ethics guideline): All tools plus sentiment analysis for prescriptive language
- Document C (1948 court case): Entity recognition, temporal extraction (focused on legal dates)

Stage 3 - Review: Researcher approves strategy with minor adjustment (disable sentiment analysis for technical report)

Stage 4 - Execute: Tools process all documents in parallel, extracting 847 entities, 156 temporal expressions, 43 definitions

Stage 5 - Synthesize: LLM generates report showing:
- Evolution from implicit ethical assumptions (1905) to explicit codes (1920s)
- Key concept definitions that shifted meaning over time
- Network of referenced actors and institutions

---

## System Architecture

Backend:
- Flask application with PostgreSQL database
- LangGraph for workflow state management
- Claude Sonnet 4 for LLM orchestration
- SQLAlchemy ORM with PROV-O schema

Frontend:
- Bootstrap 5 responsive interface
- Real-time progress tracking
- Markdown rendering for synthesized insights
- Strategy review interface

Provenance Layer:
- W3C PROV-O compliant RDF serialization
- Complete lineage tracking
- Exportable provenance graphs

---

## Operational Modes

OntExtract operates in two modes based on available resources:

### Standalone Mode (No API Key Required) - PRIMARY MODE
Complete document processing and temporal analysis capabilities:
- Manual tool selection through interface
- Same NLP libraries (spaCy, NLTK, sentence-transformers)
- Entity extraction, temporal analysis, definition extraction
- Text segmentation and embedding generation
- **Temporal timeline with ontology-backed event types**
- **Manual semantic change annotation**
- **Period-aware document linking**
- **OED integration for historical definitions**
- Full PROV-O provenance tracking
- SPARQL queries over semantic events

Configuration: Works immediately - no API keys or external services required. Ontology metadata loaded from local file.

### API-Enhanced Mode (Requires Anthropic API Key) - OPTIONAL
Additional LLM orchestration features that enhance but don't replace user control:
- Automated tool selection and strategy recommendation
- Cross-document synthesis with pattern identification
- LLM suggestions for semantic events (user reviews and approves)
- Enhanced context anchor extraction
- Human-in-the-loop review of all LLM recommendations

Configuration: Set ANTHROPIC_API_KEY environment variable to enable LLM features.

**Key Point**: All core features work without an API key. LLM features provide suggestions and insights, but users remain in control of all annotations and decisions.

---

## Ontology-Informed Design

OntExtract's semantic change event types are derived from a formally validated ontology:

- **34 event type classes** from comprehensive literature review (12 papers, 200+ pages)
- **33 academic citations** embedded directly in ontology
- **Pellet reasoner validation** ensures logical consistency
- **BFO-aligned** for upper-level ontology integration

Event types include:
- Pejoration/Amelioration (sentiment change - Jatowt & Duh 2014)
- Linguistic Drift (gradual meaning shift - Kutuzov et al. 2018)
- Intension/Extension Drift (definition vs. usage - Stavropoulos et al. 2019)
- Lexical Emergence/Obsolescence (lifecycle changes - Tahmasebi et al. 2021)
- URI/Hierarchy Drift (structural changes - Capobianco et al. 2020)

Users select event types from an ontology-backed dropdown that displays academic definitions and citations, ensuring scholarly rigor without requiring external service dependencies.

**Ontology**: [semantic-change-ontology-v2.ttl](ontologies/semantic-change-ontology-v2.ttl)
**Validation**: [VALIDATION_GUIDE.md](VALIDATION_GUIDE.md)

---

## Demonstration

Live System: https://ontextract.ontorealm.net

Local Installation:
```bash
# Clone repository
cd OntExtract

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.template .env
# Edit .env and add your ANTHROPIC_API_KEY (optional, for API-enhanced mode)

# Run application
FLASK_ENV=development python run.py

# Access at: http://localhost:8765
```

Try the Workflow:

API-Enhanced Mode (with ANTHROPIC_API_KEY):
1. Create an experiment describing your research goals
2. Upload historical documents (PDF, TXT)
3. Review LLM-recommended processing strategy
4. Execute tools and view results
5. Read synthesized cross-document insights

Standalone Mode (without API key):
1. Upload historical documents (PDF, TXT)
2. Manually select processing tools for each document
3. Execute tools and view results
4. Analyze results through interface

---

## Impact and Applications

Digital Humanities:
- Accelerate historical document analysis
- Enable reproducible computational methods
- Lower barriers to NLP tool adoption

Scholarly Communication:
- Transparent provenance for all computational steps
- Auditable analysis workflows
- Shareable processing strategies

Interdisciplinary Research:
- Bridge gap between humanities research questions and NLP capabilities
- Reduce technical expertise requirements
- Focus researchers on interpretation rather than tool configuration

---

## Publications

JCDL 2025 Paper: "LLM-Orchestrated Document Processing: Intelligent Tool Selection for Historical Text Analysis"
