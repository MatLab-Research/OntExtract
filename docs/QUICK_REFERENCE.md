# OntExtract Quick Reference

**Last Updated:** 2025-11-20 (Session 11)
**Branch:** `development`
**Status:** Production Ready - UI Error Handling Complete

---

## Running the Application

```bash
# Start Flask app (WSL)
cd /home/chris/OntExtract
source venv-ontextract/bin/activate
FLASK_ENV=development FLASK_DEBUG=1 python run.py

# Access at: http://localhost:5001
```

## Running Tests

```bash
# All tests with coverage
PYTHONPATH=/home/chris/OntExtract venv-ontextract/bin/pytest tests/ --cov=app --cov-report=html

# Specific test suites
PYTHONPATH=/home/chris/OntExtract venv-ontextract/bin/pytest tests/test_llm_orchestration_api.py -v
PYTHONPATH=/home/chris/OntExtract venv-ontextract/bin/pytest tests/test_workflow_executor.py -v

# Check-status endpoint tests (5 tests, all passing)
PYTHONPATH=/home/chris/OntExtract venv-ontextract/bin/pytest tests/test_llm_orchestration_api.py::test_check_status_no_processing -v
```

**Current Test Status:** 68 tests written, ~85% passing

---

## LLM Analyze Feature Architecture

### 5-Stage Workflow (from JCDL Paper)

```
START → Analyze → Recommend → Review → Execute → Synthesize
         (1)        (2)         (3)      (4)        (5)
```

1. **Analyze**: LLM analyzes experiment goals + documents
2. **Recommend**: LLM suggests processing tools per document
3. **Review**: User approves/modifies strategy
4. **Execute**: Tools process documents with approved strategy
5. **Synthesize**: LLM generates cross-document insights + PROV-O

### Key Components

**Backend:**
- `app/services/workflow_executor.py` - Main orchestration service (Singleton)
- `app/orchestration/experiment_graph.py` - LangGraph StateGraph
- `app/orchestration/experiment_nodes.py` - 5 LLM node implementations
- `app/routes/experiments/orchestration.py` - 6 API endpoints

**Frontend:**
- `app/static/js/llm_orchestration.js` - Orchestration client with polling
- `app/templates/experiments/document_pipeline.html` - UI modals

**Database:**
- `ExperimentOrchestrationRun` model - Stores workflow state + results

### API Endpoints

```
POST   /experiments/<id>/orchestration/analyze           # Start workflow
GET    /experiments/<id>/orchestration/check-status      # Check existing processing
GET    /orchestration/status/<run_id>                    # Poll status
POST   /orchestration/approve-strategy/<run_id>          # Approve & execute
GET    /experiments/<id>/orchestration/llm-results/<run_id>      # Results page
GET    /experiments/<id>/orchestration/llm-provenance/<run_id>   # PROV-O JSON
```

---

## Error Handling Configuration

### Backend (Session 10)

**Config:** `app/orchestration/config.py`
- `LLM_TIMEOUT_SECONDS` - Timeout for LLM calls (default: 300s/5min)
- `LLM_MAX_RETRIES` - Max retry attempts (default: 3)
- `LLM_RETRY_INITIAL_DELAY` - Initial retry delay (default: 2s)
- `LLM_RETRY_MAX_DELAY` - Max retry delay (default: 60s)

**Retry Logic:** `app/orchestration/retry_utils.py`
- Exponential backoff with jitter
- Smart error detection (429, 500-504 = retriable)
- Comprehensive logging

### Frontend (Session 11)

**Error Types:**
- `timeout` - LLM exceeded timeout → Show retry button
- `rate_limit` - 429 error → Show retry button
- `server_error` - 500/503 error → Show retry button
- `llm_error` - LLM processing failed → No retry
- `general` - Unknown error → No retry

**User Flows:**
- Error display in modal (header turns red)
- User-friendly messages + technical details
- Retry button for retriable errors
- Partial processing warning before orchestration

---

## Key Technical Patterns

### LangGraph State Management
- Progressive fields MUST be Optional (not empty values)
- Use `state.update()` to merge, never replace state
- Critical keys must persist: documents, experiment_id, run_id

### Document Model Fields
- `original_filename` (not `source`)
- `created_at` (not `upload_date`)
- `content_type` (required for all documents)

### Test Database
- Uses scoped_session for transaction isolation
- All Document fixtures need `content_type='text/plain'`
- TextSegment requires `content` field (not `segment_text`)

---

## Current Priorities

### High Priority
1. **Fix 4 remaining test failures** - Relationship loading issues in integration tests
2. **Workflow cancellation** - Add cancel button to progress modal
3. **Full test suite run** - Validate all 68 tests

### Medium Priority
4. **Production deployment** - Test with real LLM API
5. **Concurrent run handling** - Multiple simultaneous orchestrations
6. **Processing pipeline testing** - Test all 8 tools end-to-end

### Optional
7. **UI enhancements** - Elapsed time, progress animations
8. **Performance** - Load testing, optimization
9. **Monitoring** - Error dashboards, metrics

---

## Troubleshooting

### Common Issues

**Test failures with "relationship loading":**
- Use `Document.query.filter_by(experiment_id=X).all()` instead of `experiment.documents`
- Force flush before accessing relationships: `db_session.flush()`

**ProcessingArtifact creation errors:**
- Requires `processing_id` (UUID from ExperimentDocumentProcessing)
- Use `ProcessingJob` for simpler testing

**Modal not showing:**
- Check Bootstrap initialization: `new bootstrap.Modal(element)`
- Ensure element IDs match JavaScript selectors
- Check for duplicate event listeners

### Useful Commands

```bash
# Check model fields
PYTHONPATH=/home/chris/OntExtract venv-ontextract/bin/python -c "from app.models import Document; print([c.name for c in Document.__table__.columns])"

# View database migrations
.venv/bin/flask db history

# Create new migration
.venv/bin/flask db migrate -m "description"

# Apply migrations
.venv/bin/flask db upgrade
```

---

**See Also:**
- [PROGRESS.md](PROGRESS.md) - Detailed session history
- [LLM_ANALYZE_TEST_SUMMARY.md](LLM_ANALYZE_TEST_SUMMARY.md) - Test suite details
- [LLM_ERROR_HANDLING_IMPLEMENTATION.md](LLM_ERROR_HANDLING_IMPLEMENTATION.md) - Error handling implementation
