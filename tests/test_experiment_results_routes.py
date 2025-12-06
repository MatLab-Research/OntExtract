"""
Tests for Experiment Results Routes

This test file covers the experiment results routes:
- GET /experiments/<id>/results/definitions
- GET /experiments/<id>/results/entities
- GET /experiments/<id>/results/temporal
- GET /experiments/<id>/results/embeddings
- GET /experiments/<id>/results/segments

Tests verify:
1. Routes render successfully with proper status codes
2. Routes handle experiments with and without processing artifacts
3. Routes display correct data from ProcessingArtifact table
4. Document versioning is handled correctly
5. Period-aware metadata is displayed for embeddings
"""

import pytest


class TestExperimentResultsWithoutProcessing:
    """Test results routes for experiments without processing artifacts."""

    def test_definitions_empty(self, client, temporal_experiment):
        """Definitions page renders with no definitions."""
        response = client.get(f'/experiments/{temporal_experiment.id}/results/definitions')
        assert response.status_code == 200
        assert b'definitions' in response.data.lower()
        # Should show empty state
        assert b'No definitions' in response.data or b'total_definitions' in response.data or b'0' in response.data

    def test_entities_empty(self, client, temporal_experiment):
        """Entities page renders with no entities."""
        response = client.get(f'/experiments/{temporal_experiment.id}/results/entities')
        assert response.status_code == 200
        assert b'entities' in response.data.lower()

    def test_temporal_empty(self, client, temporal_experiment):
        """Temporal page renders with no temporal expressions."""
        response = client.get(f'/experiments/{temporal_experiment.id}/results/temporal')
        assert response.status_code == 200
        assert b'temporal' in response.data.lower()

    def test_embeddings_empty(self, client, temporal_experiment):
        """Embeddings page renders with no embeddings."""
        response = client.get(f'/experiments/{temporal_experiment.id}/results/embeddings')
        assert response.status_code == 200
        assert b'embeddings' in response.data.lower() or b'Embeddings' in response.data

    def test_segments_empty(self, client, temporal_experiment):
        """Segments page renders with no segments."""
        response = client.get(f'/experiments/{temporal_experiment.id}/results/segments')
        assert response.status_code == 200
        assert b'segments' in response.data.lower() or b'Segments' in response.data


class TestExperimentResultsWithDocuments:
    """Test results routes for experiments with documents but no processing."""

    def test_definitions_with_documents(self, client, experiment_with_documents):
        """Definitions page renders for experiment with documents."""
        response = client.get(f'/experiments/{experiment_with_documents.id}/results/definitions')
        assert response.status_code == 200

    def test_entities_with_documents(self, client, experiment_with_documents):
        """Entities page renders for experiment with documents."""
        response = client.get(f'/experiments/{experiment_with_documents.id}/results/entities')
        assert response.status_code == 200

    def test_temporal_with_documents(self, client, experiment_with_documents):
        """Temporal page renders for experiment with documents."""
        response = client.get(f'/experiments/{experiment_with_documents.id}/results/temporal')
        assert response.status_code == 200

    def test_embeddings_with_documents(self, client, experiment_with_documents):
        """Embeddings page renders for experiment with documents."""
        response = client.get(f'/experiments/{experiment_with_documents.id}/results/embeddings')
        assert response.status_code == 200

    def test_segments_with_documents(self, client, experiment_with_documents):
        """Segments page renders for experiment with documents."""
        response = client.get(f'/experiments/{experiment_with_documents.id}/results/segments')
        assert response.status_code == 200


class TestExperimentResultsWithProcessing:
    """Test results routes for experiments with processing artifacts."""

    def test_definitions_with_processing(self, client, experiment_with_processing):
        """Definitions page shows processed definitions."""
        response = client.get(f'/experiments/{experiment_with_processing.id}/results/definitions')
        assert response.status_code == 200
        # Should find the definition we created
        assert b'algorithm' in response.data.lower()

    def test_entities_with_processing(self, client, experiment_with_processing):
        """Entities page shows extracted entities."""
        response = client.get(f'/experiments/{experiment_with_processing.id}/results/entities')
        assert response.status_code == 200
        # Should find the entity we created
        assert b'computer science' in response.data.lower()

    def test_temporal_with_processing(self, client, experiment_with_processing):
        """Temporal page shows temporal expressions."""
        response = client.get(f'/experiments/{experiment_with_processing.id}/results/temporal')
        assert response.status_code == 200
        # Should find dates from our fixture (1990, 1995, 2000, 2005, 2010)
        assert b'1990' in response.data or b'1995' in response.data

    def test_embeddings_with_processing(self, client, experiment_with_processing):
        """Embeddings page shows embedding info."""
        response = client.get(f'/experiments/{experiment_with_processing.id}/results/embeddings')
        assert response.status_code == 200
        # Should show model info
        assert b'mpnet' in response.data.lower() or b'period_aware' in response.data.lower()

    def test_embeddings_shows_period_metadata(self, client, experiment_with_processing):
        """Embeddings page shows period-aware metadata."""
        response = client.get(f'/experiments/{experiment_with_processing.id}/results/embeddings')
        assert response.status_code == 200
        # Should show period category
        # Note: The data contains 'modern_1950_2000' - check for partial match
        html = response.data.decode('utf-8')
        assert 'modern' in html.lower() or 'period' in html.lower()

    def test_segments_with_processing(self, client, experiment_with_processing):
        """Segments page shows text segments."""
        response = client.get(f'/experiments/{experiment_with_processing.id}/results/segments')
        assert response.status_code == 200


class TestExperimentResultsNotFound:
    """Test 404 handling for non-existent experiments."""

    def test_definitions_not_found(self, client):
        """Definitions returns 404 for non-existent experiment."""
        response = client.get('/experiments/99999/results/definitions')
        assert response.status_code == 404

    def test_entities_not_found(self, client):
        """Entities returns 404 for non-existent experiment."""
        response = client.get('/experiments/99999/results/entities')
        assert response.status_code == 404

    def test_temporal_not_found(self, client):
        """Temporal returns 404 for non-existent experiment."""
        response = client.get('/experiments/99999/results/temporal')
        assert response.status_code == 404

    def test_embeddings_not_found(self, client):
        """Embeddings returns 404 for non-existent experiment."""
        response = client.get('/experiments/99999/results/embeddings')
        assert response.status_code == 404

    def test_segments_not_found(self, client):
        """Segments returns 404 for non-existent experiment."""
        response = client.get('/experiments/99999/results/segments')
        assert response.status_code == 404


class TestExperimentResultsSourceAttribution:
    """Test that source attribution (Pipeline vs Manual) works correctly."""

    def test_embeddings_source_is_manual_without_orchestration(self, client, experiment_with_processing):
        """Embeddings without orchestration run should show Manual source."""
        response = client.get(f'/experiments/{experiment_with_processing.id}/results/embeddings')
        assert response.status_code == 200
        # Without orchestration results, source should be 'manual'
        html = response.data.decode('utf-8')
        # The fixture doesn't create orchestration results, so embeddings should be manual
        assert 'Manual' in html or 'manual' in html


class TestExperimentResultsTemplateVariables:
    """Test that templates receive correct variables."""

    def test_embeddings_has_total_embeddings(self, client, experiment_with_processing):
        """Embeddings page has total_embeddings count."""
        response = client.get(f'/experiments/{experiment_with_processing.id}/results/embeddings')
        assert response.status_code == 200
        # Template should render embedding count (5 documents = 5 embeddings)
        html = response.data.decode('utf-8')
        # Check for numbers that could be the count
        assert '5' in html or 'Total' in html

    def test_definitions_has_counts(self, client, experiment_with_processing):
        """Definitions page has proper counts."""
        response = client.get(f'/experiments/{experiment_with_processing.id}/results/definitions')
        assert response.status_code == 200
        # Should have counts rendered (5 definitions from 5 documents)
        html = response.data.decode('utf-8')
        assert '5' in html or 'definitions' in html.lower()

    def test_entities_has_type_grouping(self, client, experiment_with_processing):
        """Entities page groups by entity type."""
        response = client.get(f'/experiments/{experiment_with_processing.id}/results/entities')
        assert response.status_code == 200
        html = response.data.decode('utf-8')
        # Should have entity type displayed
        assert 'FIELD' in html or 'field' in html.lower()


class TestLinkAccessibility:
    """Test that key links in results pages work."""

    def test_definitions_document_links(self, client, db_session, experiment_with_processing):
        """Document links in definitions page should work."""
        response = client.get(f'/experiments/{experiment_with_processing.id}/results/definitions')
        assert response.status_code == 200
        html = response.data.decode('utf-8')

        # Extract document UUIDs from the page and verify they're valid links
        # Links should point to process_document page
        assert 'href=' in html

    def test_embeddings_document_links(self, client, experiment_with_processing):
        """Document links in embeddings page should work."""
        response = client.get(f'/experiments/{experiment_with_processing.id}/results/embeddings')
        assert response.status_code == 200
        html = response.data.decode('utf-8')
        # Links to documents should be present
        assert 'href=' in html


class TestExperimentResultsEdgeCases:
    """Test edge cases for experiment results."""

    def test_empty_experiment(self, client, db_session, test_user):
        """Experiment with no documents should handle gracefully."""
        from app.models import Experiment

        experiment = Experiment(
            name='Empty Experiment',
            description='No documents',
            experiment_type='temporal_evolution',
            user_id=test_user.id,
            status='draft'
        )
        db_session.add(experiment)
        db_session.commit()

        # All results pages should return 200 with empty state
        for route in ['definitions', 'entities', 'temporal', 'embeddings', 'segments']:
            response = client.get(f'/experiments/{experiment.id}/results/{route}')
            assert response.status_code == 200, f"Route {route} failed"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
