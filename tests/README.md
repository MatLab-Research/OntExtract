# OntExtract Test Suite

This directory contains comprehensive tests for the OntExtract application.

## Test Structure

```
tests/
├── conftest.py                              # Shared fixtures and configuration
├── helpers.py                               # Test helper utilities
├── test_temporal_experiment_integration.py  # Main integration tests
├── test_experiments_crud.py                 # Experiment CRUD operations
├── test_historical_pipeline.py              # Historical document processing
├── test_langgraph_orchestration.py         # LangGraph workflow tests
├── test_orchestration_from_db.py           # Database integration tests
└── ...
```

## Running Tests

### Prerequisites

1. Install test dependencies:
```bash
pip install pytest pytest-flask pytest-cov
```

2. Ensure database is accessible (tests use in-memory SQLite by default)

3. Set environment variables (optional):
```bash
export FLASK_ENV=testing
export TESTING=True
```

### Run All Tests

```bash
# From project root
pytest tests/

# With verbose output
pytest tests/ -v

# With coverage report
pytest tests/ --cov=app --cov-report=html
```

### Run Specific Test Files

```bash
# Run integration tests
pytest tests/test_temporal_experiment_integration.py -v

# Run CRUD tests
pytest tests/test_experiments_crud.py -v

# Run historical pipeline tests
pytest tests/test_historical_pipeline.py -v
```

### Run Specific Test Classes or Functions

```bash
# Run specific test class
pytest tests/test_temporal_experiment_integration.py::TestTemporalExperimentWorkflow -v

# Run specific test function
pytest tests/test_temporal_experiment_integration.py::TestTemporalExperimentWorkflow::test_complete_temporal_workflow -v
```

### Filter by Markers

Tests are marked with custom markers for organization:

```bash
# Run only integration tests
pytest tests/ -m integration

# Run only unit tests
pytest tests/ -m unit

# Skip tests requiring LLM API
pytest tests/ -m "not requires_llm"
```

## Test Markers

- `@pytest.mark.integration` - Integration tests (test full stack)
- `@pytest.mark.unit` - Unit tests (test individual components)
- `@pytest.mark.requires_llm` - Tests requiring LLM API access

## Test Coverage

### Main Integration Test

`test_temporal_experiment_integration.py::TestTemporalExperimentWorkflow::test_complete_temporal_workflow`

This test covers the complete workflow:

1. ✅ Creating a temporal evolution experiment
2. ✅ Uploading 5 documents
3. ✅ Linking documents to experiment
4. ✅ Running segmentation on all documents
5. ✅ Running entity extraction on all documents
6. ✅ Running embeddings on all documents
7. ✅ Verifying results are stored correctly
8. ✅ Verifying provenance tracking

### What's Tested

**Experiment Operations:**
- Creating experiments (temporal_evolution, entity_extraction)
- Linking documents to experiments
- Managing experiment status
- Retrieving experiment data

**Document Operations:**
- Uploading documents
- Document versioning (one version per experiment)
- Content storage and retrieval

**Processing Operations:**
- Text segmentation (paragraph, sentence)
- Entity extraction (spaCy)
- Embedding generation
- Processing artifact storage

**Provenance Tracking:**
- PROV-O activity recording
- PROV-O entity tracking
- Processing history

## Fixtures Available

### From conftest.py

**Application Fixtures:**
- `app` - Flask application instance (session scope)
- `db_session` - Database session with automatic rollback (function scope)
- `client` - Unauthenticated test client
- `auth_client` - Authenticated test client

**User Fixtures:**
- `test_user` - Standard test user
- `admin_user` - Admin user for permission testing

**Document Fixtures:**
- `sample_document` - Single test document
- `sample_documents` - List of 5 documents with realistic content

**Experiment Fixtures:**
- `sample_term` - Sample term for temporal experiments
- `temporal_experiment` - Temporal evolution experiment
- `entity_extraction_experiment` - Entity extraction experiment

**File Fixtures:**
- `sample_txt_file` - BytesIO text file for upload
- `sample_pdf_file` - BytesIO PDF file for upload

### From helpers.py

**Document Generators:**
- `generate_temporal_document_content()` - Generate period-specific content
- `create_test_documents()` - Create multiple documents

**Experiment Helpers:**
- `create_experiment_with_documents()` - Create experiment + docs
- `set_experiment_status()` - Update experiment status

**API Helpers:**
- `upload_document_via_api()` - Upload via API
- `run_segmentation()` - Run segmentation tool
- `run_entity_extraction()` - Run entity extraction
- `run_embeddings()` - Generate embeddings

## Writing New Tests

### Example: Test a New Processing Tool

```python
import pytest
from tests.helpers import create_experiment_with_documents

@pytest.mark.integration
def test_new_processing_tool(auth_client, db_session, test_user):
    """Test the new processing tool."""

    # Create experiment with documents
    experiment, documents = create_experiment_with_documents(
        db_session,
        test_user,
        experiment_type='temporal_evolution',
        document_count=3
    )

    # Run new tool on first document
    doc = documents[0]
    response = auth_client.post(
        f'/process/document/{doc.uuid}/new-tool',
        json={'method': 'test', 'experiment_id': experiment.id}
    )

    assert response.status_code == 200
    # Add more assertions...
```

## Troubleshooting

### Import Errors

If you see `ModuleNotFoundError: No module named 'app'`:

```bash
# Run from project root
cd /home/user/OntExtract
pytest tests/

# Or set PYTHONPATH
export PYTHONPATH=/home/user/OntExtract:$PYTHONPATH
```

### Database Errors

If you see database connection errors:

- Tests use in-memory SQLite by default (no setup needed)
- Check `config/__init__.py` TestingConfig
- Ensure no conflicting DATABASE_URL environment variable

### Fixture Errors

If fixtures aren't found:

- Ensure `conftest.py` is in the tests directory
- Check fixture names match between test and conftest.py
- Use `pytest --fixtures` to list available fixtures

### Test Failures

If tests fail due to missing dependencies:

```bash
# Install required packages
pip install nltk spacy
python -m spacy download en_core_web_sm

# For sentence-transformers
pip install sentence-transformers
```

## Continuous Integration

Add to your CI pipeline:

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov
      - name: Run tests
        run: pytest tests/ --cov=app --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

## Next Steps

1. **Expand test coverage** - Fill in TODO tests in `test_experiments_crud.py`
2. **Add performance tests** - Test with larger documents and more operations
3. **Add edge case tests** - Test error conditions and boundary cases
4. **Add API documentation tests** - Ensure API responses match documentation
5. **Add security tests** - Test authentication and authorization

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [Flask testing](https://flask.palletsprojects.com/en/2.3.x/testing/)
- [pytest-flask](https://pytest-flask.readthedocs.io/)
