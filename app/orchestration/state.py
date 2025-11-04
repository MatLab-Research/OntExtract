"""
State management for LangGraph orchestration workflow

Uses TypedDict for type-safe state management across the graph.
"""

import operator
from typing import TypedDict, Optional, List, Dict, Any
from typing_extensions import Annotated


class OrchestratorState(TypedDict):
    """
    State that flows through the LangGraph orchestration workflow.

    This state is passed between nodes and accumulates information
    as the document processing workflow executes.
    """

    # Input (provided at start)
    document_id: int
    document_text: str
    document_metadata: Dict[str, Any]
    user_preferences: Optional[Dict[str, Any]]

    # Claude's analysis (populated by analyze node)
    document_characteristics: Optional[Dict[str, Any]]
    recommended_tools: Optional[List[str]]
    orchestration_reasoning: Optional[str]
    confidence_score: Optional[float]

    # Tool execution results (populated by tool nodes)
    segmentation_results: Optional[Dict[str, Any]]
    entity_results: Optional[Dict[str, Any]]
    temporal_results: Optional[Dict[str, Any]]
    embedding_results: Optional[Dict[str, Any]]

    # Claude's synthesis (populated by synthesis node)
    synthesis: Optional[str]
    insights: Optional[List[str]]
    suggested_next_steps: Optional[List[str]]

    # Provenance tracking (accumulated throughout)
    execution_trace: Annotated[List[Dict[str, Any]], operator.add]  # Accumulates entries using operator.add

    # Error handling
    errors: Optional[List[str]]
    warnings: Optional[List[str]]


def create_initial_state(
    document_id: int,
    document_text: str,
    document_metadata: Dict[str, Any],
    user_preferences: Optional[Dict[str, Any]] = None
) -> OrchestratorState:
    """
    Create initial state for orchestration workflow.

    Args:
        document_id: ID of document to process
        document_text: Full text content of document
        document_metadata: Metadata about document (title, format, etc.)
        user_preferences: Optional user preferences for processing

    Returns:
        Initial state object ready for graph execution
    """
    return {
        # Input
        "document_id": document_id,
        "document_text": document_text,
        "document_metadata": document_metadata,
        "user_preferences": user_preferences or {},

        # Analysis (to be populated)
        "document_characteristics": None,
        "recommended_tools": None,
        "orchestration_reasoning": None,
        "confidence_score": None,

        # Results (to be populated)
        "segmentation_results": None,
        "entity_results": None,
        "temporal_results": None,
        "embedding_results": None,

        # Synthesis (to be populated)
        "synthesis": None,
        "insights": None,
        "suggested_next_steps": None,

        # Provenance
        "execution_trace": [],

        # Errors
        "errors": None,
        "warnings": None
    }
