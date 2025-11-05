"""
State management for experiment-level orchestration.

This module defines the state schema for multi-document experiment processing,
where an LLM recommends a processing strategy across all documents to achieve
the experiment's goals (especially semantic evolution tracking).
"""

from typing import TypedDict, List, Dict, Any, Optional, Annotated
import operator


class ExperimentOrchestrationState(TypedDict):
    """
    State for experiment-level orchestration workflow.

    Stages:
    1. Analyze Experiment - Understand goals and focus term
    2. Recommend Strategy - Suggest tools per document
    3. Human Review - Optional review/modification
    4. Execute Strategy - Process all documents
    5. Synthesize Experiment - Cross-document insights
    """

    # Input (set at initialization)
    experiment_id: str
    focus_term: Optional[str]
    documents: List[Dict[str, Any]]  # [{id, title, content, metadata}, ...]
    user_preferences: Dict[str, Any]  # {review_choices: bool, ...}
    run_id: str  # UUID for this orchestration run

    # Stage 1: Experiment Understanding
    experiment_goal: str  # LLM's understanding of experiment purpose
    term_context: Optional[str]  # Why focus term matters (if present)

    # Stage 2: Strategy Recommendation
    recommended_strategy: Dict[str, List[str]]  # {doc_id: [tool1, tool2, ...]}
    strategy_reasoning: str  # Why LLM chose this approach
    confidence: float  # LLM confidence in strategy (0.0-1.0)

    # Stage 3: Human Review (optional, based on review_choices)
    strategy_approved: bool  # Whether strategy was approved (auto or manual)
    modified_strategy: Optional[Dict[str, List[str]]]  # User modifications
    review_notes: Optional[str]  # User feedback on strategy

    # Stage 4: Execution
    processing_results: Dict[str, Any]  # {doc_id: {tool: result, ...}}
    execution_trace: Annotated[List[Dict[str, Any]], operator.add]  # Provenance trail

    # Stage 5: Synthesis
    cross_document_insights: str  # Insights from analyzing all docs together
    term_evolution_analysis: Optional[str]  # Focus term semantic evolution (if applicable)
    comparative_summary: str  # High-level summary

    # Status tracking
    current_stage: str  # analyzing, recommending, reviewing, executing, synthesizing, completed
    error_message: Optional[str]  # Error details if workflow fails


def create_initial_experiment_state(
    experiment_id: str,
    run_id: str,
    documents: List[Dict[str, Any]],
    focus_term: Optional[str] = None,
    user_preferences: Optional[Dict[str, Any]] = None
) -> ExperimentOrchestrationState:
    """
    Create initial state for experiment orchestration.

    Args:
        experiment_id: UUID of experiment
        run_id: UUID for this orchestration run
        documents: List of document dicts with id, title, content, metadata
        focus_term: Optional term to focus on for semantic evolution
        user_preferences: User settings (e.g., review_choices)

    Returns:
        Initial state dict
    """
    return ExperimentOrchestrationState(
        # Input
        experiment_id=experiment_id,
        run_id=run_id,
        focus_term=focus_term,
        documents=documents,
        user_preferences=user_preferences or {},

        # Stage 1 (will be filled by analyze_experiment_node)
        experiment_goal="",
        term_context=None,

        # Stage 2 (will be filled by recommend_strategy_node)
        recommended_strategy={},
        strategy_reasoning="",
        confidence=0.0,

        # Stage 3 (will be filled by human_review_node or auto-approved)
        strategy_approved=False,
        modified_strategy=None,
        review_notes=None,

        # Stage 4 (will be filled by execute_strategy_node)
        processing_results={},
        execution_trace=[],

        # Stage 5 (will be filled by synthesize_experiment_node)
        cross_document_insights="",
        term_evolution_analysis=None,
        comparative_summary="",

        # Status
        current_stage="analyzing",
        error_message=None
    )
