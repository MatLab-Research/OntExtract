"""
Tests for Experiments CRUD Operations

This test file covers the basic CRUD operations for experiments:
- Creating experiments (new, wizard, create, sample)
- Reading experiments (index, view, api_list, api_get)
- Updating experiments (edit, update)
- Deleting experiments (delete)
- Running experiments (run)
- Viewing results (results)

Routes tested:
- GET  /experiments/
- GET  /experiments/new
- GET  /experiments/wizard
- POST /experiments/create
- POST /experiments/sample
- GET  /experiments/<id>
- GET  /experiments/<id>/edit
- POST /experiments/<id>/update
- POST /experiments/<id>/delete
- POST /experiments/<id>/run
- GET  /experiments/<id>/results
- GET  /experiments/api/list
- GET  /experiments/api/<id>
"""

import pytest
import json
from flask import url_for
from app.models import Experiment, Document, ExperimentDocument


class TestExperimentsList:
    """Test the experiments index/list page."""

    def test_index_renders_successfully(self, client):
        """Test that the experiments index page renders."""
        response = client.get('/experiments/')
        assert response.status_code == 200
        assert b'experiments' in response.data.lower()

    def test_index_shows_all_experiments(self, client, db_session):
        """Test that all experiments are shown on index."""
        # TODO: Create test experiments
        # TODO: Verify they appear on the page
        pass

    def test_index_public_access(self, client):
        """Test that index is accessible without login."""
        response = client.get('/experiments/')
        assert response.status_code == 200


class TestExperimentCreate:
    """Test experiment creation endpoints."""

    def test_new_experiment_form_renders(self, client):
        """Test that the new experiment form renders."""
        response = client.get('/experiments/new')
        assert response.status_code == 200

    def test_wizard_renders(self, client):
        """Test that the wizard page renders."""
        response = client.get('/experiments/wizard')
        assert response.status_code == 200

    def test_create_experiment_requires_login(self, client):
        """Test that creating an experiment requires authentication."""
        data = {
            'name': 'Test Experiment',
            'experiment_type': 'domain_comparison',
            'document_ids': [1]
        }
        response = client.post(
            '/experiments/create',
            data=json.dumps(data),
            content_type='application/json'
        )
        # Should redirect to login or return 401
        assert response.status_code in [302, 401]

    def test_create_experiment_valid_data(self, auth_client, db_session):
        """Test creating an experiment with valid data."""
        # TODO: Create test document
        # TODO: Submit valid experiment data
        # TODO: Verify experiment created in database
        # TODO: Verify redirect to document_pipeline
        pass

    def test_create_experiment_missing_name(self, auth_client):
        """Test that creating experiment without name fails."""
        data = {
            'experiment_type': 'domain_comparison',
            'document_ids': [1]
        }
        response = auth_client.post(
            '/experiments/create',
            data=json.dumps(data),
            content_type='application/json'
        )
        assert response.status_code == 400
        assert b'name is required' in response.data.lower()

    def test_create_experiment_missing_type(self, auth_client):
        """Test that creating experiment without type fails."""
        data = {
            'name': 'Test Experiment',
            'document_ids': [1]
        }
        response = auth_client.post(
            '/experiments/create',
            data=json.dumps(data),
            content_type='application/json'
        )
        assert response.status_code == 400
        assert b'type is required' in response.data.lower()

    def test_create_experiment_missing_documents(self, auth_client):
        """Test that creating experiment without documents fails."""
        data = {
            'name': 'Test Experiment',
            'experiment_type': 'domain_comparison'
        }
        response = auth_client.post(
            '/experiments/create',
            data=json.dumps(data),
            content_type='application/json'
        )
        assert response.status_code == 400

    def test_create_sample_experiment(self, auth_client):
        """Test creating a sample experiment."""
        # TODO: Test sample experiment creation
        pass


class TestExperimentView:
    """Test viewing experiment details."""

    def test_view_existing_experiment(self, client, db_session):
        """Test viewing an existing experiment."""
        # TODO: Create test experiment
        # TODO: Verify view page renders
        pass

    def test_view_nonexistent_experiment(self, client):
        """Test viewing a nonexistent experiment returns 404."""
        response = client.get('/experiments/99999')
        assert response.status_code == 404

    def test_view_shows_documents(self, client, db_session):
        """Test that experiment view shows associated documents."""
        # TODO: Create experiment with documents
        # TODO: Verify documents appear on page
        pass


class TestExperimentUpdate:
    """Test updating experiments."""

    def test_edit_form_renders(self, auth_client, db_session):
        """Test that edit form renders for existing experiment."""
        # TODO: Create test experiment
        # TODO: Verify edit form renders
        pass

    def test_edit_requires_login(self, client, db_session):
        """Test that edit requires authentication."""
        # TODO: Verify redirect to login
        pass

    def test_edit_running_experiment_fails(self, auth_client, db_session):
        """Test that editing a running experiment fails."""
        # TODO: Create running experiment
        # TODO: Attempt to edit
        # TODO: Verify error message
        pass

    def test_update_experiment_name(self, auth_client, db_session):
        """Test updating experiment name."""
        # TODO: Create experiment
        # TODO: Update name
        # TODO: Verify update in database
        pass

    def test_update_experiment_documents(self, auth_client, db_session):
        """Test updating experiment documents."""
        # TODO: Create experiment
        # TODO: Update documents
        # TODO: Verify changes in database
        pass

    def test_update_running_experiment_fails(self, auth_client, db_session):
        """Test that updating a running experiment fails."""
        # TODO: Create running experiment
        # TODO: Attempt update
        # TODO: Verify error
        pass


class TestExperimentDelete:
    """Test deleting experiments."""

    def test_delete_experiment_requires_login(self, client, db_session):
        """Test that delete requires authentication."""
        # TODO: Verify requires login
        pass

    def test_delete_existing_experiment(self, auth_client, db_session):
        """Test deleting an existing experiment."""
        # TODO: Create experiment
        # TODO: Delete it
        # TODO: Verify removed from database
        pass

    def test_delete_preserves_original_documents(self, auth_client, db_session):
        """Test that deleting experiment preserves original documents."""
        # TODO: Create experiment with documents
        # TODO: Delete experiment
        # TODO: Verify documents still exist
        pass

    def test_delete_running_experiment_fails(self, auth_client, db_session):
        """Test that deleting a running experiment fails."""
        # TODO: Create running experiment
        # TODO: Attempt delete
        # TODO: Verify error
        pass

    def test_delete_removes_processing_data(self, auth_client, db_session):
        """Test that deleting experiment removes processing artifacts."""
        # TODO: Create experiment with processing data
        # TODO: Delete experiment
        # TODO: Verify processing data removed
        pass


class TestExperimentRun:
    """Test running experiments."""

    def test_run_experiment_requires_login(self, client, db_session):
        """Test that running experiment requires authentication."""
        # TODO: Verify requires login
        pass

    def test_run_valid_experiment(self, auth_client, db_session):
        """Test running a valid experiment."""
        # TODO: Create experiment
        # TODO: Run it
        # TODO: Verify status changes
        pass

    def test_run_already_running_experiment(self, auth_client, db_session):
        """Test running an already running experiment."""
        # TODO: Create running experiment
        # TODO: Attempt to run again
        # TODO: Verify appropriate response
        pass


class TestExperimentResults:
    """Test viewing experiment results."""

    def test_results_page_renders(self, client, db_session):
        """Test that results page renders."""
        # TODO: Create completed experiment
        # TODO: Verify results page renders
        pass

    def test_results_for_incomplete_experiment(self, client, db_session):
        """Test viewing results for incomplete experiment."""
        # TODO: Create pending experiment
        # TODO: Verify appropriate message
        pass


class TestExperimentAPI:
    """Test experiment API endpoints."""

    def test_api_list_experiments(self, client, db_session):
        """Test API list all experiments."""
        response = client.get('/experiments/api/list')
        assert response.status_code == 200
        assert response.content_type == 'application/json'

    def test_api_get_experiment(self, client, db_session):
        """Test API get single experiment."""
        # TODO: Create experiment
        # TODO: Fetch via API
        # TODO: Verify JSON response
        pass

    def test_api_get_nonexistent_experiment(self, client):
        """Test API get nonexistent experiment returns 404."""
        response = client.get('/experiments/api/99999')
        assert response.status_code == 404


# ==============================================================================
# Test Fixtures
# ==============================================================================

@pytest.fixture
def sample_experiment_data():
    """Sample data for creating experiments."""
    return {
        'name': 'Test Experiment',
        'description': 'A test experiment for unit testing',
        'experiment_type': 'domain_comparison',
        'configuration': {
            'domains': ['Computer Science', 'Philosophy'],
            'target_terms': ['algorithm', 'function']
        }
    }


@pytest.fixture
def sample_document(db_session):
    """Create a sample document for testing."""
    document = Document(
        title='Test Document',
        content='This is test content for the document.',
        document_type='document',
        status='completed'
    )
    db_session.add(document)
    db_session.commit()
    return document


# ==============================================================================
# Helper Functions
# ==============================================================================

def create_test_experiment(db_session, **kwargs):
    """Helper to create a test experiment."""
    defaults = {
        'name': 'Test Experiment',
        'experiment_type': 'domain_comparison',
        'status': 'pending'
    }
    defaults.update(kwargs)

    experiment = Experiment(**defaults)
    db_session.add(experiment)
    db_session.commit()
    return experiment


def create_running_experiment(db_session):
    """Helper to create a running experiment."""
    return create_test_experiment(db_session, status='running')
