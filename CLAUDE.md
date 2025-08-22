# OntExtract Development Notes

## Project Overview
OntExtract is a system for ontology extraction and temporal linguistic analysis from historical texts.

## Temporal Linguistic Analysis Pipeline

### Core Objective
Track linguistic evolution through historical texts (newspapers, period books) to analyze how word usage and meanings change over time, with entity-level PROV-O provenance tracking.

### Key Components

#### 1. Historical Document Processing (`shared_services/preprocessing/historical_processor.py`)
- **Temporal Metadata Extraction**: Extract publication dates, historical periods, confidence scores
- **Historical Spelling Normalization**: Convert archaic spellings (thou→you, hath→has, etc.)
- **Semantic Unit Extraction**: Identify articles in newspapers, chapters in books
- **OCR Error Correction**: Handle common OCR errors in historical texts

#### 2. Temporal Word Usage Extraction (To be implemented: `temporal_extractor.py`)
- **Usage Context Extraction**: Capture surrounding text windows
- **Collocation Analysis**: Track words appearing together
- **Syntactic Role Identification**: Analyze grammatical functions
- **Semantic Field Classification**: Group related concepts

#### 3. Semantic Evolution Tracking (To be implemented: `semantic_tracker.py`)
- **Semantic Drift Metrics**: Measure meaning changes over time
- **Meaning Clusters**: Identify different word senses by period
- **Emergent Meanings**: Detect new meanings appearing over time
- **Domain Migration**: Track shifts between usage domains

#### 4. Entity-Level PROV-O Tracking (To be implemented: `provenance_tracker.py`)
- **Entity Provenance**: Track extraction source and method
- **Temporal Context**: Document period and publication date
- **Confidence Scoring**: Quality metrics for extractions
- **Attribution Chain**: Full audit trail from source to result

#### 5. Pre-computed Comparison Features (To be implemented: `comparison_preprocessor.py`)
- **Vocabulary Profiles**: Unique terms, frequencies, archaic/modern ratio
- **Syntactic Patterns**: Sentence and phrase structures
- **Semantic Profiles**: Topic distributions, sentiment timelines
- **Temporal Markers**: Period indicators, anachronisms

#### 6. Google Services Integration (To be implemented: `google_integration.py`)
- **Document AI**: OCR, layout detection, table/form extraction
- **Natural Language API**: NER, sentiment, syntax analysis
- **Custom Historical NER**: Period-specific entity recognition

### Implementation Status

✅ **Completed**:
- Basic project structure and Docker deployment
- Admin account management system
- File type icon differentiation in UI
- Historical document processor core class
- **OntServe Integration** (2025-08-22): PROV-O access via centralized OntServe

#### OntServe Integration ✅ (2025-08-22)
- [x] **Enhanced OntologyImporter**: `shared_services/ontology/ontology_importer.py` now uses OntServe first
- [x] **Automatic Fallback**: Falls back to direct download when OntServe unavailable
- [x] **Backward Compatibility**: All existing PROV-O code works unchanged
- [x] **Performance Optimization**: Cached responses from OntServe, no more downloads/parsing
- [x] **Environment Configuration**: `USE_ONTSERVE=true`, `ONTSERVE_URL=http://localhost:8082`

🔄 **In Progress**:
- Temporal word usage extractor
- Semantic evolution tracker
- Entity provenance tracker

📋 **Pending**:
- Google services integration
- Comparison preprocessor
- Visualization layer for temporal evolution

### Technical Architecture

```
Input Documents (PDFs, scanned texts)
    ↓
Historical Document Processor
    ├── OCR & Layout Analysis
    ├── Temporal Metadata Extraction
    └── Historical Normalization
    ↓
Temporal Word Usage Extractor
    ├── Context Windows
    ├── Collocation Analysis
    └── Syntactic Analysis
    ↓
Semantic Evolution Tracker
    ├── Semantic Drift Calculation
    ├── Meaning Clustering
    └── Domain Migration Analysis
    ↓
PROV-O Provenance Layer
    ├── Entity-level tracking
    ├── Attribution chains
    └── Quality metrics
    ↓
Pre-computed Features
    ├── Embeddings
    ├── Statistical profiles
    └── Comparison vectors
    ↓
Storage & Analysis
```

### Key Design Decisions

1. **Entity-Level Provenance**: Each extracted term has full PROV-O tracking for scholarly attribution
2. **Historical Normalization**: Dual storage of original and normalized forms for accuracy
3. **Semantic Units**: Process documents at article/chapter level for better context
4. **Period-Aware Processing**: Different processing rules for different historical periods
5. **Hybrid NER**: Combine Google NLP with custom historical entity recognition

### Google Cloud Requirements

- Document AI API for OCR and layout analysis
- Natural Language API for modern NER and syntax
- Custom models for historical text processing
- Storage for large document collections

### Database Schema Considerations

- Temporal metadata tables for period classification
- Word usage tables with context and collocations
- Provenance tracking tables following PROV-O
- Pre-computed feature storage for fast comparison
- Semantic evolution metrics over time

### Deployment Notes

- Docker-based deployment with persistent volumes
- Admin account: Username "Wook", Password "ontology" (private, not in repo)
- Update mechanism preserves user data
- File type icons distinguish local files from external references (OED)

### OntServe Integration Architecture ✅ (2025-08-22)

OntExtract now integrates with OntServe for centralized PROV-O ontology access:

```
OntExtract ──→ OntExtract Client ──→ OntServe MCP Server ──→ PostgreSQL Database
    ↓              ↓                      ↓                        ↓
 Local Cache ←─ Response Cache ←─── Entity Storage ←───── PROV-O Concepts
```

#### Integration Features
- **OntServe-First Approach**: Try OntServe, fall back to direct download
- **Intelligent Caching**: 1-hour TTL cache for OntServe responses
- **Transparent Operation**: Existing code works unchanged
- **Environment Configuration**: `USE_ONTSERVE=true` enables integration
- **PROV-O Access**: 59+ classes and 69+ properties from centralized server

#### Usage Example
```python
# Existing code works unchanged - now uses OntServe when available
from shared_services.ontology.ontology_importer import OntologyImporter

importer = OntologyImporter()  # Auto-detects OntServe
result = importer.import_prov_o()

if result.get('from_ontserve'):
    print("✓ Using centralized OntServe")
else:
    print("⚠ Fell back to direct download")

# Access experiment concepts as before
concepts = result['experiment_concepts']
```

#### Configuration
```bash
# Enable OntServe integration
export USE_ONTSERVE=true
export ONTSERVE_URL=http://localhost:8082
export ONTSERVE_CACHE_TTL=3600  # 1 hour cache
```

### Next Development Steps

1. Complete temporal_extractor.py implementation
2. Implement semantic evolution tracking algorithms
3. **Leverage OntServe PROV-O**: Use centralized PROV-O entities for provenance tracking
4. Integrate Google Cloud services
5. Build visualization layer for temporal analysis
6. Add batch processing for large document collections

### Research Applications

- Track semantic drift in historical texts
- Analyze domain-specific language evolution
- Study emergence of new word meanings
- Compare language use across different periods
- Create temporal word usage databases
- Support digital humanities research

### Important Files

- `shared_services/preprocessing/historical_processor.py` - Core historical text processor
- `shared_services/temporal/temporal_analysis_service.py` - Temporal analysis utilities
- `setup_admin.sh.private` - Private admin creation script (not in repo)
- `install.sh` - One-command Docker installation
- `update.sh` - Git-based update mechanism
