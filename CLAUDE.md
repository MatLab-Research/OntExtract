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

### Next Development Steps

1. Complete temporal_extractor.py implementation
2. Implement semantic evolution tracking algorithms
3. Create PROV-O entity tracking system
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
