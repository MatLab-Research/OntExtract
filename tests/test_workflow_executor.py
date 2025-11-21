"""
Unit Tests for WorkflowExecutor Service

Tests the core WorkflowExecutor service that manages LangGraph execution
for the LLM Analyze feature.

Coverage:
- State building methods (_build_graph_state, _build_processing_state)
- Execution methods (execute_recommendation_phase, execute_processing_phase)
- Error handling and recovery
- State management and merging
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from uuid import uuid4

from app.services.workflow_executor import WorkflowExecutor, get_workflow_executor
from app.models import Experiment, Document
from app.models.experiment_orchestration_run import ExperimentOrchestrationRun


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
def workflow_executor():
    """Create a WorkflowExecutor instance for testing."""
    return WorkflowExecutor()


@pytest.fixture
def sample_experiment_with_documents(db_session, test_user):
    """Create an experiment with multiple documents for testing."""
    # Create experiment
    experiment = Experiment(
        name='Test Orchestration Experiment',
        description='Test experiment for workflow executor',
        experiment_type='temporal_evolution',
        user_id=test_user.id,
        status='draft',
        configuration='{"target_terms": ["algorithm"], "periods": ["1980-1990", "1990-2000"]}'
    )
    db_session.add(experiment)
    db_session.flush()

    # Create documents
    for i in range(3):
        doc = Document(
            title=f'Test Document {i+1}',
            content=f'This is test content for document {i+1}. ' * 50,
            original_filename=f'test_doc_{i+1}.txt',
            document_type='document',
            content_type='text/plain',
            status='completed',
            user_id=test_user.id,
            experiment_id=experiment.id,
            word_count=200
        )
        db_session.add(doc)

    db_session.commit()
    return experiment


@pytest.fixture
def orchestration_run(db_session, sample_experiment_with_documents, test_user):
    """Create an orchestration run for testing."""
    run = ExperimentOrchestrationRun(
        experiment_id=sample_experiment_with_documents.id,
        user_id=test_user.id,
        status='analyzing',
        current_stage='analyzing'
    )
    db_session.add(run)
    db_session.commit()
    return run


@pytest.fixture
def completed_recommendation_run(db_session, sample_experiment_with_documents, test_user):
    """Create an orchestration run with completed recommendation phase."""
    docs = Document.query.filter_by(experiment_id=sample_experiment_with_documents.id).all()

    run = ExperimentOrchestrationRun(
        experiment_id=sample_experiment_with_documents.id,
        user_id=test_user.id,
        status='reviewing',
        current_stage='reviewing',
        experiment_goal='Analyze temporal evolution of the term "algorithm"',
        term_context='algorithm',
        recommended_strategy={
            str(docs[0].id): ['extract_entities_spacy', 'extract_temporal'],
            str(docs[1].id): ['extract_entities_spacy'],
            str(docs[2].id): ['segment_paragraph', 'extract_entities_spacy']
        },
        strategy_reasoning='Documents contain historical content requiring entity and temporal extraction.',
        confidence=0.87
    )
    db_session.add(run)
    db_session.commit()
    return run


# ==============================================================================
# Unit Tests - State Building
# ==============================================================================

class TestBuildGraphState:
    """Test _build_graph_state method."""

    def test_build_graph_state_creates_valid_state(
        self,
        workflow_executor,
        sample_experiment_with_documents,
        orchestration_run
    ):
        """Test that _build_graph_state creates a valid state dictionary."""
        state = workflow_executor._build_graph_state(
            experiment_id=sample_experiment_with_documents.id,
            run_id=orchestration_run.id,
            review_choices=True
        )

        # Verify basic structure
        assert 'run_id' in state
        assert 'experiment_id' in state
        assert 'documents' in state
        assert 'focus_term' in state
        assert 'user_preferences' in state

        # Verify types
        assert state['run_id'] == str(orchestration_run.id)
        assert state['experiment_id'] == sample_experiment_with_documents.id
        assert isinstance(state['documents'], list)
        assert len(state['documents']) == 3

        # Verify user preferences
        assert state['user_preferences']['review_choices'] is True

        # Verify progressive fields are initialized to None
        assert state['experiment_goal'] is None
        assert state['recommended_strategy'] is None
        assert state['confidence'] is None

    def test_build_graph_state_extracts_focus_term(
        self,
        workflow_executor,
        sample_experiment_with_documents,
        orchestration_run
    ):
        """Test that focus term is extracted from temporal_evolution experiments."""
        state = workflow_executor._build_graph_state(
            experiment_id=sample_experiment_with_documents.id,
            run_id=orchestration_run.id,
            review_choices=True
        )

        assert state['focus_term'] == 'algorithm'

    def test_build_graph_state_document_structure(
        self,
        workflow_executor,
        sample_experiment_with_documents,
        orchestration_run
    ):
        """Test that documents are properly structured in state."""
        state = workflow_executor._build_graph_state(
            experiment_id=sample_experiment_with_documents.id,
            run_id=orchestration_run.id,
            review_choices=True
        )

        # Check first document structure
        doc = state['documents'][0]
        assert 'id' in doc
        assert 'uuid' in doc
        assert 'title' in doc
        assert 'content' in doc
        assert 'metadata' in doc

        # Check metadata structure
        assert 'filename' in doc['metadata']
        assert 'created_at' in doc['metadata']
        assert 'document_type' in doc['metadata']
        assert 'word_count' in doc['metadata']

    def test_build_graph_state_invalid_experiment(
        self,
        workflow_executor,
        orchestration_run
    ):
        """Test that invalid experiment ID raises ValueError."""
        with pytest.raises(ValueError, match='Experiment .* not found'):
            workflow_executor._build_graph_state(
                experiment_id=99999,
                run_id=orchestration_run.id,
                review_choices=True
            )

    def test_build_graph_state_no_review(
        self,
        workflow_executor,
        sample_experiment_with_documents,
        orchestration_run
    ):
        """Test state building with review_choices=False."""
        state = workflow_executor._build_graph_state(
            experiment_id=sample_experiment_with_documents.id,
            run_id=orchestration_run.id,
            review_choices=False
        )

        assert state['user_preferences']['review_choices'] is False


class TestBuildProcessingState:
    """Test _build_processing_state method."""

    def test_build_processing_state_creates_valid_state(
        self,
        workflow_executor,
        completed_recommendation_run
    ):
        """Test that _build_processing_state creates valid state from run."""
        state = workflow_executor._build_processing_state(completed_recommendation_run)

        # Verify basic structure
        assert state['run_id'] == str(completed_recommendation_run.id)
        assert state['experiment_id'] == completed_recommendation_run.experiment_id
        assert isinstance(state['documents'], list)

        # Verify recommendation phase data is preserved
        assert state['experiment_goal'] == completed_recommendation_run.experiment_goal
        assert state['recommended_strategy'] == completed_recommendation_run.recommended_strategy
        assert state['strategy_reasoning'] == completed_recommendation_run.strategy_reasoning
        assert state['confidence'] == completed_recommendation_run.confidence

        # Verify processing fields are initialized to None
        assert state['processing_results'] is None
        assert state['execution_trace'] is None
        assert state['cross_document_insights'] is None

        # Verify stage and approval
        assert state['current_stage'] == 'executing'
        assert state['strategy_approved'] is True
        assert state['user_preferences']['review_choices'] is False

    def test_build_processing_state_with_modified_strategy(
        self,
        workflow_executor,
        completed_recommendation_run,
        db_session
    ):
        """Test state building with user-modified strategy."""
        # Add modified strategy
        modified_strategy = {
            str(completed_recommendation_run.experiment.documents[0].id): ['extract_entities_spacy', 'extract_temporal', 'extract_definitions']
        }
        completed_recommendation_run.modified_strategy = modified_strategy
        db_session.commit()

        state = workflow_executor._build_processing_state(completed_recommendation_run)

        assert state['modified_strategy'] == modified_strategy


# ==============================================================================
# Unit Tests - Execution Methods
# ==============================================================================

class TestExecuteRecommendationPhase:
    """Test execute_recommendation_phase method."""

    @patch('app.services.workflow_executor.WorkflowExecutor._execute_graph')
    def test_execute_recommendation_phase_success(
        self,
        mock_execute_graph,
        workflow_executor,
        orchestration_run,
        db_session
    ):
        """Test successful execution of recommendation phase."""
        # Mock graph execution
        mock_execute_graph.return_value = {
            'experiment_goal': 'Analyze temporal evolution of algorithm',
            'term_context': 'algorithm',
            'recommended_strategy': {
                '1': ['extract_entities_spacy', 'extract_temporal']
            },
            'strategy_reasoning': 'Documents require entity and temporal analysis.',
            'confidence': 0.92,
            'strategy_approved': False
        }

        result = workflow_executor.execute_recommendation_phase(
            run_id=orchestration_run.id,
            review_choices=True
        )

        # Verify result structure
        assert result['status'] == 'reviewing'
        assert result['run_id'] == str(orchestration_run.id)
        assert result['experiment_goal'] == 'Analyze temporal evolution of algorithm'
        assert result['confidence'] == 0.92
        assert result['awaiting_approval'] is True

        # Verify database update
        db_session.refresh(orchestration_run)
        assert orchestration_run.status == 'reviewing'
        assert orchestration_run.experiment_goal == 'Analyze temporal evolution of algorithm'
        assert orchestration_run.recommended_strategy == {'1': ['extract_entities_spacy', 'extract_temporal']}

    @patch('app.services.workflow_executor.WorkflowExecutor._execute_graph')
    def test_execute_recommendation_phase_no_review(
        self,
        mock_execute_graph,
        workflow_executor,
        orchestration_run,
        db_session
    ):
        """Test execution with review_choices=False."""
        mock_execute_graph.return_value = {
            'experiment_goal': 'Test goal',
            'term_context': 'test',
            'recommended_strategy': {},
            'strategy_reasoning': 'Test reasoning',
            'confidence': 0.85,
            'strategy_approved': True
        }

        result = workflow_executor.execute_recommendation_phase(
            run_id=orchestration_run.id,
            review_choices=False
        )

        assert result['status'] == 'executing'
        assert result['awaiting_approval'] is False

        db_session.refresh(orchestration_run)
        assert orchestration_run.status == 'executing'

    def test_execute_recommendation_phase_invalid_run(
        self,
        workflow_executor
    ):
        """Test execution with invalid run_id."""
        fake_run_id = uuid4()

        with pytest.raises(RuntimeError, match='Recommendation phase failed'):
            workflow_executor.execute_recommendation_phase(
                run_id=fake_run_id,
                review_choices=True
            )

    @patch('app.services.workflow_executor.WorkflowExecutor._execute_graph')
    def test_execute_recommendation_phase_graph_error(
        self,
        mock_execute_graph,
        workflow_executor,
        orchestration_run,
        db_session
    ):
        """Test error handling when graph execution fails."""
        mock_execute_graph.side_effect = Exception('LLM API error')

        with pytest.raises(RuntimeError, match='Recommendation phase failed'):
            workflow_executor.execute_recommendation_phase(
                run_id=orchestration_run.id,
                review_choices=True
            )

        # Verify run is marked as failed
        db_session.refresh(orchestration_run)
        assert orchestration_run.status == 'failed'
        assert 'LLM API error' in orchestration_run.error_message


class TestExecuteProcessingPhase:
    """Test execute_processing_phase method."""

    @patch('app.services.workflow_executor.WorkflowExecutor._execute_processing')
    def test_execute_processing_phase_success(
        self,
        mock_execute_processing,
        workflow_executor,
        completed_recommendation_run,
        db_session
    ):
        """Test successful execution of processing phase."""
        # Mock processing execution
        mock_execute_processing.return_value = {
            'processing_results': {
                '1': {
                    'extract_entities_spacy': {'count': 15},
                    'extract_temporal': {'count': 3}
                }
            },
            'execution_trace': [
                {'node': 'execute_strategy', 'timestamp': datetime.utcnow().isoformat()}
            ],
            'cross_document_insights': 'The term "algorithm" shows increasing formalization.',
            'term_evolution_analysis': 'Semantic shift from informal to formal usage.',
            'comparative_summary': 'Analysis complete.'
        }

        result = workflow_executor.execute_processing_phase(
            run_id=completed_recommendation_run.id,
            modified_strategy=None,
            review_notes='Looks good',
            reviewer_id=1
        )

        # Verify result
        assert result['status'] == 'completed'
        assert result['run_id'] == str(completed_recommendation_run.id)
        assert 'processing_results' in result
        assert 'cross_document_insights' in result
        assert 'execution_time' in result

        # Verify database update
        db_session.refresh(completed_recommendation_run)
        assert completed_recommendation_run.status == 'completed'
        assert completed_recommendation_run.processing_results is not None
        assert completed_recommendation_run.cross_document_insights is not None
        assert completed_recommendation_run.completed_at is not None
        assert completed_recommendation_run.review_notes == 'Looks good'
        assert completed_recommendation_run.reviewed_by == 1

    @patch('app.services.workflow_executor.WorkflowExecutor._execute_processing')
    def test_execute_processing_phase_with_modified_strategy(
        self,
        mock_execute_processing,
        workflow_executor,
        completed_recommendation_run,
        db_session
    ):
        """Test execution with user-modified strategy."""
        modified_strategy = {
            '1': ['extract_entities_spacy', 'extract_temporal', 'extract_definitions']
        }

        mock_execute_processing.return_value = {
            'processing_results': {},
            'execution_trace': [],
            'cross_document_insights': 'Test insights',
            'term_evolution_analysis': None,
            'comparative_summary': None
        }

        result = workflow_executor.execute_processing_phase(
            run_id=completed_recommendation_run.id,
            modified_strategy=modified_strategy,
            review_notes='Added definitions extraction',
            reviewer_id=1
        )

        # Verify modified strategy saved
        db_session.refresh(completed_recommendation_run)
        assert completed_recommendation_run.modified_strategy == modified_strategy

    def test_execute_processing_phase_invalid_run(
        self,
        workflow_executor
    ):
        """Test execution with invalid run_id."""
        fake_run_id = uuid4()

        with pytest.raises(RuntimeError, match='Processing phase failed'):
            workflow_executor.execute_processing_phase(
                run_id=fake_run_id
            )

    @patch('app.services.workflow_executor.WorkflowExecutor._execute_processing')
    def test_execute_processing_phase_execution_error(
        self,
        mock_execute_processing,
        workflow_executor,
        completed_recommendation_run,
        db_session
    ):
        """Test error handling when processing fails."""
        mock_execute_processing.side_effect = Exception('Tool execution failed')

        with pytest.raises(RuntimeError, match='Processing phase failed'):
            workflow_executor.execute_processing_phase(
                run_id=completed_recommendation_run.id
            )

        # Verify run is marked as failed
        db_session.refresh(completed_recommendation_run)
        assert completed_recommendation_run.status == 'failed'
        assert 'Tool execution failed' in completed_recommendation_run.error_message


# ==============================================================================
# Unit Tests - Singleton Pattern
# ==============================================================================

class TestWorkflowExecutorSingleton:
    """Test the singleton pattern for WorkflowExecutor."""

    def test_get_workflow_executor_returns_singleton(self):
        """Test that get_workflow_executor returns the same instance."""
        executor1 = get_workflow_executor()
        executor2 = get_workflow_executor()

        assert executor1 is executor2

    def test_workflow_executor_has_graph(self):
        """Test that executor is initialized with graph."""
        executor = get_workflow_executor()

        assert executor.graph is not None


# ==============================================================================
# Integration-like Tests (with mocked LLM)
# ==============================================================================

@pytest.mark.integration
class TestWorkflowExecutorIntegration:
    """Integration tests with mocked LLM calls."""

    @patch('app.services.workflow_executor.WorkflowExecutor._execute_graph')
    @patch('app.services.workflow_executor.WorkflowExecutor._execute_processing')
    def test_full_workflow_execution(
        self,
        mock_execute_processing,
        mock_execute_graph,
        workflow_executor,
        sample_experiment_with_documents,
        test_user,
        db_session
    ):
        """Test full workflow from start to finish."""
        # Create orchestration run
        run = ExperimentOrchestrationRun(
            experiment_id=sample_experiment_with_documents.id,
            user_id=test_user.id,
            status='analyzing',
            current_stage='analyzing'
        )
        db_session.add(run)
        db_session.commit()

        # Mock Stage 1-2: Recommendation
        mock_execute_graph.return_value = {
            'experiment_goal': 'Analyze temporal evolution of algorithm',
            'term_context': 'algorithm',
            'recommended_strategy': {
                str(sample_experiment_with_documents.documents[0].id): ['extract_entities_spacy']
            },
            'strategy_reasoning': 'Test reasoning',
            'confidence': 0.88,
            'strategy_approved': False
        }

        # Execute recommendation phase
        rec_result = workflow_executor.execute_recommendation_phase(
            run_id=run.id,
            review_choices=True
        )

        assert rec_result['status'] == 'reviewing'

        # Mock Stage 4-5: Processing
        mock_execute_processing.return_value = {
            'processing_results': {'1': {'extract_entities_spacy': {'count': 10}}},
            'execution_trace': [],
            'cross_document_insights': 'Test insights',
            'term_evolution_analysis': 'Test evolution',
            'comparative_summary': 'Test summary'
        }

        # Execute processing phase
        proc_result = workflow_executor.execute_processing_phase(
            run_id=run.id,
            reviewer_id=test_user.id
        )

        assert proc_result['status'] == 'completed'

        # Verify final state
        db_session.refresh(run)
        assert run.status == 'completed'
        assert run.experiment_goal is not None
        assert run.recommended_strategy is not None
        assert run.processing_results is not None
        assert run.cross_document_insights is not None
        assert run.completed_at is not None
