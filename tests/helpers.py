"""
Test Helper Utilities

Provides helper functions for generating test data and common test operations.
"""

import json
from datetime import datetime, timedelta
from io import BytesIO
from typing import List, Dict, Any, Optional

from app import db
from app.models import Document, Experiment, ExperimentDocument, Term
from app.models.user import User


# ==============================================================================
# Document Generators
# ==============================================================================

def generate_temporal_document_content(
    period: str,
    term: str = 'algorithm',
    word_count: int = 200
) -> str:
    """
    Generate realistic document content for temporal analysis testing.

    Args:
        period: Time period (e.g., '1980-1990', '1990-2000')
        term: Main term to include in content
        word_count: Approximate word count

    Returns:
        Generated document content
    """
    templates = {
        '1980-1990': """
        Research in {term}s during the 1980s focused on theoretical foundations
        and computational complexity. Computer scientists at major universities
        developed new {term}s for sorting, searching, and graph traversal.
        The analysis of {term} efficiency using asymptotic notation became
        standard practice. Researchers published extensively on {term} design
        and optimization techniques.
        """,
        '1990-2000': """
        The 1990s saw the practical application of {term}s in commercial software.
        Object-oriented programming languages provided new ways to implement {term}s.
        Software engineers focused on creating reusable {term} libraries.
        The internet boom drove demand for efficient {term}s in web applications.
        Design patterns emerged as a way to document common {term} solutions.
        """,
        '2000-2010': """
        The 2000s brought machine learning {term}s to the mainstream. Large
        technology companies applied {term}s at unprecedented scale. Cloud
        computing enabled distributed {term} execution across multiple servers.
        Data-driven approaches to {term} design became increasingly important.
        Open source libraries democratized access to advanced {term}s.
        """,
        '2010-2020': """
        The 2010s were dominated by deep learning {term}s and neural networks.
        {term}s powered artificial intelligence applications in computer vision,
        natural language processing, and robotics. Edge computing brought {term}
        execution to mobile and IoT devices. Quantum computing promised to
        revolutionize certain classes of {term}s.
        """
    }

    template = templates.get(period, templates['2000-2010'])
    content = template.format(term=term)

    # Pad to approximate word count
    current_words = len(content.split())
    if current_words < word_count:
        padding = " ".join([
            f"Additional research in {term}s covered various aspects of",
            f"computer science including data structures, optimization,",
            f"and computational theory."
        ] * ((word_count - current_words) // 20))
        content = content + "\n\n" + padding

    return content.strip()


def create_test_documents(
    db_session,
    user: User,
    count: int = 5,
    base_title: str = "Test Document"
) -> List[Document]:
    """
    Create multiple test documents.

    Args:
        db_session: Database session
        user: User who owns the documents
        count: Number of documents to create
        base_title: Base title for documents

    Returns:
        List of created documents
    """
    documents = []

    for i in range(1, count + 1):
        content = f"""
        {base_title} {i}

        This is test content for document {i}. It contains multiple paragraphs
        to test document processing functionality.

        The document includes various sentences. Each sentence should be properly
        tokenized and processed. Named entities like Python, JavaScript, and
        Microsoft should be extracted correctly.

        {generate_temporal_document_content('2000-2010', 'algorithm', 100)}
        """

        doc = Document(
            title=f'{base_title} {i}',
            content=content.strip(),
            document_type='document',
            status='completed',
            user_id=user.id,
            word_count=len(content.split())
        )
        db_session.add(doc)
        documents.append(doc)

    db_session.commit()
    return documents


# ==============================================================================
# Experiment Helpers
# ==============================================================================

def create_experiment_with_documents(
    db_session,
    user: User,
    experiment_type: str = 'temporal_evolution',
    document_count: int = 5,
    name: str = "Test Experiment"
) -> tuple[Experiment, List[Document]]:
    """
    Create an experiment and link documents to it.

    Args:
        db_session: Database session
        user: User who owns the experiment
        experiment_type: Type of experiment
        document_count: Number of documents to create and link
        name: Experiment name

    Returns:
        Tuple of (experiment, list of documents)
    """
    # Create term if needed for temporal experiments
    term = None
    if experiment_type == 'temporal_evolution':
        term = Term.query.filter_by(term='algorithm').first()
        if not term:
            term = Term(
                term='algorithm',
                definition='A step-by-step procedure',
                domain='Computer Science',
                status='active'
            )
            db_session.add(term)
            db_session.flush()

    # Create experiment
    experiment = Experiment(
        name=name,
        description=f'Test experiment of type {experiment_type}',
        experiment_type=experiment_type,
        user_id=user.id,
        term_id=term.id if term else None,
        status='draft',
        configuration=json.dumps({
            'terms': ['algorithm', 'function'],
            'periods': ['1980-1990', '1990-2000', '2000-2010']
        })
    )
    db_session.add(experiment)
    db_session.flush()

    # Create and link documents
    documents = create_test_documents(
        db_session,
        user,
        count=document_count,
        base_title=f"Doc for {name}"
    )

    for doc in documents:
        exp_doc = ExperimentDocument(
            experiment_id=experiment.id,
            document_id=doc.id,
            processing_status='pending'
        )
        db_session.add(exp_doc)

    db_session.commit()
    return experiment, documents


def set_experiment_status(db_session, experiment: Experiment, status: str):
    """
    Set experiment status and update timestamps.

    Args:
        db_session: Database session
        experiment: Experiment to update
        status: New status ('draft', 'running', 'completed', 'error')
    """
    experiment.status = status

    if status == 'running' and not experiment.started_at:
        experiment.started_at = datetime.utcnow()
    elif status == 'completed' and not experiment.completed_at:
        experiment.completed_at = datetime.utcnow()

    db_session.commit()


# ==============================================================================
# API Request Helpers
# ==============================================================================

def upload_document_via_api(
    client,
    title: str,
    content: str,
    experiment_id: Optional[int] = None,
    document_type: str = 'document'
) -> Dict[str, Any]:
    """
    Upload a document via the API.

    Args:
        client: Flask test client
        title: Document title
        content: Document content
        experiment_id: Optional experiment ID to link to
        document_type: Type of document

    Returns:
        Response data as dictionary
    """
    file_data = {
        'file': (BytesIO(content.encode('utf-8')), 'test.txt'),
        'title': title,
        'document_type': document_type,
        'prov_type': 'prov:Entity/SourceDocument',
        'language': 'en'
    }

    if experiment_id:
        file_data['experiment_id'] = str(experiment_id)

    response = client.post(
        '/upload/document',
        data=file_data,
        content_type='multipart/form-data'
    )

    return {
        'status_code': response.status_code,
        'data': response.data,
        'success': response.status_code in [200, 201, 302]
    }


def run_segmentation(
    client,
    document_uuid: str,
    method: str = 'paragraph',
    experiment_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Run segmentation on a document.

    Args:
        client: Flask test client
        document_uuid: Document UUID
        method: Segmentation method
        experiment_id: Optional experiment ID

    Returns:
        Response data as dictionary
    """
    data = {'method': method}
    if experiment_id:
        data['experiment_id'] = experiment_id

    response = client.post(
        f'/process/document/{document_uuid}/segment',
        data=json.dumps(data),
        content_type='application/json'
    )

    return {
        'status_code': response.status_code,
        'data': response.data,
        'success': response.status_code == 200
    }


def run_entity_extraction(
    client,
    document_uuid: str,
    method: str = 'spacy',
    experiment_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Run entity extraction on a document.

    Args:
        client: Flask test client
        document_uuid: Document UUID
        method: Extraction method
        experiment_id: Optional experiment ID

    Returns:
        Response data as dictionary
    """
    data = {'method': method}
    if experiment_id:
        data['experiment_id'] = experiment_id

    response = client.post(
        f'/process/document/{document_uuid}/entities',
        data=json.dumps(data),
        content_type='application/json'
    )

    return {
        'status_code': response.status_code,
        'data': response.data,
        'success': response.status_code == 200
    }


def run_embeddings(
    client,
    document_uuid: str,
    method: str = 'local',
    experiment_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Generate embeddings for a document.

    Args:
        client: Flask test client
        document_uuid: Document UUID
        method: Embedding method
        experiment_id: Optional experiment ID

    Returns:
        Response data as dictionary
    """
    data = {'method': method}
    if experiment_id:
        data['experiment_id'] = experiment_id

    response = client.post(
        f'/process/document/{document_uuid}/embeddings',
        data=json.dumps(data),
        content_type='application/json'
    )

    return {
        'status_code': response.status_code,
        'data': response.data,
        'success': response.status_code == 200
    }


# ==============================================================================
# Assertion Helpers
# ==============================================================================

def assert_experiment_has_documents(experiment: Experiment, expected_count: int):
    """Assert experiment has expected number of documents."""
    actual_count = experiment.get_document_count()
    assert actual_count == expected_count, \
        f"Expected {expected_count} documents, found {actual_count}"


def assert_document_processed(
    db_session,
    document: Document,
    processing_types: List[str]
):
    """
    Assert document has been processed with specified types.

    Args:
        db_session: Database session
        document: Document to check
        processing_types: List of expected processing types
            (e.g., ['segmentation', 'entities', 'embeddings'])
    """
    from app.models.experiment_processing import ExperimentDocumentProcessing
    from app.models.experiment_document import ExperimentDocument

    for proc_type in processing_types:
        processing = db_session.query(ExperimentDocumentProcessing).join(
            ExperimentDocument
        ).filter(
            ExperimentDocument.document_id == document.id,
            ExperimentDocumentProcessing.processing_type == proc_type
        ).first()

        assert processing is not None, \
            f"Document {document.id} missing {proc_type} processing"


# ==============================================================================
# Time Period Helpers
# ==============================================================================

def generate_publication_date(period: str) -> str:
    """
    Generate a publication date within a time period.

    Args:
        period: Time period string (e.g., '1980-1990')

    Returns:
        ISO format date string
    """
    if '-' in period:
        start_year = int(period.split('-')[0])
        # Use middle of period
        year = start_year + 5
    else:
        year = int(period)

    return f"{year}-01-01"


def get_period_for_year(year: int) -> str:
    """
    Get time period string for a given year.

    Args:
        year: Year

    Returns:
        Period string (e.g., '1980-1990')
    """
    decade_start = (year // 10) * 10
    return f"{decade_start}-{decade_start + 10}"
