# Getting Started with OntExtract Tests

## Quick Start

The integration tests are now ready to use! Here's how to run them:

### 1. Install Test Dependencies

```bash
# Make sure you're in the project root
cd /home/user/OntExtract

# Install test dependencies (if not already installed)
pip install pytest pytest-flask pytest-cov
```

### 2. Run the Main Integration Test

This tests your complete temporal analysis workflow (create experiment → upload 5 docs → run tools):

```bash
# Set PYTHONPATH so tests can import the app
export PYTHONPATH=/home/user/OntExtract:$PYTHONPATH

# Run the integration test
pytest tests/test_temporal_experiment_integration.py::TestTemporalExperimentWorkflow::test_complete_temporal_workflow -v

# Or run all integration tests
pytest tests/test_temporal_experiment_integration.py -v
```

### 3. Expected Output

When the test runs successfully, you should see output like:

```
================================ test session starts =================================
collected 1 item

tests/test_temporal_experiment_integration.py::TestTemporalExperimentWorkflow::test_complete_temporal_workflow PASSED

✓ Created experiment: Algorithm Evolution Study (ID: 1)
✓ Uploaded 5 documents
✓ Linked 5 documents to experiment
✓ Ran segmentation on 5 documents
✓ Ran entity extraction on 5 documents
✓ Ran embeddings on 5 documents
✓ Found 15 processing records
✓ Found 45 processing artifacts
✓ Found 20 provenance activities
✓ Found 5 provenance entities

======================================================================
✓ TEMPORAL EXPERIMENT WORKFLOW TEST PASSED
======================================================================
Experiment: Algorithm Evolution Study
Documents: 5
Segmentations: 5
Entity Extractions: 5
Embeddings: 5
Processing Records: 15
Provenance Activities: 20
======================================================================

================================ 1 passed in 5.23s ==================================
```

## What the Test Covers

The main integration test (`test_complete_temporal_workflow`) tests:

1. ✅ **Create Experiment**: Creates a temporal_evolution experiment via API
2. ✅ **Upload Documents**: Uploads 5 documents with realistic content
3. ✅ **Link to Experiment**: Associates documents with the experiment
4. ✅ **Run Segmentation**: Paragraph segmentation on all 5 documents
5. ✅ **Run Entity Extraction**: spaCy entity extraction on all 5 documents
6. ✅ **Run Embeddings**: Local embedding generation on all 5 documents
7. ✅ **Verify Results**: Checks that processing records are created
8. ✅ **Verify Provenance**: Validates PROV-O tracking is working

## Files Created

### Core Test Infrastructure

- **`tests/conftest.py`** - Shared fixtures for all tests
  - Flask app setup with in-memory SQLite
  - Database fixtures with automatic rollback
  - Authenticated test client
  - Sample data fixtures (users, documents, experiments)

- **`tests/helpers.py`** - Test helper utilities
  - Document content generators
  - API request helpers
  - Assertion helpers
  - Time period utilities

- **`tests/test_temporal_experiment_integration.py`** - Main integration tests
  - `TestTemporalExperimentWorkflow` - Complete workflow test
  - `TestExperimentDocumentProcessing` - Individual tool tests
  - `TestExperimentVersioning` - Versioning system tests
  - `TestExperimentResultsRetrieval` - Results viewing tests

### Documentation

- **`tests/README.md`** - Comprehensive test documentation
- **`tests/GETTING_STARTED.md`** - This quick start guide

## Running Other Tests

### Run All Tests

```bash
export PYTHONPATH=/home/user/OntExtract:$PYTHONPATH
pytest tests/ -v
```

### Run Specific Test Class

```bash
pytest tests/test_temporal_experiment_integration.py::TestExperimentDocumentProcessing -v
```

### Run with Coverage Report

```bash
pytest tests/ --cov=app --cov-report=html
# Open htmlcov/index.html in browser to see coverage
```

### Run Only Integration Tests

```bash
pytest tests/ -m integration -v
```

## Troubleshooting

### Issue: ModuleNotFoundError: No module named 'app'

**Solution**: Set PYTHONPATH before running tests:
```bash
export PYTHONPATH=/home/user/OntExtract:$PYTHONPATH
```

Or add it to your shell profile (~/.bashrc or ~/.zshrc):
```bash
echo 'export PYTHONPATH=/home/user/OntExtract:$PYTHONPATH' >> ~/.bashrc
```

### Issue: ModuleNotFoundError: No module named 'flask'

**Solution**: Install dependencies:
```bash
pip install -r requirements.txt
```

### Issue: Database connection errors

**Solution**: Tests use in-memory SQLite by default, so no database setup is needed. If you see errors, check that `TESTING=True` is set:
```bash
export TESTING=True
export FLASK_ENV=testing
```

### Issue: spaCy model not found

**Solution**: Download the English language model:
```bash
python -m spacy download en_core_web_sm
```

### Issue: NLTK data not found

**Solution**: Download required NLTK data:
```bash
python -c "import nltk; nltk.download('punkt'); nltk.download('averaged_perceptron_tagger')"
```

## Next Steps

### 1. Run the Tests

Try running the integration test to verify everything works:

```bash
export PYTHONPATH=/home/user/OntExtract:$PYTHONPATH
pytest tests/test_temporal_experiment_integration.py::TestTemporalExperimentWorkflow::test_complete_temporal_workflow -v -s
```

The `-s` flag shows print statements, so you can see progress messages.

### 2. Review Test Coverage

After running tests, check what's covered:

```bash
pytest tests/ --cov=app --cov-report=term-missing
```

This shows which lines of code aren't covered by tests.

### 3. Fill in TODO Tests

The file `tests/test_experiments_crud.py` has 53 TODO placeholders. You can use the integration test as a template to fill them in.

### 4. Add Custom Tests

Use the helpers and fixtures to create tests for your specific use cases:

```python
import pytest
from tests.helpers import create_experiment_with_documents

@pytest.mark.integration
def test_my_custom_workflow(auth_client, db_session, test_user):
    """Test my custom workflow."""

    # Create experiment with documents
    experiment, documents = create_experiment_with_documents(
        db_session,
        test_user,
        experiment_type='temporal_evolution',
        document_count=5
    )

    # Your test code here
    assert experiment is not None
    assert len(documents) == 5
```

## Benefits of These Tests

1. **Confidence**: Know that your core workflow works end-to-end
2. **Regression Prevention**: Catch bugs before they reach production
3. **Documentation**: Tests serve as executable documentation
4. **Refactoring Safety**: Change code with confidence
5. **CI/CD Ready**: Can be integrated into automated pipelines

## Integration with CI/CD

Add to `.github/workflows/test.yml`:

```yaml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v2

    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        python -m spacy download en_core_web_sm

    - name: Run tests
      run: |
        export PYTHONPATH=$PWD:$PYTHONPATH
        pytest tests/ -v --cov=app --cov-report=xml

    - name: Upload coverage
      uses: codecov/codecov-action@v2
```

## Questions or Issues?

If you encounter any issues with the tests:

1. Check `tests/README.md` for detailed documentation
2. Review the test code in `tests/test_temporal_experiment_integration.py`
3. Look at example fixtures in `tests/conftest.py`
4. Use helper functions from `tests/helpers.py`

Happy testing! 🚀
