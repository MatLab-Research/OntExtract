"""
Unit Tests for Orchestration Prompts Module

Tests the experiment-type-specific prompt generation for LLM orchestration.

Coverage:
- get_analyze_prompt() for different experiment types
- get_recommend_strategy_prompt() with metadata
- get_synthesis_prompt() including structured card generation
"""

import pytest
from app.orchestration.prompts import (
    get_analyze_prompt,
    get_recommend_strategy_prompt,
    get_synthesis_prompt
)


# ==============================================================================
# Test Data
# ==============================================================================

SAMPLE_DOCUMENTS = [
    {
        'id': 1,
        'title': 'Early AI Research (1960)',
        'content': 'Content about early AI...'
    },
    {
        'id': 2,
        'title': 'Modern Machine Learning (2020)',
        'content': 'Content about modern ML...'
    }
]

SAMPLE_DOCUMENT_METADATA = {
    '1': {
        'title': 'Early AI Research (1960)',
        'authors': 'McCarthy, J.',
        'year': 1960,
        'journal': 'Communications of the ACM',
        'domain': 'Computer Science'
    },
    '2': {
        'title': 'Modern Machine Learning (2020)',
        'authors': 'LeCun, Y.; Bengio, Y.',
        'year': 2020,
        'journal': 'Nature',
        'domain': 'AI/ML'
    }
}

SAMPLE_CONTEXT_ANCHORS = ['person', 'actor', 'entity', 'system', 'autonomous']


# ==============================================================================
# Tests for get_analyze_prompt
# ==============================================================================

def test_analyze_prompt_temporal_evolution():
    """Test analyze prompt for temporal_evolution experiment."""
    prompt = get_analyze_prompt(
        experiment_type='temporal_evolution',
        focus_term='agent',
        focus_term_definition='An entity that acts upon something or someone',
        focus_term_context_anchors=SAMPLE_CONTEXT_ANCHORS,
        focus_term_source='Oxford English Dictionary',
        focus_term_domain='Philosophy',
        documents=SAMPLE_DOCUMENTS,
        document_metadata=SAMPLE_DOCUMENT_METADATA
    )

    # Check that prompt includes key components
    assert 'Focus Term: "agent"' in prompt
    assert 'Baseline Definition' in prompt
    assert 'Oxford English Dictionary' in prompt
    assert 'Context Anchors' in prompt
    assert 'person, actor, entity, system, autonomous' in prompt
    assert 'Domain' in prompt and 'Philosophy' in prompt  # More flexible check
    assert 'Temporal Evolution' in prompt
    assert 'evolved across different time periods' in prompt
    assert 'McCarthy, J.' in prompt  # Document metadata
    assert '1960' in prompt
    assert '2020' in prompt


def test_analyze_prompt_domain_comparison():
    """Test analyze prompt for domain_comparison experiment."""
    prompt = get_analyze_prompt(
        experiment_type='domain_comparison',
        focus_term='agent',
        focus_term_definition='An entity that acts upon something or someone',
        focus_term_context_anchors=SAMPLE_CONTEXT_ANCHORS,
        focus_term_source='Merriam-Webster',
        focus_term_domain=None,
        documents=SAMPLE_DOCUMENTS,
        document_metadata=SAMPLE_DOCUMENT_METADATA
    )

    # Check domain comparison specific content
    assert 'Domain Comparison' in prompt
    assert 'across different research domains' in prompt
    assert 'domain-specific' in prompt
    assert 'Computer Science' in prompt  # Domain from metadata


def test_analyze_prompt_entity_extraction():
    """Test analyze prompt for entity_extraction experiment."""
    prompt = get_analyze_prompt(
        experiment_type='entity_extraction',
        focus_term=None,
        focus_term_definition=None,
        focus_term_context_anchors=None,
        focus_term_source=None,
        focus_term_domain=None,
        documents=SAMPLE_DOCUMENTS,
        document_metadata=None
    )

    # Check entity extraction specific content
    assert 'Entity Extraction' in prompt
    assert 'entities, concepts, and relationships' in prompt


def test_analyze_prompt_without_metadata():
    """Test analyze prompt works without optional metadata."""
    prompt = get_analyze_prompt(
        experiment_type='temporal_evolution',
        focus_term='algorithm',
        focus_term_definition=None,
        focus_term_context_anchors=None,
        focus_term_source=None,
        focus_term_domain=None,
        documents=SAMPLE_DOCUMENTS,
        document_metadata=None
    )

    # Should still include focus term
    assert 'Focus Term: "algorithm"' in prompt
    # But not include sections that require metadata
    assert 'Baseline Definition' not in prompt
    assert 'Context Anchors' not in prompt


# ==============================================================================
# Tests for get_recommend_strategy_prompt
# ==============================================================================

def test_recommend_strategy_prompt_temporal():
    """Test strategy recommendation prompt for temporal experiment."""
    tools = ['extract_entities_spacy', 'extract_temporal', 'semantic_similarity']
    tool_descriptions = {
        'extract_entities_spacy': 'Extract named entities using spaCy',
        'extract_temporal': 'Extract temporal expressions',
        'semantic_similarity': 'Compute semantic similarity'
    }

    prompt = get_recommend_strategy_prompt(
        experiment_type='temporal_evolution',
        experiment_goal='Analyze how "agent" evolved from 1960 to 2020',
        term_context='agent - an autonomous entity',
        focus_term='agent',
        focus_term_definition='An entity that acts',
        focus_term_context_anchors=SAMPLE_CONTEXT_ANCHORS,
        documents=SAMPLE_DOCUMENTS,
        document_metadata=SAMPLE_DOCUMENT_METADATA,
        available_tools=tools,
        tool_descriptions=tool_descriptions
    )

    # Check temporal-specific prioritization
    assert 'temporal_evolution' in prompt
    assert 'extract_temporal' in prompt
    assert 'semantic_similarity' in prompt
    assert 'track meaning evolution over time' in prompt
    assert 'Baseline Meaning' in prompt
    assert 'person, actor, entity, system, autonomous' in prompt


def test_recommend_strategy_prompt_domain():
    """Test strategy recommendation prompt for domain comparison."""
    tools = ['extract_entities_spacy', 'semantic_similarity']
    tool_descriptions = {
        'extract_entities_spacy': 'Extract named entities',
        'semantic_similarity': 'Compute semantic similarity'
    }

    prompt = get_recommend_strategy_prompt(
        experiment_type='domain_comparison',
        experiment_goal='Compare usage across Computer Science and Philosophy',
        term_context='agent',
        focus_term='agent',
        focus_term_definition='An entity that acts',
        focus_term_context_anchors=SAMPLE_CONTEXT_ANCHORS,
        documents=SAMPLE_DOCUMENTS,
        document_metadata=SAMPLE_DOCUMENT_METADATA,
        available_tools=tools,
        tool_descriptions=tool_descriptions
    )

    # Check domain-specific content
    assert 'domain_comparison' in prompt
    assert 'usage patterns across fields' in prompt


# ==============================================================================
# Tests for get_synthesis_prompt
# ==============================================================================

def test_synthesis_prompt_temporal_with_card_generation():
    """Test synthesis prompt for temporal evolution includes card generation."""
    processing_results = {
        '1': {
            'extract_temporal': {'dates': ['1960'], 'count': 1},
            'extract_entities_spacy': {'entities': [{'text': 'McCarthy', 'label': 'PERSON'}]}
        },
        '2': {
            'extract_temporal': {'dates': ['2020'], 'count': 1},
            'extract_entities_spacy': {'entities': [{'text': 'LeCun', 'label': 'PERSON'}]}
        }
    }

    prompt = get_synthesis_prompt(
        experiment_type='temporal_evolution',
        experiment_goal='Analyze temporal evolution of "agent"',
        focus_term='agent',
        focus_term_definition='An entity that acts',
        focus_term_context_anchors=SAMPLE_CONTEXT_ANCHORS,
        processing_results=processing_results,
        document_metadata=SAMPLE_DOCUMENT_METADATA
    )

    # Check temporal synthesis content
    assert 'Temporal Evolution Analysis' in prompt
    assert 'evolved across time periods' in prompt
    assert 'Semantic Drift' in prompt
    assert 'Context Anchor Tracking' in prompt

    # IMPORTANT: Check for structured card generation request
    assert 'generated_term_cards' in prompt
    assert 'period_label' in prompt
    assert 'frequency' in prompt
    assert 'context_changes' in prompt
    assert 'narrative' in prompt


def test_synthesis_prompt_domain_comparison():
    """Test synthesis prompt for domain comparison."""
    processing_results = {
        '1': {'extract_entities_spacy': {'entities': [{'text': 'algorithm', 'label': 'CONCEPT'}]}},
        '2': {'extract_entities_spacy': {'entities': [{'text': 'neural network', 'label': 'CONCEPT'}]}}
    }

    prompt = get_synthesis_prompt(
        experiment_type='domain_comparison',
        experiment_goal='Compare "agent" across disciplines',
        focus_term='agent',
        focus_term_definition='An entity that acts',
        focus_term_context_anchors=SAMPLE_CONTEXT_ANCHORS,
        processing_results=processing_results,
        document_metadata=SAMPLE_DOCUMENT_METADATA
    )

    # Check domain comparison content
    assert 'Domain Comparison Analysis' in prompt
    assert 'across different research domains' in prompt
    assert 'Domain-Specific Meanings' in prompt
    assert 'Universal vs. Specialized Anchors' in prompt


def test_synthesis_prompt_entity_extraction():
    """Test synthesis prompt for entity extraction."""
    processing_results = {
        '1': {'extract_entities_spacy': {'entities': [{'text': 'AI', 'label': 'ORG'}]}},
        '2': {'llm_extract_concepts': {'concepts': ['machine learning', 'deep learning']}}
    }

    prompt = get_synthesis_prompt(
        experiment_type='entity_extraction',
        experiment_goal='Extract key entities and concepts',
        focus_term=None,
        focus_term_definition=None,
        focus_term_context_anchors=None,
        processing_results=processing_results,
        document_metadata=None
    )

    # Check entity extraction content
    assert 'Entity Analysis' in prompt
    assert 'Common entities, patterns, and relationships' in prompt


def test_synthesis_prompt_includes_metadata():
    """Test that synthesis prompt includes document metadata."""
    processing_results = {'1': {}, '2': {}}

    prompt = get_synthesis_prompt(
        experiment_type='temporal_evolution',
        experiment_goal='Test',
        focus_term='test',
        focus_term_definition='Test definition',
        focus_term_context_anchors=['test'],
        processing_results=processing_results,
        document_metadata=SAMPLE_DOCUMENT_METADATA
    )

    # Metadata should be in processing results
    assert 'McCarthy, J.' in prompt
    assert '1960' in prompt
    assert 'Communications of the ACM' in prompt


# ==============================================================================
# Integration Tests
# ==============================================================================

def test_prompt_chain_consistency():
    """Test that all three prompts can be generated for the same experiment."""
    experiment_type = 'temporal_evolution'
    focus_term = 'agent'
    definition = 'An entity that acts'
    anchors = SAMPLE_CONTEXT_ANCHORS

    # Stage 1: Analyze
    analyze_prompt = get_analyze_prompt(
        experiment_type=experiment_type,
        focus_term=focus_term,
        focus_term_definition=definition,
        focus_term_context_anchors=anchors,
        focus_term_source='OED',
        focus_term_domain='Philosophy',
        documents=SAMPLE_DOCUMENTS,
        document_metadata=SAMPLE_DOCUMENT_METADATA
    )
    assert len(analyze_prompt) > 0

    # Stage 2: Recommend
    recommend_prompt = get_recommend_strategy_prompt(
        experiment_type=experiment_type,
        experiment_goal='Analyze temporal evolution',
        term_context='agent context',
        focus_term=focus_term,
        focus_term_definition=definition,
        focus_term_context_anchors=anchors,
        documents=SAMPLE_DOCUMENTS,
        document_metadata=SAMPLE_DOCUMENT_METADATA,
        available_tools=['extract_temporal', 'semantic_similarity'],
        tool_descriptions={'extract_temporal': 'Extract dates', 'semantic_similarity': 'Compare semantics'}
    )
    assert len(recommend_prompt) > 0

    # Stage 5: Synthesize
    synthesis_prompt = get_synthesis_prompt(
        experiment_type=experiment_type,
        experiment_goal='Analyze temporal evolution',
        focus_term=focus_term,
        focus_term_definition=definition,
        focus_term_context_anchors=anchors,
        processing_results={'1': {}, '2': {}},
        document_metadata=SAMPLE_DOCUMENT_METADATA
    )
    assert len(synthesis_prompt) > 0


def test_all_experiment_types_supported():
    """Test that all experiment types generate valid prompts."""
    experiment_types = ['temporal_evolution', 'domain_comparison', 'entity_extraction']

    for exp_type in experiment_types:
        # Analyze prompt
        prompt = get_analyze_prompt(
            experiment_type=exp_type,
            focus_term='test',
            focus_term_definition='test def',
            focus_term_context_anchors=['test'],
            focus_term_source='test',
            focus_term_domain='test',
            documents=SAMPLE_DOCUMENTS,
            document_metadata=None
        )
        assert len(prompt) > 0
        assert exp_type.replace('_', ' ').title() in prompt or 'Entity Extraction' in prompt

        # Recommend prompt
        prompt = get_recommend_strategy_prompt(
            experiment_type=exp_type,
            experiment_goal='Test goal',
            term_context='test',
            focus_term='test',
            focus_term_definition='test',
            focus_term_context_anchors=['test'],
            documents=SAMPLE_DOCUMENTS,
            document_metadata=None,
            available_tools=['tool1'],
            tool_descriptions={'tool1': 'desc'}
        )
        assert len(prompt) > 0

        # Synthesis prompt
        prompt = get_synthesis_prompt(
            experiment_type=exp_type,
            experiment_goal='Test goal',
            focus_term='test',
            focus_term_definition='test',
            focus_term_context_anchors=['test'],
            processing_results={'1': {}},
            document_metadata=None
        )
        assert len(prompt) > 0
