"""
Tests for document CRUD operations.

Tests deletion cascade order, FK constraint handling, and experiment protection.
"""

import pytest
from flask import url_for


class TestDeleteAllDocuments:
    """Test the delete all documents functionality."""

    def test_delete_all_requires_admin(self, auth_client, db_session):
        """Test that delete all documents requires admin privileges."""
        # Regular user should get 403
        response = auth_client.post('/input/documents/delete-all')
        assert response.status_code == 403
        data = response.get_json()
        assert data['success'] is False
        assert 'Admin' in data['error']

    def test_delete_all_blocked_by_experiments(self, admin_client, db_session, experiment_with_processing):
        """Test that delete all documents is blocked when experiments reference documents."""
        # Should return 409 with experiment info
        response = admin_client.post('/input/documents/delete-all')
        assert response.status_code == 409
        data = response.get_json()
        assert data['success'] is False
        assert 'experiment' in data['error'].lower()
        assert 'experiments' in data

    def test_delete_all_with_document_processing_index(self, admin_client, db_session, sample_documents, admin_user):
        """
        Test that delete all documents handles DocumentProcessingIndex FK correctly.

        This tests the FK constraint order: document_processing_index must be deleted
        BEFORE experiment_document_processing due to the processing_id FK.
        """
        from app.models.experiment_processing import (
            ExperimentDocumentProcessing,
            DocumentProcessingIndex,
            ProcessingArtifact
        )
        from app.models.experiment_document import ExperimentDocument
        from app.models import Experiment, Document
        from app import db

        # Create experiment using admin_user's ID
        experiment = Experiment(
            name='Test Experiment for Deletion',
            description='Testing FK cascade',
            experiment_type='temporal_evolution',
            user_id=admin_user.id,
            status='draft'
        )
        db_session.add(experiment)
        db_session.flush()

        # Link a document to the experiment
        doc = sample_documents[0]
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
            processing_method='local',
            status='completed'
        )
        db_session.add(processing)
        db_session.flush()

        # Create DocumentProcessingIndex (this is what was causing the FK violation)
        doc_proc_index = DocumentProcessingIndex(
            document_id=doc.id,
            experiment_id=experiment.id,
            processing_id=processing.id,
            processing_type='embeddings',
            processing_method='local',
            status='completed'
        )
        db_session.add(doc_proc_index)
        db_session.commit()

        # Verify the records exist
        assert DocumentProcessingIndex.query.count() > 0
        assert ExperimentDocumentProcessing.query.count() > 0

        # Now delete the experiment first (required before deleting documents)
        from app.services.experiment_service import get_experiment_service
        service = get_experiment_service()
        service.delete_experiment(experiment.id, user_id=admin_user.id)

        # Now delete all documents should work
        response = admin_client.post('/input/documents/delete-all')
        assert response.status_code == 200, f"Failed: {response.get_json()}"
        data = response.get_json()
        assert data['success'] is True

    def test_delete_all_success_no_experiments(self, admin_client, db_session, sample_documents):
        """Test that delete all documents succeeds when no experiments exist."""
        from app.models import Document

        # Verify documents exist
        assert Document.query.count() > 0

        # Delete all
        response = admin_client.post('/input/documents/delete-all')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

        # Verify all documents are deleted
        assert Document.query.count() == 0


class TestExperimentDeleteCascade:
    """Test experiment deletion cascade order."""

    def test_experiment_delete_clears_document_processing_index(
        self, auth_client, db_session, experiment_with_processing, test_user
    ):
        """
        Test that deleting an experiment also deletes DocumentProcessingIndex entries.

        This verifies the cascade delete handles the FK constraint correctly:
        DocumentProcessingIndex -> ExperimentDocumentProcessing (via processing_id)
        """
        from app.models.experiment_processing import DocumentProcessingIndex, ExperimentDocumentProcessing
        from app.services.experiment_service import get_experiment_service

        experiment_id = experiment_with_processing.id

        # Verify index entries exist
        index_count = DocumentProcessingIndex.query.filter_by(
            experiment_id=experiment_id
        ).count()
        assert index_count > 0, "Test fixture should create DocumentProcessingIndex entries"

        # Delete the experiment (use the test_user who owns it)
        service = get_experiment_service()
        service.delete_experiment(experiment_id, user_id=test_user.id)

        # Verify index entries are deleted
        remaining = DocumentProcessingIndex.query.filter_by(
            experiment_id=experiment_id
        ).count()
        assert remaining == 0, "DocumentProcessingIndex entries should be deleted with experiment"

    def test_experiment_delete_preserves_original_documents(
        self, auth_client, db_session, experiment_with_processing, test_user
    ):
        """Test that deleting an experiment preserves original (v1) documents."""
        from app.models import Document
        from app.services.experiment_service import get_experiment_service

        experiment_id = experiment_with_processing.id

        # Get original document IDs before deletion
        original_doc_ids = [
            doc.id for doc in Document.query.filter_by(version_type='original').all()
        ]
        assert len(original_doc_ids) > 0

        # Delete the experiment (use the test_user who owns it)
        service = get_experiment_service()
        service.delete_experiment(experiment_id, user_id=test_user.id)

        # Verify original documents still exist
        remaining_originals = Document.query.filter(
            Document.id.in_(original_doc_ids)
        ).count()
        assert remaining_originals == len(original_doc_ids), \
            "Original documents should not be deleted with experiment"
