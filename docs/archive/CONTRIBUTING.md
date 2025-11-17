# Contributing to OntExtract

Thank you for your interest in contributing to OntExtract! This document provides guidelines and standards for contributing to the project.

---

## Table of Contents

- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Coding Standards](#coding-standards)
- [Testing Requirements](#testing-requirements)
- [Git Workflow](#git-workflow)
- [Pull Request Process](#pull-request-process)
- [Code Review Guidelines](#code-review-guidelines)

---

## Getting Started

### Prerequisites

- **Python**: 3.11 or higher
- **PostgreSQL**: 14+ with pgvector extension
- **Redis**: 7+ (for caching)
- **Git**: 2.30+

### First-Time Setup

1. **Fork and clone the repository**:
   ```bash
   git clone https://github.com/your-username/OntExtract.git
   cd OntExtract
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

4. **Set up pre-commit hooks**:
   ```bash
   pre-commit install
   ```

5. **Configure environment variables**:
   ```bash
   cp .env.example .env  # Create from example if available
   # Edit .env with your configuration
   ```

6. **Initialize the database**:
   ```bash
   flask db upgrade
   flask init-db
   ```

7. **Run tests to verify setup**:
   ```bash
   pytest
   ```

---

## Development Setup

### Running the Development Server

```bash
python run.py
```

The application will be available at `http://localhost:8765`

### Database Migrations

**Create a new migration**:
```bash
flask db migrate -m "Description of changes"
```

**Apply migrations**:
```bash
flask db upgrade
```

**Rollback migrations**:
```bash
flask db downgrade
```

### Running Tests

**Run all tests**:
```bash
pytest
```

**Run with coverage**:
```bash
pytest --cov=app --cov=shared_services --cov-report=html
```

**Run specific test file**:
```bash
pytest tests/test_experiment.py
```

**Run tests matching a pattern**:
```bash
pytest -k "test_create_experiment"
```

---

## Coding Standards

### Python Style Guide

We follow **PEP 8** with some modifications defined in `pyproject.toml`. Our code is automatically formatted with **Ruff**.

#### Key Principles

1. **Readability over cleverness**
2. **Explicit is better than implicit**
3. **Simple is better than complex**
4. **Flat is better than nested**

### File Organization

#### Maximum File Sizes
- **Routes**: 400 lines maximum
- **Services**: 400 lines maximum
- **Models**: 300 lines maximum
- **Utilities**: 200 lines maximum

If a file exceeds these limits, it should be split into multiple modules.

#### Naming Conventions

**Files and Modules**:
```python
# Good
user_service.py
experiment_repository.py
oed_api_client.py

# Bad
UserService.py
experimentRepo.py
OEDClient.py
```

**Classes**:
```python
# Good
class UserRepository:
class ExperimentService:
class OEDAPIClient:

# Bad
class user_repository:
class experimentService:
class Oed_Api_Client:
```

**Functions and Methods**:
```python
# Good
def get_user_by_id(user_id: int) -> User | None:
def process_document(document: Document) -> ProcessingResult:

# Bad
def GetUserById(UserId):
def ProcessDoc(doc):
```

**Constants**:
```python
# Good
MAX_FILE_SIZE = 16 * 1024 * 1024
DEFAULT_TIMEOUT = 30

# Bad
max_file_size = 16777216
defaultTimeout = 30
```

### Type Hints

**All public functions and methods must have type hints**:

```python
# Good ✅
from typing import Any

def create_experiment(
    title: str,
    description: str | None = None,
    config: dict[str, Any] | None = None
) -> Experiment:
    """Create a new experiment.

    Args:
        title: The experiment title
        description: Optional description
        config: Optional configuration dictionary

    Returns:
        The created Experiment instance

    Raises:
        ValueError: If title is empty
    """
    ...

# Bad ❌
def create_experiment(title, description=None, config=None):
    ...
```

**Use modern type syntax (Python 3.10+)**:

```python
# Good ✅ (Python 3.10+)
def process(data: dict[str, Any]) -> list[Result] | None:
    ...

# Acceptable (for compatibility)
from typing import Dict, List, Optional, Any

def process(data: Dict[str, Any]) -> Optional[List[Result]]:
    ...
```

### Docstrings

**Use Google-style docstrings** for all public classes, functions, and methods:

```python
def enrich_metadata(
    reference: Reference,
    sources: list[str] | None = None
) -> EnrichmentResult:
    """Enrich reference metadata from external sources.

    This function queries multiple external APIs (OED, Zotero) to
    enhance the reference metadata with additional information.

    Args:
        reference: The reference to enrich
        sources: Optional list of sources to query. If None, queries all.
            Valid values: ["oed", "zotero", "google"]

    Returns:
        EnrichmentResult containing:
            - enriched_reference: The updated reference
            - sources_used: List of sources that provided data
            - confidence: Confidence score (0.0-1.0)

    Raises:
        APIConnectionError: If all external APIs are unavailable
        InvalidReferenceError: If the reference is missing required fields

    Example:
        >>> ref = Reference(title="Machine Learning Basics")
        >>> result = enrich_metadata(ref, sources=["oed"])
        >>> print(result.confidence)
        0.95
    """
    ...
```

### Error Handling

#### Use Specific Exceptions

```python
# Good ✅
try:
    user = user_repository.get_by_id(user_id)
except UserNotFoundError:
    logger.warning(f"User not found: {user_id}")
    return error_response("User not found", 404)
except DatabaseConnectionError as e:
    logger.error(f"Database error: {e}", exc_info=True)
    return error_response("Database unavailable", 503)

# Bad ❌
try:
    user = user_repository.get_by_id(user_id)
except Exception as e:
    return error_response(str(e), 500)
```

#### Always Log Exceptions

```python
# Good ✅
try:
    result = process_document(doc)
except ProcessingError as e:
    logger.exception(f"Failed to process document {doc.id}")
    raise

# Bad ❌
try:
    result = process_document(doc)
except ProcessingError:
    pass  # Silent failure
```

### Logging

**Use structured logging throughout**:

```python
import logging

logger = logging.getLogger(__name__)

# Good ✅
logger.info(
    "Experiment created",
    extra={
        "experiment_id": experiment.id,
        "user_id": current_user.id,
        "document_count": len(experiment.documents)
    }
)

# Also good ✅
logger.error(
    f"Failed to process document {doc.id}",
    exc_info=True,
    extra={"document_id": doc.id, "user_id": user.id}
)

# Bad ❌
print(f"Created experiment {experiment.id}")
```

**Logging Levels**:
- `DEBUG`: Detailed diagnostic information
- `INFO`: General informational messages (user actions, state changes)
- `WARNING`: Warning messages (deprecated features, potential issues)
- `ERROR`: Error messages (recoverable errors)
- `CRITICAL`: Critical errors (application failure)

### Code Organization

#### Layered Architecture

```
routes/          → HTTP request/response handling only
  ├── experiments.py
  └── processing.py

services/        → Business logic
  ├── experiment_service.py
  └── processing_service.py

repositories/    → Database access
  ├── experiment_repository.py
  └── document_repository.py

models/          → Database models
  ├── experiment.py
  └── document.py
```

**Routes should be thin**:

```python
# Good ✅
@experiments_bp.route('/', methods=['POST'])
@login_required
def create_experiment():
    """Create a new experiment endpoint."""
    try:
        data = request.get_json()
        experiment = experiment_service.create(
            title=data['title'],
            description=data.get('description'),
            user_id=current_user.id
        )
        return jsonify(experiment.to_dict()), 201
    except ValidationError as e:
        return error_response(str(e), 400)
    except Exception as e:
        logger.exception("Failed to create experiment")
        return error_response("Internal server error", 500)

# Bad ❌
@experiments_bp.route('/', methods=['POST'])
def create_experiment():
    """Create a new experiment endpoint."""
    data = request.get_json()

    # Validation logic (should be in service)
    if not data.get('title'):
        return jsonify({'error': 'Title required'}), 400

    # Business logic (should be in service)
    experiment = Experiment(
        title=data['title'],
        description=data.get('description'),
        created_by=current_user.id
    )

    # Direct database access (should be in repository)
    db.session.add(experiment)
    db.session.commit()

    return jsonify(experiment.to_dict()), 201
```

---

## Testing Requirements

### Test Coverage

- **Minimum coverage**: 70% overall
- **New code**: Must have 80%+ coverage
- **Critical paths**: Must have 90%+ coverage

### Test Structure

**Organize tests by layer**:

```
tests/
├── unit/
│   ├── test_services/
│   ├── test_repositories/
│   └── test_models/
├── integration/
│   ├── test_routes/
│   └── test_database/
└── e2e/
    └── test_workflows/
```

### Writing Tests

**Use pytest fixtures and factories**:

```python
import pytest
from tests.factories import UserFactory, ExperimentFactory

def test_create_experiment(client, db_session):
    """Test experiment creation endpoint."""
    # Arrange
    user = UserFactory()
    data = {
        'title': 'Test Experiment',
        'description': 'A test experiment'
    }

    # Act
    response = client.post(
        '/experiments/',
        json=data,
        headers={'Authorization': f'Bearer {user.token}'}
    )

    # Assert
    assert response.status_code == 201
    assert response.json['title'] == data['title']

    # Verify database state
    experiment = Experiment.query.filter_by(title=data['title']).first()
    assert experiment is not None
    assert experiment.created_by == user.id
```

**Test naming convention**:

```python
# Pattern: test_<function>_<scenario>_<expected_result>

def test_create_experiment_valid_data_returns_201():
    """Test that creating an experiment with valid data returns 201."""
    ...

def test_create_experiment_missing_title_returns_400():
    """Test that creating an experiment without title returns 400."""
    ...

def test_get_experiment_nonexistent_id_returns_404():
    """Test that getting a nonexistent experiment returns 404."""
    ...
```

### Test Markers

Use pytest markers to categorize tests:

```python
import pytest

@pytest.mark.unit
def test_user_model_creation():
    """Unit test for User model."""
    ...

@pytest.mark.integration
@pytest.mark.requires_db
def test_experiment_crud_operations():
    """Integration test for experiment CRUD."""
    ...

@pytest.mark.slow
def test_large_document_processing():
    """Test processing of large documents."""
    ...
```

Run specific test categories:
```bash
pytest -m unit          # Run only unit tests
pytest -m "not slow"    # Skip slow tests
pytest -m integration   # Run only integration tests
```

---

## Git Workflow

### Branch Naming

```
feature/experiment-versioning
bugfix/user-authentication-error
refactor/split-experiments-route
docs/update-api-documentation
test/add-experiment-tests
```

### Commit Messages

Follow the **Conventional Commits** specification:

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `refactor`: Code refactoring (no functional changes)
- `test`: Adding or updating tests
- `docs`: Documentation changes
- `style`: Code style changes (formatting, no logic changes)
- `perf`: Performance improvements
- `chore`: Build process or auxiliary tool changes

**Examples**:

```
feat(experiments): add document versioning support

Implement document versioning within experiments to track
changes over time. Includes:
- New DocumentVersion model
- Versioning service
- API endpoints for version management

Closes #123
```

```
fix(auth): prevent duplicate user registrations

Add unique constraint on email field and handle
IntegrityError in registration endpoint.

Fixes #456
```

```
refactor(routes): split experiments.py into modules

Break down experiments.py (2,239 lines) into:
- experiments/crud.py
- experiments/processing.py
- experiments/analytics.py

Part of #789 (Phase 1 refactoring)
```

### Commit Hygiene

1. **Keep commits atomic**: One logical change per commit
2. **Write descriptive messages**: Explain why, not just what
3. **Reference issues**: Use `Closes #123`, `Fixes #456`, `Refs #789`
4. **Avoid "WIP" commits**: Squash before creating PR

---

## Pull Request Process

### Before Creating a PR

**Checklist**:
- [ ] All tests pass: `pytest`
- [ ] Code coverage meets minimum: `pytest --cov`
- [ ] Linting passes: `ruff check .`
- [ ] Type checking passes: `mypy app/`
- [ ] Pre-commit hooks pass: `pre-commit run --all-files`
- [ ] Documentation updated (if needed)
- [ ] CHANGELOG updated (for user-facing changes)

### Creating a PR

1. **Use the PR template** (auto-populated)
2. **Write a clear title**: Same format as commit messages
3. **Provide context**: Explain what, why, and how
4. **Link related issues**: Use keywords (`Closes #123`)
5. **Add screenshots**: For UI changes
6. **Mark as draft**: If work is incomplete

### PR Size Guidelines

- **Small**: <200 lines changed (preferred)
- **Medium**: 200-500 lines changed (acceptable)
- **Large**: 500-1000 lines changed (needs justification)
- **Huge**: >1000 lines changed (should be split)

If your PR is large, consider:
- Breaking it into multiple smaller PRs
- Creating a parent issue to track the overall feature

---

## Code Review Guidelines

### For Authors

1. **Respond promptly** to review comments
2. **Be open to feedback** and willing to make changes
3. **Ask questions** if feedback is unclear
4. **Mark conversations** as resolved after addressing
5. **Request re-review** after making significant changes

### For Reviewers

1. **Be respectful and constructive**
   - ✅ "Consider extracting this into a separate method for clarity"
   - ❌ "This code is terrible"

2. **Provide context** for your suggestions
   - Explain why a change is needed
   - Link to documentation or examples

3. **Distinguish between**:
   - **Must fix**: Bugs, security issues, violations of standards
   - **Should fix**: Code quality improvements
   - **Could fix**: Stylistic suggestions (use "nit:")

4. **Approve when ready**:
   - All critical issues resolved
   - Tests pass and coverage is adequate
   - Code meets standards

---

## Additional Resources

- [Python Type Hints](https://docs.python.org/3/library/typing.html)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [Flask Best Practices](https://flask.palletsprojects.com/en/latest/patterns/)
- [SQLAlchemy Best Practices](https://docs.sqlalchemy.org/en/20/orm/queryguide/index.html)
- [Pytest Documentation](https://docs.pytest.org/)

---

## Questions?

If you have questions about contributing:
1. Check existing documentation
2. Search closed issues
3. Ask in discussions
4. Open a new issue with the `question` label

---

**Thank you for contributing to OntExtract! 🎉**
