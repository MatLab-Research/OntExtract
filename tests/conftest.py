"""
Test Configuration and Fixtures

Provides shared fixtures for all OntExtract tests including:
- Flask application setup
- Database fixtures
- Authenticated clients
- Sample data generators
"""

import pytest
import os
import tempfile
from io import BytesIO
from datetime import datetime

# Set test environment before importing app
os.environ['FLASK_ENV'] = 'testing'
os.environ['TESTING'] = 'True'

from app import create_app, db
from app.models.user import User
from app.models.document import Document
from app.models.experiment import Experiment
from app.models.term import Term


# ==============================================================================
# Application & Database Fixtures
# ==============================================================================

@pytest.fixture(scope='session')
def app():
    """
    Create and configure a Flask application instance for testing.
    Uses in-memory SQLite database for speed and isolation.
    """
    app = create_app('testing')

    # Ensure upload folder exists
    upload_folder = app.config.get('UPLOAD_FOLDER', 'uploads')
    os.makedirs(upload_folder, exist_ok=True)

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture(scope='function')
def db_session(app):
    """
    Provide a clean database session for each test.
    Automatically rolls back changes after each test.
    """
    with app.app_context():
        # Begin a transaction
        connection = db.engine.connect()
        transaction = connection.begin()

        # Bind session to this connection
        session = db.session

        yield session

        # Rollback transaction and close
        session.remove()
        transaction.rollback()
        connection.close()


# ==============================================================================
# Client Fixtures
# ==============================================================================

@pytest.fixture
def client(app):
    """
    Provide a test client for making requests without authentication.
    """
    return app.test_client()


@pytest.fixture
def auth_client(app, db_session, test_user):
    """
    Provide an authenticated test client.
    Uses Flask-Login to simulate a logged-in user.
    """
    client = app.test_client()

    with client.session_transaction() as sess:
        sess['_user_id'] = str(test_user.id)
        sess['_fresh'] = True

    return client


# ==============================================================================
# User Fixtures
# ==============================================================================

@pytest.fixture
def test_user(db_session):
    """
    Create a test user with active account.
    """
    user = User(
        username='testuser',
        email='test@example.com',
        password='testpass123',
        first_name='Test',
        last_name='User',
        is_active=True,
        account_status='active'
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def admin_user(db_session):
    """
    Create an admin user for permission testing.
    """
    user = User(
        username='admin',
        email='admin@example.com',
        password='adminpass123',
        is_active=True,
        is_admin=True,
        account_status='active'
    )
    db_session.add(user)
    db_session.commit()
    return user


# ==============================================================================
# Document Fixtures
# ==============================================================================

@pytest.fixture
def sample_document(db_session, test_user):
    """
    Create a single sample document for testing.
    """
    doc = Document(
        title='Test Document',
        content='This is test content for the document. ' * 20,
        document_type='document',
        status='completed',
        user_id=test_user.id,
        word_count=100
    )
    db_session.add(doc)
    db_session.commit()
    return doc


@pytest.fixture
def sample_documents(db_session, test_user):
    """
    Create 5 sample documents for batch testing.
    Each document has realistic content for temporal analysis.
    """
    documents = []

    sample_contents = [
        """
        The concept of algorithms has evolved significantly over time. In computer science,
        an algorithm is a step-by-step procedure for solving a problem or performing a task.
        Modern algorithms power everything from search engines to artificial intelligence systems.
        Understanding algorithmic complexity is essential for efficient software development.
        """,
        """
        Functions are fundamental building blocks in programming. A function encapsulates
        a specific task or computation, making code more modular and reusable. Functions can
        take parameters, perform operations, and return results. Good function design leads
        to cleaner, more maintainable codebases.
        """,
        """
        Data structures organize and store data efficiently in computer memory. Common data
        structures include arrays, linked lists, trees, and hash tables. Choosing the right
        data structure is crucial for algorithm performance. Understanding data structures
        is essential for any software engineer.
        """,
        """
        Object-oriented programming introduced the concept of classes and objects. Classes
        define blueprints for creating objects with specific properties and behaviors.
        Inheritance, polymorphism, and encapsulation are key principles of OOP. This paradigm
        revolutionized software design and architecture.
        """,
        """
        Machine learning algorithms enable computers to learn from data without explicit
        programming. Neural networks, decision trees, and support vector machines are popular
        ML algorithms. The field has seen tremendous growth with advances in deep learning.
        Modern ML powers applications from image recognition to natural language processing.
        """
    ]

    for i, content in enumerate(sample_contents, 1):
        doc = Document(
            title=f'Test Document {i}',
            content=content.strip(),
            document_type='document',
            status='completed',
            user_id=test_user.id,
            word_count=len(content.split())
        )
        db_session.add(doc)
        documents.append(doc)

    db_session.commit()
    return documents


# ==============================================================================
# Experiment Fixtures
# ==============================================================================

@pytest.fixture
def sample_term(db_session):
    """
    Create a sample term for temporal experiments.
    """
    term = Term(
        term='algorithm',
        definition='A step-by-step procedure for solving a problem',
        domain='Computer Science',
        status='active'
    )
    db_session.add(term)
    db_session.commit()
    return term


@pytest.fixture
def temporal_experiment(db_session, test_user, sample_term):
    """
    Create a temporal evolution experiment.
    """
    experiment = Experiment(
        name='Temporal Analysis Test',
        description='Test experiment for temporal evolution analysis',
        experiment_type='temporal_evolution',
        user_id=test_user.id,
        term_id=sample_term.id,
        status='draft',
        configuration='{"terms": ["algorithm", "function"], "periods": ["1980-1990", "1990-2000", "2000-2010"]}'
    )
    db_session.add(experiment)
    db_session.commit()
    return experiment


@pytest.fixture
def entity_extraction_experiment(db_session, test_user):
    """
    Create an entity extraction experiment.
    """
    experiment = Experiment(
        name='Entity Extraction Test',
        description='Test experiment for entity extraction',
        experiment_type='entity_extraction',
        user_id=test_user.id,
        status='draft',
        configuration='{"entity_types": ["PERSON", "ORG", "GPE", "DATE"]}'
    )
    db_session.add(experiment)
    db_session.commit()
    return experiment


# ==============================================================================
# File Upload Helpers
# ==============================================================================

@pytest.fixture
def sample_txt_file():
    """
    Create a sample text file for upload testing.
    """
    content = b"""
    Test Document Content

    This is a test document with multiple paragraphs for testing document upload
    and processing functionality.

    It contains several sentences. Each sentence should be properly tokenized.
    The document processor should handle this content correctly.

    Temporal analysis requires documents with rich content spanning different
    time periods and containing various technical terms and concepts.
    """
    return BytesIO(content)


@pytest.fixture
def sample_pdf_file():
    """
    Create a minimal PDF file for upload testing.
    Note: This creates a very basic PDF structure.
    For full PDF testing, consider using reportlab or similar.
    """
    # Minimal PDF header
    content = b"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> /MediaBox [0 0 612 792] /Contents 4 0 R >> endobj
4 0 obj << /Length 44 >> stream
BT /F1 12 Tf 100 700 Td (Test PDF Content) Tj ET
endstream endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000314 00000 n
trailer << /Size 5 /Root 1 0 R >>
startxref
407
%%EOF"""
    return BytesIO(content)


# ==============================================================================
# Helper Functions
# ==============================================================================

def create_test_file(filename='test.txt', content=b'test content'):
    """
    Helper function to create a temporary test file.

    Args:
        filename: Name of the file
        content: File content as bytes

    Returns:
        Path to the temporary file
    """
    fd, path = tempfile.mkstemp(suffix=os.path.splitext(filename)[1])
    with os.fdopen(fd, 'wb') as tmp:
        tmp.write(content)
    return path


# ==============================================================================
# Pytest Configuration
# ==============================================================================

def pytest_configure(config):
    """
    Configure pytest with custom markers.
    """
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (slow)"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test (fast)"
    )
    config.addinivalue_line(
        "markers", "requires_llm: mark test as requiring LLM API access"
    )


@pytest.fixture(autouse=True)
def reset_db_session(db_session):
    """
    Automatically reset database session after each test.
    """
    yield
    db_session.rollback()
