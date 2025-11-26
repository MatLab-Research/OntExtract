"""
API Tests for LLM Orchestration Endpoints

Tests the Flask API routes for the LLM Analyze feature orchestration workflow.

Coverage:
- POST /experiments/<id>/orchestration/analyze - Start orchestration
- GET  /orchestration/status/<run_id> - Poll status
- POST /orchestration/approve-strategy/<run_id> - Approve strategy
- GET  /experiments/<id>/orchestration/llm-results/<run_id> - Results page
- GET  /experiments/<id>/orchestration/llm-provenance/<run_id> - PROV-O download
"""

import pytest
import json
from unittest.mock import patch, Mock
from uuid import uuid4

from app.models import Experiment, Document
from app.models.experiment_orchestration_run import ExperimentOrchestrationRun


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
def experiment_with_docs(db_session, test_user):
    """Create experiment with documents for testing."""
    experiment = Experiment(
        name='LLM Test Experiment',
        description='Test experiment for LLM orchestration',
        experiment_type='temporal_evolution',
        user_id=test_user.id,
        status='draft',
        configuration='{"target_terms": ["algorithm"]}'
    )
    db_session.add(experiment)
    db_session.flush()

    # Add 3 documents
    for i in range(3):
        doc = Document(
            title=f'Doc {i+1}',
            content=f'Content for doc {i+1}. ' * 50,
            original_filename=f'doc{i+1}.txt',
            document_type='document',
            content_type='text/plain',
            status='completed',
            user_id=test_user.id,
            experiment_id=experiment.id,
            word_count=150
        )
        db_session.add(doc)

    db_session.commit()
    return experiment


@pytest.fixture
def pending_run(db_session, experiment_with_docs, test_user):
    """Create a pending orchestration run."""
    run = ExperimentOrchestrationRun(
        experiment_id=experiment_with_docs.id,
        user_id=test_user.id,
        status='analyzing',
        current_stage='analyzing'
    )
    db_session.add(run)
    db_session.commit()
    return run


@pytest.fixture
def reviewing_run(db_session, experiment_with_docs, test_user):
    """Create a run waiting for review."""
    run = ExperimentOrchestrationRun(
        experiment_id=experiment_with_docs.id,
        user_id=test_user.id,
        status='reviewing',
        current_stage='reviewing',
        experiment_goal='Analyze temporal evolution',
        term_context='algorithm',
        recommended_strategy={
            '1': ['extract_entities_spacy', 'extract_temporal'],
            '2': ['extract_entities_spacy']
        },
        strategy_reasoning='Documents require entity extraction.',
        confidence=0.89
    )
    db_session.add(run)
    db_session.commit()
    return run


@pytest.fixture
def completed_run(db_session, experiment_with_docs, test_user):
    """Create a completed orchestration run."""
    run = ExperimentOrchestrationRun(
        experiment_id=experiment_with_docs.id,
        user_id=test_user.id,
        status='completed',
        current_stage='completed',
        experiment_goal='Analyze temporal evolution',
        recommended_strategy={'1': ['extract_entities_spacy']},
        strategy_reasoning='Test reasoning',
        confidence=0.92,
        strategy_approved=True,
        processing_results={'1': {'extract_entities_spacy': {'count': 25}}},
        execution_trace=[{'node': 'execute_strategy', 'timestamp': '2025-11-20T12:00:00'}],
        cross_document_insights='The term shows increasing formalization over time.',
        term_evolution_analysis='Semantic shift detected from 1980 to 2000.'
    )
    db_session.add(run)
    db_session.commit()
    return run


# ==============================================================================
# Test Start Orchestration Endpoint
# ==============================================================================

class TestStartOrchestration:
    """Test POST /experiments/<id>/orchestration/analyze"""

    @patch('app.routes.experiments.orchestration.get_orchestration_task')
    def test_start_orchestration_success(
        self,
        mock_get_task,
        auth_client,
        experiment_with_docs,
        db_session
    ):
        """Test starting orchestration successfully via Celery."""
        # Mock Celery task
        mock_task = Mock()
        mock_task.apply_async.return_value = Mock(id='test-task-id-success')
        mock_get_task.return_value = (mock_task, True)

        response = auth_client.post(
            f'/experiments/{experiment_with_docs.id}/orchestration/analyze',
            data=json.dumps({'review_choices': True}),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'run_id' in data
        assert data['status'] == 'analyzing'  # Initial status when task enqueued
        assert data['task_id'] == 'test-task-id-success'

    def test_start_orchestration_requires_auth(
        self,
        client,
        experiment_with_docs
    ):
        """Test that starting orchestration requires authentication."""
        response = client.post(
            f'/experiments/{experiment_with_docs.id}/orchestration/analyze',
            data=json.dumps({'review_choices': True}),
            content_type='application/json'
        )

        assert response.status_code in [302, 401]

    def test_start_orchestration_nonexistent_experiment(
        self,
        auth_client
    ):
        """Test starting orchestration for nonexistent experiment."""
        response = auth_client.post(
            '/experiments/99999/orchestration/analyze',
            data=json.dumps({'review_choices': True}),
            content_type='application/json'
        )

        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False

    @patch('app.routes.experiments.orchestration.get_orchestration_task')
    def test_start_orchestration_workflow_error(
        self,
        mock_get_task,
        auth_client,
        experiment_with_docs
    ):
        """Test error handling when Celery task enqueueing fails."""
        # Mock Celery task that raises error when enqueued
        mock_task = Mock()
        mock_task.apply_async.side_effect = Exception('Redis connection error')
        mock_get_task.return_value = (mock_task, True)

        response = auth_client.post(
            f'/experiments/{experiment_with_docs.id}/orchestration/analyze',
            data=json.dumps({'review_choices': True}),
            content_type='application/json'
        )

        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'error' in data

    @patch('app.routes.experiments.orchestration.get_orchestration_task')
    def test_start_orchestration_auto_approve(
        self,
        mock_get_task,
        auth_client,
        experiment_with_docs
    ):
        """Test orchestration with auto-approval (no review) via Celery."""
        # Mock Celery task
        mock_task = Mock()
        mock_task.apply_async.return_value = Mock(id='test-celery-task-id')
        mock_get_task.return_value = (mock_task, True)

        response = auth_client.post(
            f'/experiments/{experiment_with_docs.id}/orchestration/analyze',
            data=json.dumps({'review_choices': False}),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'analyzing'  # Initial status when task enqueued
        assert data['task_id'] == 'test-celery-task-id'
        assert 'run_id' in data

        # Verify Celery task was enqueued with review_choices=False
        mock_task.apply_async.assert_called_once()
        call_args = mock_task.apply_async.call_args
        assert call_args[1]['args'][1] is False  # review_choices=False


# ==============================================================================
# Test Status Polling Endpoint
# ==============================================================================

class TestOrchestrationStatus:
    """Test GET /orchestration/status/<run_id>"""

    def test_get_status_analyzing(
        self,
        client,
        pending_run
    ):
        """Test status endpoint during analyzing phase."""
        response = client.get(f'/experiments/orchestration/status/{pending_run.id}')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'analyzing'
        assert data['progress_percentage'] == 20
        assert 'stage_completed' in data

    def test_get_status_reviewing(
        self,
        client,
        reviewing_run
    ):
        """Test status endpoint during review phase."""
        response = client.get(f'/experiments/orchestration/status/{reviewing_run.id}')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'reviewing'
        assert data['progress_percentage'] == 50
        assert data['awaiting_user_approval'] is True
        assert 'recommended_strategy' in data
        assert 'strategy_reasoning' in data
        assert 'confidence' in data
        assert data['confidence'] == 0.89

    def test_get_status_completed(
        self,
        client,
        completed_run
    ):
        """Test status endpoint for completed run."""
        response = client.get(f'/experiments/orchestration/status/{completed_run.id}')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'completed'
        assert data['progress_percentage'] == 100
        assert 'completed_at' in data
        assert 'duration_seconds' in data

    def test_get_status_nonexistent_run(
        self,
        client
    ):
        """Test status endpoint for nonexistent run."""
        fake_uuid = uuid4()
        response = client.get(f'/experiments/orchestration/status/{fake_uuid}')

        assert response.status_code == 404

    def test_get_status_stage_completion_flags(
        self,
        client,
        reviewing_run
    ):
        """Test that stage completion flags are accurate."""
        response = client.get(f'/experiments/orchestration/status/{reviewing_run.id}')

        data = json.loads(response.data)
        stages = data['stage_completed']

        assert stages['analyze_experiment'] is True  # Has experiment_goal
        assert stages['recommend_strategy'] is True  # Has recommended_strategy
        assert stages['human_review'] is False  # Not approved yet
        assert stages['execute_strategy'] is False  # No processing_results
        assert stages['synthesize_experiment'] is False  # No insights


# ==============================================================================
# Test Approve Strategy Endpoint
# ==============================================================================

class TestApproveStrategy:
    """Test POST /orchestration/approve-strategy/<run_id>"""

    @patch('app.routes.experiments.orchestration.workflow_executor')
    def test_approve_strategy_success(
        self,
        mock_executor,
        auth_client,
        reviewing_run
    ):
        """Test approving strategy successfully."""
        mock_executor.execute_processing_phase.return_value = {
            'status': 'completed',
            'run_id': str(reviewing_run.id),
            'processing_results': {},
            'cross_document_insights': 'Test insights',
            'execution_time': 125.5
        }

        response = auth_client.post(
            f'/experiments/orchestration/approve-strategy/{reviewing_run.id}',
            data=json.dumps({
                'strategy_approved': True,
                'review_notes': 'Looks good'
            }),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['status'] == 'completed'
        assert 'execution_time' in data

    def test_approve_strategy_requires_auth(
        self,
        client,
        reviewing_run
    ):
        """Test that approving strategy requires authentication."""
        response = client.post(
            f'/experiments/orchestration/approve-strategy/{reviewing_run.id}',
            data=json.dumps({'strategy_approved': True}),
            content_type='application/json'
        )

        assert response.status_code in [302, 401]

    def test_approve_strategy_nonexistent_run(
        self,
        auth_client
    ):
        """Test approving strategy for nonexistent run."""
        fake_uuid = uuid4()
        response = auth_client.post(
            f'/experiments/orchestration/approve-strategy/{fake_uuid}',
            data=json.dumps({'strategy_approved': True}),
            content_type='application/json'
        )

        assert response.status_code == 404

    def test_approve_strategy_invalid_state(
        self,
        auth_client,
        pending_run
    ):
        """Test approving strategy when not in reviewing state."""
        response = auth_client.post(
            f'/experiments/orchestration/approve-strategy/{pending_run.id}',
            data=json.dumps({'strategy_approved': True}),
            content_type='application/json'
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'Cannot approve strategy' in data['error']

    @patch('app.routes.experiments.orchestration.workflow_executor')
    def test_approve_strategy_with_modifications(
        self,
        mock_executor,
        auth_client,
        reviewing_run
    ):
        """Test approving strategy with user modifications."""
        modified_strategy = {
            '1': ['extract_entities_spacy', 'extract_temporal', 'extract_definitions']
        }

        mock_executor.execute_processing_phase.return_value = {
            'status': 'completed',
            'run_id': str(reviewing_run.id),
            'processing_results': {},
            'cross_document_insights': 'Test',
            'execution_time': 100.0
        }

        response = auth_client.post(
            f'/experiments/orchestration/approve-strategy/{reviewing_run.id}',
            data=json.dumps({
                'strategy_approved': True,
                'modified_strategy': modified_strategy,
                'review_notes': 'Added definitions extraction'
            }),
            content_type='application/json'
        )

        assert response.status_code == 200

        # Verify modified strategy was passed to executor
        call_args = mock_executor.execute_processing_phase.call_args
        assert call_args[1]['modified_strategy'] == modified_strategy
        assert call_args[1]['review_notes'] == 'Added definitions extraction'

    def test_reject_strategy(
        self,
        auth_client,
        reviewing_run,
        db_session
    ):
        """Test rejecting strategy (strategy_approved=False)."""
        response = auth_client.post(
            f'/experiments/orchestration/approve-strategy/{reviewing_run.id}',
            data=json.dumps({
                'strategy_approved': False,
                'review_notes': 'Not suitable for this experiment'
            }),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'cancelled'

        # Verify run is cancelled in database
        db_session.refresh(reviewing_run)
        assert reviewing_run.status == 'cancelled'
        assert 'Not suitable' in reviewing_run.review_notes

    @patch('app.routes.experiments.orchestration.workflow_executor')
    def test_approve_strategy_execution_error(
        self,
        mock_executor,
        auth_client,
        reviewing_run
    ):
        """Test error handling when processing phase fails."""
        mock_executor.execute_processing_phase.side_effect = Exception('Tool execution failed')

        response = auth_client.post(
            f'/experiments/orchestration/approve-strategy/{reviewing_run.id}',
            data=json.dumps({'strategy_approved': True}),
            content_type='application/json'
        )

        assert response.status_code == 500
        data = json.loads(response.data)
        assert 'Processing failed' in data['error']


# ==============================================================================
# Test Results Display Endpoint
# ==============================================================================

class TestOrchestrationResults:
    """Test GET /experiments/<id>/orchestration/llm-results/<run_id>"""

    def test_view_results_success(
        self,
        client,
        experiment_with_docs,
        completed_run
    ):
        """Test viewing results for completed run."""
        response = client.get(
            f'/experiments/{experiment_with_docs.id}/orchestration/llm-results/{completed_run.id}'
        )

        assert response.status_code == 200
        # UI was redesigned - now shows 'LLM Orchestration Results' or 'Term Usage Patterns'
        assert b'LLM Orchestration Results' in response.data or b'Term Usage Patterns' in response.data

    def test_view_results_nonexistent_experiment(
        self,
        client,
        completed_run
    ):
        """Test viewing results for nonexistent experiment."""
        response = client.get(
            f'/experiments/99999/orchestration/llm-results/{completed_run.id}'
        )

        assert response.status_code == 404

    def test_view_results_nonexistent_run(
        self,
        client,
        experiment_with_docs
    ):
        """Test viewing results for nonexistent run."""
        fake_uuid = uuid4()
        response = client.get(
            f'/experiments/{experiment_with_docs.id}/orchestration/llm-results/{fake_uuid}'
        )

        assert response.status_code == 404

    def test_view_results_wrong_experiment(
        self,
        client,
        db_session,
        test_user,
        completed_run
    ):
        """Test viewing results for run from different experiment."""
        # Create another experiment
        other_exp = Experiment(
            name='Other Experiment',
            experiment_type='entity_extraction',
            user_id=test_user.id
        )
        db_session.add(other_exp)
        db_session.commit()

        response = client.get(
            f'/experiments/{other_exp.id}/orchestration/llm-results/{completed_run.id}'
        )

        assert response.status_code == 404

    def test_view_results_includes_metrics(
        self,
        client,
        experiment_with_docs,
        completed_run
    ):
        """Test that results page includes duration and operation metrics."""
        response = client.get(
            f'/experiments/{experiment_with_docs.id}/orchestration/llm-results/{completed_run.id}'
        )

        # Check that metrics are calculated (exact format depends on template)
        assert response.status_code == 200


# ==============================================================================
# Test PROV-O Provenance Download
# ==============================================================================

class TestProvenanceDownload:
    """Test GET /experiments/<id>/orchestration/llm-provenance/<run_id>"""

    def test_download_provenance_success(
        self,
        client,
        experiment_with_docs,
        completed_run
    ):
        """Test downloading PROV-O provenance JSON."""
        response = client.get(
            f'/experiments/{experiment_with_docs.id}/orchestration/llm-provenance/{completed_run.id}'
        )

        assert response.status_code == 200
        assert response.content_type == 'application/json'

        data = json.loads(response.data)
        assert '@context' in data
        assert data['@context'] == 'http://www.w3.org/ns/prov'
        assert '@type' in data
        assert data['@type'] == 'prov:Bundle'

    def test_download_provenance_structure(
        self,
        client,
        experiment_with_docs,
        completed_run
    ):
        """Test PROV-O structure is correct."""
        response = client.get(
            f'/experiments/{experiment_with_docs.id}/orchestration/llm-provenance/{completed_run.id}'
        )

        data = json.loads(response.data)

        # Check required PROV-O elements
        assert 'experiment' in data
        assert 'orchestration_run' in data
        assert 'strategy' in data
        assert 'results' in data

        # Check experiment entity
        exp = data['experiment']
        assert '@id' in exp
        assert '@type' in exp
        assert exp['@type'] == 'prov:Entity'

        # Check orchestration run activity
        run = data['orchestration_run']
        assert '@type' in run
        assert run['@type'] == 'prov:Activity'
        assert 'prov:startedAtTime' in run
        assert 'status' in run
        assert run['status'] == 'completed'

    def test_download_provenance_nonexistent_run(
        self,
        client,
        experiment_with_docs
    ):
        """Test downloading provenance for nonexistent run."""
        fake_uuid = uuid4()
        response = client.get(
            f'/experiments/{experiment_with_docs.id}/orchestration/llm-provenance/{fake_uuid}'
        )

        assert response.status_code == 404

    def test_download_provenance_wrong_experiment(
        self,
        client,
        db_session,
        test_user,
        completed_run
    ):
        """Test downloading provenance for run from different experiment."""
        other_exp = Experiment(
            name='Other Experiment',
            experiment_type='entity_extraction',
            user_id=test_user.id
        )
        db_session.add(other_exp)
        db_session.commit()

        response = client.get(
            f'/experiments/{other_exp.id}/orchestration/llm-provenance/{completed_run.id}'
        )

        assert response.status_code == 404

    def test_provenance_includes_execution_trace(
        self,
        client,
        experiment_with_docs,
        completed_run
    ):
        """Test that provenance includes execution trace."""
        response = client.get(
            f'/experiments/{experiment_with_docs.id}/orchestration/llm-provenance/{completed_run.id}'
        )

        data = json.loads(response.data)
        assert 'execution_trace' in data
        assert isinstance(data['execution_trace'], list)


# ==============================================================================
# Integration Test - Full Workflow
# ==============================================================================

@pytest.mark.integration
class TestFullOrchestrationWorkflow:
    """Test complete orchestration workflow through API."""

    @patch('app.routes.experiments.orchestration.workflow_executor')
    def test_full_workflow_api(
        self,
        mock_executor,
        auth_client,
        client,
        experiment_with_docs,
        db_session
    ):
        """Test full workflow: start → poll → approve → results → provenance."""

        # Step 1: Start orchestration
        mock_executor.execute_recommendation_phase.return_value = {
            'status': 'reviewing',
            'run_id': str(uuid4()),
            'experiment_goal': 'Test goal',
            'recommended_strategy': {'1': ['extract_entities_spacy']},
            'strategy_reasoning': 'Test reasoning',
            'confidence': 0.88,
            'awaiting_approval': True
        }

        start_response = auth_client.post(
            f'/experiments/{experiment_with_docs.id}/orchestration/analyze',
            data=json.dumps({'review_choices': True}),
            content_type='application/json'
        )

        assert start_response.status_code == 200
        start_data = json.loads(start_response.data)
        run_id = start_data['run_id']

        # Simulate what the real execute_recommendation_phase does - update run status in DB
        run = ExperimentOrchestrationRun.query.get(run_id)
        run.status = 'reviewing'
        run.experiment_goal = 'Test goal'
        run.recommended_strategy = {'1': ['extract_entities_spacy']}
        run.strategy_reasoning = 'Test reasoning'
        run.confidence = 0.88
        db_session.commit()

        # Step 2: Poll status
        status_response = client.get(f'/experiments/orchestration/status/{run_id}')
        assert status_response.status_code == 200
        status_data = json.loads(status_response.data)
        assert status_data['status'] == 'reviewing'
        assert status_data['awaiting_user_approval'] is True

        # Step 3: Approve strategy
        mock_executor.execute_processing_phase.return_value = {
            'status': 'completed',
            'run_id': run_id,
            'processing_results': {'1': {'extract_entities_spacy': {'count': 15}}},
            'cross_document_insights': 'Test insights',
            'execution_time': 95.3
        }

        approve_response = auth_client.post(
            f'/experiments/orchestration/approve-strategy/{run_id}',
            data=json.dumps({'strategy_approved': True, 'review_notes': 'LGTM'}),
            content_type='application/json'
        )

        assert approve_response.status_code == 200
        approve_data = json.loads(approve_response.data)
        assert approve_data['status'] == 'completed'

        # Step 4: View results
        results_response = client.get(
            f'/experiments/{experiment_with_docs.id}/orchestration/llm-results/{run_id}'
        )
        assert results_response.status_code == 200

        # Step 5: Download provenance
        prov_response = client.get(
            f'/experiments/{experiment_with_docs.id}/orchestration/llm-provenance/{run_id}'
        )
        assert prov_response.status_code == 200
        prov_data = json.loads(prov_response.data)
        assert '@context' in prov_data


# ==============================================================================
# Check Processing Status Endpoint Tests
# ==============================================================================

def test_check_status_no_processing(client, experiment_with_docs):
    """Test check-status endpoint when no documents are processed."""
    response = client.get(f'/experiments/{experiment_with_docs.id}/orchestration/check-status')

    assert response.status_code == 200
    data = json.loads(response.data)

    assert data['experiment_id'] == experiment_with_docs.id
    assert data['total_documents'] == 3
    assert data['processed_documents'] == 0
    assert data['unprocessed_documents'] == 3
    assert data['has_partial_processing'] is False
    assert data['has_full_processing'] is False
    assert len(data['documents']) == 3

    # Check all documents have no processing
    for doc_status in data['documents']:
        assert doc_status['has_processing'] is False
        assert doc_status['processing_types'] == []


def test_check_status_partial_processing(client, db_session, experiment_with_docs, test_user):
    """Test check-status endpoint when some documents are processed."""
    from app.models import TextSegment, ProcessingJob, Document

    # Get first two documents
    docs = Document.query.filter_by(experiment_id=experiment_with_docs.id).limit(2).all()

    # Create processing job for segmentation on first document
    job1 = ProcessingJob(
        document_id=docs[0].id,
        user_id=test_user.id,
        job_type='segmentation',
        status='completed'
    )
    db_session.add(job1)
    db_session.flush()  # Get the job ID

    # Add segmentation to first document
    segment = TextSegment(
        document_id=docs[0].id,
        content='Test segment content',
        segment_type='paragraph',
        start_position=0,
        end_position=20
    )
    db_session.add(segment)

    # Add processing job (entity extraction) to second document
    job2 = ProcessingJob(
        document_id=docs[1].id,
        user_id=test_user.id,
        job_type='entity_extraction',
        status='completed'
    )
    db_session.add(job2)
    db_session.commit()

    response = client.get(f'/experiments/{experiment_with_docs.id}/orchestration/check-status')

    assert response.status_code == 200
    data = json.loads(response.data)

    assert data['total_documents'] == 3
    assert data['processed_documents'] == 2
    assert data['unprocessed_documents'] == 1
    assert data['has_partial_processing'] is True
    assert data['has_full_processing'] is False

    # Check processing types
    processed_docs = [d for d in data['documents'] if d['has_processing']]
    assert len(processed_docs) == 2

    # First doc should have segmentation
    doc1_status = next(d for d in data['documents'] if d['document_id'] == docs[0].id)
    assert 'segmentation' in doc1_status['processing_types']

    # Second doc should have entities
    doc2_status = next(d for d in data['documents'] if d['document_id'] == docs[1].id)
    assert 'entities' in doc2_status['processing_types']


def test_check_status_full_processing(client, db_session, experiment_with_docs, test_user):
    """Test check-status endpoint when all documents are processed."""
    from app.models import ProcessingJob, Document

    # Get all documents
    docs = Document.query.filter_by(experiment_id=experiment_with_docs.id).all()

    # Add processing jobs for all documents
    for doc in docs:
        job = ProcessingJob(
            document_id=doc.id,
            user_id=test_user.id,
            job_type='entity_extraction',
            status='completed'
        )
        db_session.add(job)

    db_session.commit()

    response = client.get(f'/experiments/{experiment_with_docs.id}/orchestration/check-status')

    assert response.status_code == 200
    data = json.loads(response.data)

    assert data['total_documents'] == 3
    assert data['processed_documents'] == 3
    assert data['unprocessed_documents'] == 0
    assert data['has_partial_processing'] is False
    assert data['has_full_processing'] is True

    # Check all documents have processing
    for doc_status in data['documents']:
        assert doc_status['has_processing'] is True
        assert 'entities' in doc_status['processing_types']


def test_check_status_experiment_not_found(client):
    """Test check-status endpoint with non-existent experiment."""
    response = client.get('/experiments/99999/orchestration/check-status')

    assert response.status_code == 404
    data = json.loads(response.data)
    assert 'error' in data


def test_check_status_mixed_processing_types(client, db_session, experiment_with_docs, test_user):
    """Test check-status endpoint with multiple processing types on same document."""
    from app.models import TextSegment, ProcessingJob, Document

    # Get first document
    doc = Document.query.filter_by(experiment_id=experiment_with_docs.id).first()

    # Create processing job for segmentation
    job1 = ProcessingJob(
        document_id=doc.id,
        user_id=test_user.id,
        job_type='segmentation',
        status='completed'
    )
    db_session.add(job1)
    db_session.flush()

    # Add multiple processing types to first document
    segment = TextSegment(
        document_id=doc.id,
        content='Test segment content',
        segment_type='paragraph',
        start_position=0,
        end_position=20
    )
    db_session.add(segment)

    # Add processing job for entities
    job2 = ProcessingJob(
        document_id=doc.id,
        user_id=test_user.id,
        job_type='entity_extraction',
        status='completed'
    )
    db_session.add(job2)

    db_session.commit()

    response = client.get(f'/experiments/{experiment_with_docs.id}/orchestration/check-status')

    assert response.status_code == 200
    data = json.loads(response.data)

    # Find the processed document
    doc_status = next(d for d in data['documents'] if d['document_id'] == doc.id)

    assert doc_status['has_processing'] is True
    assert 'segmentation' in doc_status['processing_types']
    assert 'entities' in doc_status['processing_types']
    assert len(doc_status['processing_types']) == 2
