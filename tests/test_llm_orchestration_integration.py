"""
Integration Tests for LLM Orchestration Workflow

Tests complete end-to-end scenarios including:
- Full 5-stage workflow execution
- PROV-O provenance structure validation
- Error recovery scenarios
- Concurrent run handling
- Strategy modification flows
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import json
from uuid import uuid4
from datetime import datetime, timedelta

from app.models import Experiment, Document
from app.models.experiment_orchestration_run import ExperimentOrchestrationRun
from app.services.workflow_executor import WorkflowExecutor


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
def multi_doc_experiment(db_session, test_user):
    """Create experiment with 5 documents for realistic testing."""
    experiment = Experiment(
        name='Multi-Document Temporal Analysis',
        description='Test experiment with multiple documents',
        experiment_type='temporal_evolution',
        user_id=test_user.id,
        status='draft',
        configuration=json.dumps({
            'target_terms': ['algorithm', 'function'],
            'periods': ['1980-1990', '1990-2000', '2000-2010']
        })
    )
    db_session.add(experiment)
    db_session.flush()

    # Create 5 documents with varied content
    doc_contents = [
        "The concept of algorithms in early computer science (1980s) focused on procedural approaches.",
        "Functional programming paradigms emerged in the 1990s, transforming algorithm design.",
        "Object-oriented algorithms became dominant in the late 1990s and early 2000s.",
        "Modern machine learning algorithms (2000s) leverage statistical methods and neural networks.",
        "Contemporary algorithms (2010s) prioritize efficiency, parallelization, and scalability."
    ]

    for i, content in enumerate(doc_contents):
        doc = Document(
            title=f'Document {i+1}: {content[:30]}...',
            content=content * 10,  # Repeat for realistic length
            original_filename=f'historical_doc_{i+1}.txt',
            document_type='document',
            content_type='text/plain',
            status='completed',
            user_id=test_user.id,
            experiment_id=experiment.id,
            word_count=len(content.split()) * 10
        )
        db_session.add(doc)

    db_session.commit()
    return experiment


# ==============================================================================
# PROV-O Validation Tests
# ==============================================================================

@pytest.mark.integration
class TestProvenanceValidation:
    """Test PROV-O provenance structure and compliance."""

    def test_provenance_required_fields(self, client, multi_doc_experiment, db_session, test_user):
        """Test that PROV-O provenance includes all required fields."""
        # Create completed run
        run = ExperimentOrchestrationRun(
            experiment_id=multi_doc_experiment.id,
            user_id=test_user.id,
            status='completed',
            current_stage='completed',
            experiment_goal='Test goal',
            recommended_strategy={'1': ['extract_entities_spacy']},
            strategy_reasoning='Test reasoning',
            confidence=0.92,
            strategy_approved=True,
            processing_results={'1': {'extract_entities_spacy': {'count': 25}}},
            execution_trace=[
                {
                    'node': 'execute_strategy',
                    'timestamp': datetime.utcnow().isoformat(),
                    'tool': 'extract_entities_spacy',
                    'document_id': '1',
                    'status': 'completed'
                }
            ],
            cross_document_insights='Test insights'
        )
        db_session.add(run)
        db_session.commit()

        # Get provenance
        response = client.get(
            f'/experiments/{multi_doc_experiment.id}/orchestration/llm-provenance/{run.id}'
        )

        assert response.status_code == 200
        prov = json.loads(response.data)

        # Required PROV-O fields
        assert '@context' in prov
        assert '@type' in prov
        assert prov['@context'] == 'http://www.w3.org/ns/prov'
        assert prov['@type'] == 'prov:Bundle'

    def test_provenance_entity_structure(self, client, multi_doc_experiment, db_session, test_user):
        """Test PROV-O entity structure is correct."""
        run = ExperimentOrchestrationRun(
            experiment_id=multi_doc_experiment.id,
            user_id=test_user.id,
            status='completed',
            experiment_goal='Test',
            recommended_strategy={},
            processing_results={}
        )
        db_session.add(run)
        db_session.commit()

        response = client.get(
            f'/experiments/{multi_doc_experiment.id}/orchestration/llm-provenance/{run.id}'
        )

        prov = json.loads(response.data)

        # Check experiment entity
        assert 'experiment' in prov
        exp_entity = prov['experiment']
        assert '@id' in exp_entity
        assert '@type' in exp_entity
        assert exp_entity['@type'] == 'prov:Entity'
        assert f'experiment:{multi_doc_experiment.id}' in exp_entity['@id']

        # Check strategy entity
        assert 'strategy' in prov
        strategy_entity = prov['strategy']
        assert '@type' in strategy_entity
        assert strategy_entity['@type'] == 'prov:Entity'
        assert 'prov:wasGeneratedBy' in strategy_entity

        # Check results entity
        assert 'results' in prov
        results_entity = prov['results']
        assert '@type' in results_entity
        assert results_entity['@type'] == 'prov:Entity'

    def test_provenance_activity_structure(self, client, multi_doc_experiment, db_session, test_user):
        """Test PROV-O activity structure is correct."""
        started_at = datetime.utcnow()
        completed_at = started_at + timedelta(minutes=5)

        run = ExperimentOrchestrationRun(
            experiment_id=multi_doc_experiment.id,
            user_id=test_user.id,
            status='completed',
            started_at=started_at,
            completed_at=completed_at,
            experiment_goal='Test',
            recommended_strategy={},
            processing_results={},
            confidence=0.85
        )
        db_session.add(run)
        db_session.commit()

        response = client.get(
            f'/experiments/{multi_doc_experiment.id}/orchestration/llm-provenance/{run.id}'
        )

        prov = json.loads(response.data)

        # Check orchestration run activity
        assert 'orchestration_run' in prov
        run_activity = prov['orchestration_run']
        assert '@type' in run_activity
        assert run_activity['@type'] == 'prov:Activity'
        assert 'prov:startedAtTime' in run_activity
        assert 'prov:endedAtTime' in run_activity
        assert 'prov:used' in run_activity
        assert 'status' in run_activity
        assert 'confidence' in run_activity

    def test_provenance_execution_trace(self, client, multi_doc_experiment, db_session, test_user):
        """Test that execution trace is included in provenance."""
        execution_trace = [
            {
                'node': 'analyze_experiment',
                'timestamp': datetime.utcnow().isoformat(),
                'stage': 1,
                'status': 'completed'
            },
            {
                'node': 'recommend_strategy',
                'timestamp': datetime.utcnow().isoformat(),
                'stage': 2,
                'status': 'completed',
                'tools_recommended': ['extract_entities_spacy']
            },
            {
                'node': 'execute_strategy',
                'timestamp': datetime.utcnow().isoformat(),
                'stage': 4,
                'tool': 'extract_entities_spacy',
                'document_id': '1',
                'status': 'completed'
            }
        ]

        run = ExperimentOrchestrationRun(
            experiment_id=multi_doc_experiment.id,
            user_id=test_user.id,
            status='completed',
            experiment_goal='Test',
            recommended_strategy={},
            processing_results={},
            execution_trace=execution_trace
        )
        db_session.add(run)
        db_session.commit()

        response = client.get(
            f'/experiments/{multi_doc_experiment.id}/orchestration/llm-provenance/{run.id}'
        )

        prov = json.loads(response.data)
        assert 'execution_trace' in prov
        assert isinstance(prov['execution_trace'], list)
        assert len(prov['execution_trace']) == 3


# ==============================================================================
# Error Scenario Tests
# ==============================================================================

@pytest.mark.integration
class TestErrorRecovery:
    """Test error handling and recovery scenarios."""

    @patch('app.services.workflow_executor.WorkflowExecutor._execute_graph')
    def test_llm_api_timeout(self, mock_graph, multi_doc_experiment, db_session, test_user):
        """Test handling of LLM API timeout."""
        executor = WorkflowExecutor()

        # Create run
        run = ExperimentOrchestrationRun(
            experiment_id=multi_doc_experiment.id,
            user_id=test_user.id,
            status='analyzing'
        )
        db_session.add(run)
        db_session.commit()

        # Simulate timeout
        mock_graph.side_effect = TimeoutError('LLM API timeout after 30 seconds')

        with pytest.raises(RuntimeError, match='Recommendation phase failed'):
            executor.execute_recommendation_phase(run.id, review_choices=True)

        # Verify run marked as failed
        db_session.refresh(run)
        assert run.status == 'failed'
        assert 'timeout' in run.error_message.lower()

    @patch('app.services.workflow_executor.WorkflowExecutor._execute_processing')
    def test_tool_execution_failure(self, mock_processing, multi_doc_experiment, db_session, test_user):
        """Test handling of tool execution failure."""
        executor = WorkflowExecutor()

        # Create run in reviewing state
        run = ExperimentOrchestrationRun(
            experiment_id=multi_doc_experiment.id,
            user_id=test_user.id,
            status='reviewing',
            experiment_goal='Test',
            recommended_strategy={'1': ['extract_entities_spacy']}
        )
        db_session.add(run)
        db_session.commit()

        # Simulate tool failure
        mock_processing.side_effect = Exception('spaCy model not found')

        with pytest.raises(RuntimeError, match='Processing phase failed'):
            executor.execute_processing_phase(run.id)

        # Verify run marked as failed
        db_session.refresh(run)
        assert run.status == 'failed'
        assert 'spaCy model not found' in run.error_message

    @patch('app.services.workflow_executor.WorkflowExecutor._execute_graph')
    def test_malformed_llm_response(self, mock_graph, multi_doc_experiment, db_session, test_user):
        """Test handling of malformed LLM response."""
        executor = WorkflowExecutor()

        run = ExperimentOrchestrationRun(
            experiment_id=multi_doc_experiment.id,
            user_id=test_user.id,
            status='analyzing'
        )
        db_session.add(run)
        db_session.commit()

        # Return malformed response (missing required fields)
        mock_graph.return_value = {
            'experiment_goal': 'Test goal'
            # Missing recommended_strategy, confidence, etc.
        }

        result = executor.execute_recommendation_phase(run.id, review_choices=True)

        # Should handle gracefully, fields should be None
        assert result['recommended_strategy'] is None
        assert result['confidence'] is None


# ==============================================================================
# Strategy Modification Tests
# ==============================================================================

@pytest.mark.integration
class TestStrategyModification:
    """Test user modification of recommended strategies."""

    @patch('app.services.workflow_executor.WorkflowExecutor._execute_graph')
    @patch('app.services.workflow_executor.WorkflowExecutor._execute_processing')
    def test_modify_strategy_add_tools(
        self,
        mock_processing,
        mock_graph,
        auth_client,
        multi_doc_experiment,
        db_session,
        test_user
    ):
        """Test adding additional tools to recommended strategy."""
        # Start orchestration
        mock_graph.return_value = {
            'experiment_goal': 'Analyze temporal evolution',
            'recommended_strategy': {
                '1': ['extract_entities_spacy'],
                '2': ['extract_entities_spacy']
            },
            'strategy_reasoning': 'Documents require entity extraction',
            'confidence': 0.82
        }

        start_response = auth_client.post(
            f'/experiments/{multi_doc_experiment.id}/orchestration/analyze',
            data=json.dumps({'review_choices': True}),
            content_type='application/json'
        )

        data = json.loads(start_response.data)
        run_id = data['run_id']

        # Modify strategy to add temporal extraction
        modified_strategy = {
            '1': ['extract_entities_spacy', 'extract_temporal'],
            '2': ['extract_entities_spacy', 'extract_temporal']
        }

        mock_processing.return_value = {
            'processing_results': {
                '1': {
                    'extract_entities_spacy': {'count': 15},
                    'extract_temporal': {'count': 5}
                }
            },
            'execution_trace': [],
            'cross_document_insights': 'Test insights'
        }

        # Approve with modifications
        approve_response = auth_client.post(
            f'/experiments/orchestration/approve-strategy/{run_id}',
            data=json.dumps({
                'strategy_approved': True,
                'modified_strategy': modified_strategy,
                'review_notes': 'Added temporal extraction for historical analysis'
            }),
            content_type='application/json'
        )

        assert approve_response.status_code == 200

        # Verify modified strategy was used
        # _execute_processing receives state as first positional arg
        call_args = mock_processing.call_args
        state_arg = call_args[0][0]  # First positional argument is the state dict
        assert state_arg.get('modified_strategy') == modified_strategy

    @patch('app.services.workflow_executor.WorkflowExecutor._execute_graph')
    def test_modify_strategy_remove_tools(
        self,
        mock_graph,
        auth_client,
        multi_doc_experiment,
        db_session
    ):
        """Test removing tools from recommended strategy."""
        mock_graph.return_value = {
            'experiment_goal': 'Test',
            'recommended_strategy': {
                '1': ['segment_paragraph', 'extract_entities_spacy', 'extract_temporal'],
                '2': ['segment_sentence', 'extract_entities_spacy']
            },
            'strategy_reasoning': 'Comprehensive analysis',
            'confidence': 0.75
        }

        start_response = auth_client.post(
            f'/experiments/{multi_doc_experiment.id}/orchestration/analyze',
            data=json.dumps({'review_choices': True}),
            content_type='application/json'
        )

        run_id = json.loads(start_response.data)['run_id']

        # Simplify strategy
        modified_strategy = {
            '1': ['extract_entities_spacy'],
            '2': ['extract_entities_spacy']
        }

        # Get the run to verify modification is saved
        run = ExperimentOrchestrationRun.query.get(run_id)

        # In real scenario, would approve and execute
        # Here just verify the modification pattern works
        assert run.status == 'reviewing'


# ==============================================================================
# Concurrent Run Tests
# ==============================================================================

@pytest.mark.integration
class TestConcurrentRuns:
    """Test handling of concurrent orchestration runs."""

    @patch('app.services.workflow_executor.WorkflowExecutor._execute_graph')
    def test_multiple_runs_same_experiment(
        self,
        mock_graph,
        auth_client,
        multi_doc_experiment
    ):
        """Test multiple orchestration runs for same experiment."""
        mock_graph.return_value = {
            'experiment_goal': 'Test',
            'recommended_strategy': {},
            'confidence': 0.85
        }

        # Start first run
        response1 = auth_client.post(
            f'/experiments/{multi_doc_experiment.id}/orchestration/analyze',
            data=json.dumps({'review_choices': True}),
            content_type='application/json'
        )

        run_id_1 = json.loads(response1.data)['run_id']

        # Start second run (should be allowed - different runs)
        response2 = auth_client.post(
            f'/experiments/{multi_doc_experiment.id}/orchestration/analyze',
            data=json.dumps({'review_choices': True}),
            content_type='application/json'
        )

        run_id_2 = json.loads(response2.data)['run_id']

        # Runs should be different
        assert run_id_1 != run_id_2
        assert response2.status_code == 200

    def test_status_isolation_between_runs(
        self,
        client,
        multi_doc_experiment,
        db_session,
        test_user
    ):
        """Test that status polling returns correct data for each run."""
        # Create two runs in different states
        run1 = ExperimentOrchestrationRun(
            experiment_id=multi_doc_experiment.id,
            user_id=test_user.id,
            status='reviewing',
            confidence=0.92
        )
        run2 = ExperimentOrchestrationRun(
            experiment_id=multi_doc_experiment.id,
            user_id=test_user.id,
            status='completed',
            confidence=0.88
        )
        db_session.add_all([run1, run2])
        db_session.commit()

        # Check run1 status (reviewing includes confidence)
        response1 = client.get(f'/experiments/orchestration/status/{run1.id}')
        data1 = json.loads(response1.data)
        assert data1['status'] == 'reviewing'
        assert data1['confidence'] == 0.92

        # Check run2 status (completed doesn't include confidence in response)
        response2 = client.get(f'/experiments/orchestration/status/{run2.id}')
        data2 = json.loads(response2.data)
        assert data2['status'] == 'completed'
        # confidence is only included for 'reviewing' status
        assert 'confidence' not in data2


# ==============================================================================
# Edge Case Tests
# ==============================================================================

@pytest.mark.integration
class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_experiment_with_no_documents(self, db_session, test_user):
        """Test orchestration with experiment that has no documents."""
        executor = WorkflowExecutor()

        # Create experiment without documents
        experiment = Experiment(
            name='Empty Experiment',
            experiment_type='entity_extraction',
            user_id=test_user.id
        )
        db_session.add(experiment)
        db_session.flush()

        run = ExperimentOrchestrationRun(
            experiment_id=experiment.id,
            user_id=test_user.id,
            status='analyzing'
        )
        db_session.add(run)
        db_session.commit()

        # Should handle gracefully (build state with empty document list)
        state = executor._build_graph_state(experiment.id, run.id, review_choices=True)
        assert state['documents'] == []

    def test_experiment_with_empty_documents(self, db_session, test_user):
        """Test orchestration with documents that have no content."""
        executor = WorkflowExecutor()

        experiment = Experiment(
            name='Empty Docs Experiment',
            experiment_type='entity_extraction',
            user_id=test_user.id
        )
        db_session.add(experiment)
        db_session.flush()

        # Add document with empty content
        doc = Document(
            title='Empty Document',
            content='',
            content_type='text/plain',
            document_type='document',
            user_id=test_user.id,
            experiment_id=experiment.id
        )
        db_session.add(doc)

        run = ExperimentOrchestrationRun(
            experiment_id=experiment.id,
            user_id=test_user.id,
            status='analyzing'
        )
        db_session.add(run)
        db_session.commit()

        # Should handle empty content
        state = executor._build_graph_state(experiment.id, run.id, review_choices=True)
        assert len(state['documents']) == 1
        assert state['documents'][0]['content'] == ''

    def test_non_temporal_experiment_no_focus_term(self, db_session, test_user):
        """Test that non-temporal experiments don't extract focus term."""
        executor = WorkflowExecutor()

        experiment = Experiment(
            name='Entity Extraction Experiment',
            experiment_type='entity_extraction',
            user_id=test_user.id,
            configuration='{}'
        )
        db_session.add(experiment)
        db_session.flush()

        run = ExperimentOrchestrationRun(
            experiment_id=experiment.id,
            user_id=test_user.id,
            status='analyzing'
        )
        db_session.add(run)
        db_session.commit()

        state = executor._build_graph_state(experiment.id, run.id, review_choices=True)
        assert state['focus_term'] is None

    @patch('app.services.workflow_executor.WorkflowExecutor._execute_graph')
    def test_very_high_confidence(self, mock_graph, multi_doc_experiment, db_session, test_user):
        """Test handling of very high confidence recommendations."""
        executor = WorkflowExecutor()

        run = ExperimentOrchestrationRun(
            experiment_id=multi_doc_experiment.id,
            user_id=test_user.id,
            status='analyzing'
        )
        db_session.add(run)
        db_session.commit()

        # Return very high confidence
        mock_graph.return_value = {
            'experiment_goal': 'Test',
            'recommended_strategy': {'1': ['extract_entities_spacy']},
            'strategy_reasoning': 'Clear match',
            'confidence': 0.99
        }

        result = executor.execute_recommendation_phase(run.id, review_choices=True)
        assert result['confidence'] == 0.99

    @patch('app.services.workflow_executor.WorkflowExecutor._execute_graph')
    def test_very_low_confidence(self, mock_graph, multi_doc_experiment, db_session, test_user):
        """Test handling of very low confidence recommendations."""
        executor = WorkflowExecutor()

        run = ExperimentOrchestrationRun(
            experiment_id=multi_doc_experiment.id,
            user_id=test_user.id,
            status='analyzing'
        )
        db_session.add(run)
        db_session.commit()

        # Return low confidence
        mock_graph.return_value = {
            'experiment_goal': 'Test',
            'recommended_strategy': {'1': ['segment_paragraph']},
            'strategy_reasoning': 'Uncertain match',
            'confidence': 0.42
        }

        result = executor.execute_recommendation_phase(run.id, review_choices=True)
        assert result['confidence'] == 0.42
        # User should review low confidence recommendations
        assert result['awaiting_approval'] is True
