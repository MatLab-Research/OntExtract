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

    This fixture creates a nested transaction that gets rolled back
    after each test, ensuring complete isolation.
    """
    with app.app_context():
        # Create a connection and begin a transaction
        connection = db.engine.connect()
        transaction = connection.begin()

        # Create a scoped session bound to this connection
        from sqlalchemy.orm import sessionmaker, scoped_session
        session_factory = sessionmaker(bind=connection)
        Session = scoped_session(session_factory)

        # Store the original session
        original_session = db.session

        # Replace db.session with our transaction-bound scoped session
        db.session = Session

        yield Session

        # Restore the original session
        db.session = original_session

        # Close the session and rollback the transaction
        Session.remove()
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


@pytest.fixture
def admin_client(app, db_session, admin_user):
    """
    Provide an authenticated admin test client.
    Uses Flask-Login to simulate a logged-in admin user.
    """
    client = app.test_client()

    with client.session_transaction() as sess:
        sess['_user_id'] = str(admin_user.id)
        sess['_fresh'] = True

    return client


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
        content_type='text/plain',
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
            content_type='text/plain',
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
        term_text='algorithm',
        description='A step-by-step procedure for solving a problem',
        research_domain='Computer Science',
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
# Experiment with Documents Fixtures
# ==============================================================================

@pytest.fixture
def experiment_with_documents(db_session, test_user, sample_documents):
    """
    Create an experiment with linked documents for testing results routes.
    """
    from app.models.experiment_document import ExperimentDocument

    experiment = Experiment(
        name='Experiment with Documents',
        description='Test experiment with linked documents',
        experiment_type='temporal_evolution',
        user_id=test_user.id,
        status='completed',
        configuration='{"terms": ["algorithm"], "periods": ["1980-2000"]}'
    )
    db_session.add(experiment)
    db_session.flush()  # Get experiment ID

    # Link documents to experiment
    for doc in sample_documents:
        exp_doc = ExperimentDocument(
            experiment_id=experiment.id,
            document_id=doc.id
        )
        db_session.add(exp_doc)

    db_session.commit()
    return experiment


@pytest.fixture
def experiment_with_processing(db_session, test_user, sample_documents):
    """
    Create an experiment with documents and processing artifacts.
    This simulates an experiment that has been processed with embeddings,
    definitions, entities, and temporal markers.
    """
    from app.models.experiment_document import ExperimentDocument
    from app.models.experiment_processing import ProcessingArtifact, ExperimentDocumentProcessing, DocumentProcessingIndex
    from datetime import date
    import json

    # Create experiment
    experiment = Experiment(
        name='Processed Experiment',
        description='Test experiment with processing artifacts',
        experiment_type='temporal_evolution',
        user_id=test_user.id,
        status='completed',
        configuration='{"terms": ["algorithm"], "periods": ["1980-2000"]}'
    )
    db_session.add(experiment)
    db_session.flush()

    # Link documents and add processing artifacts
    for i, doc in enumerate(sample_documents):
        # Set publication date for period-aware testing
        doc.publication_date = date(1990 + i * 5, 1, 1)  # 1990, 1995, 2000, 2005, 2010

        # Link document to experiment
        exp_doc = ExperimentDocument(
            experiment_id=experiment.id,
            document_id=doc.id
        )
        db_session.add(exp_doc)
        db_session.flush()

        # Create processing record
        processing = ExperimentDocumentProcessing(
            experiment_document_id=exp_doc.id,
            processing_type='embeddings',
            processing_method='period_aware',
            status='completed',
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow()
        )
        db_session.add(processing)
        db_session.flush()

        # Create DocumentProcessingIndex entry (for FK cascade testing)
        doc_proc_index = DocumentProcessingIndex(
            document_id=doc.id,
            experiment_id=experiment.id,
            processing_id=processing.id,
            processing_type='embeddings',
            processing_method='period_aware',
            status='completed'
        )
        db_session.add(doc_proc_index)

        # Create embedding artifact
        embedding_artifact = ProcessingArtifact(
            processing_id=processing.id,
            document_id=doc.id,
            artifact_type='embedding_vector',
            artifact_index=0
        )
        embedding_artifact.set_content({
            'vector': [0.1] * 768,
            'method': 'period_aware',
            'model': 'all-mpnet-base-v2',
            'dimensions': 768
        })
        embedding_artifact.set_metadata({
            'method': 'period_aware',
            'model': 'all-mpnet-base-v2',
            'dimensions': 768,
            'period_category': 'modern_1950_2000' if doc.publication_date.year >= 1950 else 'historical_1850_1950',
            'document_year': doc.publication_date.year,
            'selection_confidence': 0.8,
            'era': 'modern'
        })
        db_session.add(embedding_artifact)

        # Create definition artifact
        definition_artifact = ProcessingArtifact(
            processing_id=processing.id,
            document_id=doc.id,
            artifact_type='term_definition',
            artifact_index=0
        )
        definition_artifact.set_content({
            'term': 'algorithm',
            'definition': 'A step-by-step procedure for solving a problem',
            'pattern': 'copula',
            'confidence': 0.85,
            'sentence': 'An algorithm is a step-by-step procedure for solving a problem.'
        })
        definition_artifact.set_metadata({'method': 'pattern_matching+dependency_parsing'})
        db_session.add(definition_artifact)

        # Create entity artifact
        entity_artifact = ProcessingArtifact(
            processing_id=processing.id,
            document_id=doc.id,
            artifact_type='extracted_entity',
            artifact_index=0
        )
        entity_artifact.set_content({
            'entity': 'computer science',
            'type': 'FIELD',
            'start': 10,
            'end': 26,
            'confidence': 0.9
        })
        entity_artifact.set_metadata({'method': 'spacy_ner'})
        db_session.add(entity_artifact)

        # Create temporal artifact
        temporal_artifact = ProcessingArtifact(
            processing_id=processing.id,
            document_id=doc.id,
            artifact_type='temporal_marker',
            artifact_index=0
        )
        temporal_artifact.set_content({
            'text': f'{1990 + i * 5}',
            'type': 'DATE',
            'normalized': f'{1990 + i * 5}-01-01',
            'confidence': 0.95,
            'start': 50,
            'end': 54
        })
        temporal_artifact.set_metadata({'method': 'spacy_ner_plus_regex'})
        db_session.add(temporal_artifact)

        # Create segment artifact
        segment_artifact = ProcessingArtifact(
            processing_id=processing.id,
            document_id=doc.id,
            artifact_type='text_segment',
            artifact_index=0
        )
        segment_artifact.set_content({
            'text': doc.content[:200],
            'segment_type': 'paragraph'
        })
        segment_artifact.set_metadata({'method': 'paragraph', 'word_count': 50})
        db_session.add(segment_artifact)

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
