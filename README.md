# OntExtract

**Status:** Production Ready (Session 11)
**Branch:** `development`

Ontology extraction platform with intelligent LLM-orchestrated processing workflows.

---

## Quick Start

```bash
# Clone and setup
cd /home/chris/OntExtract
source venv-ontextract/bin/activate

# Run application
FLASK_ENV=development FLASK_DEBUG=1 python run.py

# Access at: http://localhost:5001

# Run tests
PYTHONPATH=/home/chris/OntExtract venv-ontextract/bin/pytest tests/ -v
```

---

## Features

### 1. LLM-Orchestrated Analysis ✨
5-stage intelligent workflow from JCDL 2025 paper:
- **Analyze** - LLM understands experiment goals
- **Recommend** - LLM suggests optimal processing tools per document
- **Review** - Human approves/modifies strategy
- **Execute** - Tools process documents
- **Synthesize** - LLM generates cross-document insights

### 2. Robust Error Handling
- 5-minute timeouts with 3 automatic retries
- Exponential backoff for transient failures
- User-friendly error messages with retry buttons
- Partial processing detection and warnings

### 3. Comprehensive Testing
- 68 automated tests (85% passing)
- Unit, integration, and API endpoint coverage
- PostgreSQL test infrastructure

### 4. Processing Tools
8 NLP tools for document analysis:
- Named Entity Recognition (SpaCy)
- Temporal Expression Extraction
- Definition Extraction
- Text Segmentation
- Embedding Generation
- LLM Text Cleanup

---

## Documentation

- **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - Commands, API, troubleshooting
- **[PROGRESS.md](PROGRESS.md)** - Session history, current status
- **[LLM_WORKFLOW_REFERENCE.md](LLM_WORKFLOW_REFERENCE.md)** - Workflow architecture
- **[LLM_ANALYZE_TEST_SUMMARY.md](LLM_ANALYZE_TEST_SUMMARY.md)** - Test details

---

## Architecture

**Backend:**
- Flask application with PostgreSQL
- LangGraph for workflow orchestration
- Claude Sonnet 4 for LLM tasks
- SQLAlchemy ORM

**Frontend:**
- Bootstrap 5 UI
- JavaScript orchestration client
- Real-time progress tracking
- Markdown rendering for insights

**Testing:**
- pytest with Flask-Testing
- PostgreSQL test database
- Transaction isolation

---

## Recent Updates

### Session 11 (2025-11-20)
- ✅ UI error handling complete
- ✅ Enhanced error display with retry buttons
- ✅ Partial processing warnings
- ✅ 5 new tests for status checking

### Session 10 (2025-11-20)
- ✅ 68-test suite created
- ✅ Backend error handling (timeout + retry)
- ✅ Test infrastructure fixed

### Session 8 (2025-11-20)
- ✅ LLM Analyze feature fully implemented
- ✅ 6 API endpoints created
- ✅ Progress tracking and strategy review UI

---

## Next Steps

1. Manual testing of error handling flows
2. Fix 4 remaining test failures
3. Implement workflow cancellation
4. Production deployment

---

**License:** [Your License]
**Contributors:** Chris + Claude
**Contact:** [Your Contact]
