"""
Unit Tests for Enhanced Orchestration State Schema

Tests the updated ExperimentOrchestrationState with metadata fields
and structured card outputs.

Coverage:
- State creation with new metadata fields
- State field validation
- Database model for structured card fields
"""

import pytest
from app.orchestration.experiment_state import (
    ExperimentOrchestrationState,
    create_initial_experiment_state
)
from app.models.experiment_orchestration_run import ExperimentOrchestrationRun
from app import db


# ==============================================================================
# Test Data
# ==============================================================================

SAMPLE_DOCUMENTS = [
    {'id': 1, 'title': 'Doc 1', 'content': 'Content 1'},
    {'id': 2, 'title': 'Doc 2', 'content': 'Content 2'}
]

SAMPLE_CONTEXT_ANCHORS = ['person', 'actor', 'entity', 'system']

SAMPLE_DOCUMENT_METADATA = {
    '1': {
        'title': 'Early AI Research',
        'authors': 'McCarthy, J.',
        'year': 1960,
        'journal': 'CACM',
        'domain': 'Computer Science'
    },
    '2': {
        'title': 'Modern ML',
        'authors': 'LeCun, Y.',
        'year': 2020,
        'journal': 'Nature',
        'domain': 'AI/ML'
    }
}


# ==============================================================================
# Tests for State Creation
# ==============================================================================

def test_create_initial_state_with_minimal_fields():
    """Test creating state with only required fields."""
    state = create_initial_experiment_state(
        experiment_id=1,
        run_id='test-uuid',
        documents=SAMPLE_DOCUMENTS
    )

    # Check required fields
    assert state['experiment_id'] == 1
    assert state['run_id'] == 'test-uuid'
    assert state['documents'] == SAMPLE_DOCUMENTS
    assert state['current_stage'] == 'analyzing'

    # Check optional metadata fields default to None
    assert state['experiment_type'] is None
    assert state['focus_term_definition'] is None
    assert state['focus_term_context_anchors'] is None
    assert state['focus_term_source'] is None
    assert state['focus_term_domain'] is None
    assert state['document_metadata'] is None

    # Check structured output fields default to None
    assert state['generated_term_cards'] is None
    assert state['generated_domain_cards'] is None
    assert state['generated_entity_cards'] is None


def test_create_initial_state_with_full_metadata():
    """Test creating state with all metadata fields populated."""
    state = create_initial_experiment_state(
        experiment_id=1,
        run_id='test-uuid',
        documents=SAMPLE_DOCUMENTS,
        focus_term='agent',
        user_preferences={'review_choices': True},
        experiment_type='temporal_evolution',
        focus_term_definition='An entity that acts',
        focus_term_context_anchors=SAMPLE_CONTEXT_ANCHORS,
        focus_term_source='Oxford English Dictionary',
        focus_term_domain='Philosophy',
        document_metadata=SAMPLE_DOCUMENT_METADATA
    )

    # Check all metadata fields
    assert state['experiment_type'] == 'temporal_evolution'
    assert state['focus_term'] == 'agent'
    assert state['focus_term_definition'] == 'An entity that acts'
    assert state['focus_term_context_anchors'] == SAMPLE_CONTEXT_ANCHORS
    assert state['focus_term_source'] == 'Oxford English Dictionary'
    assert state['focus_term_domain'] == 'Philosophy'
    assert state['document_metadata'] == SAMPLE_DOCUMENT_METADATA


def test_state_preserves_all_stage_fields():
    """Test that all workflow stage fields are present in state."""
    state = create_initial_experiment_state(
        experiment_id=1,
        run_id='test-uuid',
        documents=SAMPLE_DOCUMENTS
    )

    # Stage 1 fields
    assert 'experiment_goal' in state
    assert 'term_context' in state

    # Stage 2 fields
    assert 'recommended_strategy' in state
    assert 'strategy_reasoning' in state
    assert 'confidence' in state

    # Stage 3 fields
    assert 'strategy_approved' in state
    assert 'modified_strategy' in state
    assert 'review_notes' in state

    # Stage 4 fields
    assert 'processing_results' in state
    assert 'execution_trace' in state

    # Stage 5 fields
    assert 'cross_document_insights' in state
    assert 'term_evolution_analysis' in state
    assert 'comparative_summary' in state

    # Structured output fields
    assert 'generated_term_cards' in state
    assert 'generated_domain_cards' in state
    assert 'generated_entity_cards' in state


# ==============================================================================
# Tests for Database Model
# ==============================================================================

def test_orchestration_run_model_has_card_fields(db_session, test_user, temporal_experiment):
    """Test that ExperimentOrchestrationRun model has new card fields."""
    run = ExperimentOrchestrationRun(
        experiment_id=temporal_experiment.id,
        user_id=test_user.id,
        status='completed',
        current_stage='completed'
    )

    # Set structured card data
    run.generated_term_cards = [
        {
            'term': 'agent',
            'period_label': '1960-1980',
            'definition': 'An autonomous program',
            'frequency': 0.3,
            'context_changes': ['program', 'autonomous'],
            'narrative': 'Early usage focused on automation'
        }
    ]

    run.generated_domain_cards = [
        {
            'domain': 'Computer Science',
            'definition': 'Software agent',
            'key_features': ['autonomous', 'reactive']
        }
    ]

    run.generated_entity_cards = [
        {
            'entity': 'McCarthy',
            'type': 'PERSON',
            'relations': ['founded', 'AI']
        }
    ]

    db_session.add(run)
    db_session.commit()

    # Retrieve and verify
    retrieved = ExperimentOrchestrationRun.query.get(run.id)
    assert retrieved.generated_term_cards is not None
    assert len(retrieved.generated_term_cards) == 1
    assert retrieved.generated_term_cards[0]['term'] == 'agent'
    assert retrieved.generated_term_cards[0]['period_label'] == '1960-1980'

    assert retrieved.generated_domain_cards is not None
    assert len(retrieved.generated_domain_cards) == 1
    assert retrieved.generated_domain_cards[0]['domain'] == 'Computer Science'

    assert retrieved.generated_entity_cards is not None
    assert len(retrieved.generated_entity_cards) == 1
    assert retrieved.generated_entity_cards[0]['entity'] == 'McCarthy'


def test_orchestration_run_to_dict_includes_card_fields(db_session, test_user, temporal_experiment):
    """Test that to_dict() includes structured card fields."""
    run = ExperimentOrchestrationRun(
        experiment_id=temporal_experiment.id,
        user_id=test_user.id,
        status='completed',
        generated_term_cards=[{'test': 'data'}],
        generated_domain_cards=[{'domain': 'test'}],
        generated_entity_cards=[{'entity': 'test'}]
    )
    db_session.add(run)
    db_session.commit()

    run_dict = run.to_dict()

    assert 'generated_term_cards' in run_dict
    assert 'generated_domain_cards' in run_dict
    assert 'generated_entity_cards' in run_dict
    assert run_dict['generated_term_cards'] == [{'test': 'data'}]
    assert run_dict['generated_domain_cards'] == [{'domain': 'test'}]
    assert run_dict['generated_entity_cards'] == [{'entity': 'test'}]


def test_orchestration_run_card_fields_nullable(db_session, test_user, temporal_experiment):
    """Test that card fields are nullable (can be None)."""
    run = ExperimentOrchestrationRun(
        experiment_id=temporal_experiment.id,
        user_id=test_user.id,
        status='analyzing'
    )
    db_session.add(run)
    db_session.commit()

    # Should be able to create without card fields
    retrieved = ExperimentOrchestrationRun.query.get(run.id)
    assert retrieved.generated_term_cards is None
    assert retrieved.generated_domain_cards is None
    assert retrieved.generated_entity_cards is None


# ==============================================================================
# Integration Tests
# ==============================================================================

def test_state_to_database_round_trip(db_session, test_user, temporal_experiment):
    """Test creating state, saving to DB, and loading back."""
    # Create state
    state = create_initial_experiment_state(
        experiment_id=temporal_experiment.id,
        run_id='test-uuid',
        documents=SAMPLE_DOCUMENTS,
        experiment_type='temporal_evolution',
        focus_term='agent',
        focus_term_definition='An entity that acts',
        focus_term_context_anchors=SAMPLE_CONTEXT_ANCHORS,
        focus_term_source='OED',
        focus_term_domain='Philosophy',
        document_metadata=SAMPLE_DOCUMENT_METADATA
    )

    # Simulate workflow completion - save to database
    run = ExperimentOrchestrationRun(
        experiment_id=temporal_experiment.id,
        user_id=test_user.id,
        status='completed',
        experiment_goal='Test goal',
        term_context='agent',
        cross_document_insights='Test insights',
        generated_term_cards=[
            {
                'term': 'agent',
                'period_label': '1960-1980',
                'definition': 'Early usage',
                'frequency': 0.3,
                'context_changes': ['program', 'autonomous'],
                'narrative': 'Focus on automation'
            }
        ]
    )
    db_session.add(run)
    db_session.commit()

    # Load back from database
    retrieved = ExperimentOrchestrationRun.query.get(run.id)

    # Verify round trip
    assert retrieved.experiment_id == temporal_experiment.id
    assert retrieved.experiment_goal == 'Test goal'
    assert retrieved.term_context == 'agent'
    assert retrieved.generated_term_cards is not None
    assert len(retrieved.generated_term_cards) == 1
    assert retrieved.generated_term_cards[0]['term'] == 'agent'
    assert retrieved.generated_term_cards[0]['frequency'] == 0.3


def test_multiple_experiment_types(db_session, test_user, temporal_experiment):
    """Test that different experiment types can use appropriate card fields."""
    # Temporal evolution - uses generated_term_cards
    temporal_run = ExperimentOrchestrationRun(
        experiment_id=temporal_experiment.id,
        user_id=test_user.id,
        status='completed',
        generated_term_cards=[{'period': '1960-1980'}]
    )
    db_session.add(temporal_run)

    # Domain comparison - uses generated_domain_cards
    domain_run = ExperimentOrchestrationRun(
        experiment_id=temporal_experiment.id,
        user_id=test_user.id,
        status='completed',
        generated_domain_cards=[{'domain': 'CS'}]
    )
    db_session.add(domain_run)

    # Entity extraction - uses generated_entity_cards
    entity_run = ExperimentOrchestrationRun(
        experiment_id=temporal_experiment.id,
        user_id=test_user.id,
        status='completed',
        generated_entity_cards=[{'entity': 'McCarthy'}]
    )
    db_session.add(entity_run)

    db_session.commit()

    # Verify all three types can coexist
    assert ExperimentOrchestrationRun.query.filter_by(
        experiment_id=temporal_experiment.id
    ).count() == 3
