"""
LangGraph workflow for experiment-level orchestration.

Assembles the 5-stage workflow with conditional branching for human review.

Workflow:
    START
      ↓
    analyze_experiment (Stage 1)
      ↓
    recommend_strategy (Stage 2)
      ↓
    [Conditional: review_choices?]
      ├─ Yes → human_review (Stage 3)
      └─ No  → execute_strategy (Stage 4)
      ↓
    execute_strategy (Stage 4)
      ↓
    synthesize_experiment (Stage 5)
      ↓
    END
"""

from langgraph.graph import StateGraph, END
from typing import Literal

from .experiment_state import ExperimentOrchestrationState
from .experiment_nodes import (
    analyze_experiment_node,
    recommend_strategy_node,
    human_review_node,
    execute_strategy_node,
    synthesize_experiment_node
)


def create_experiment_orchestration_graph():
    """
    Create the experiment-level orchestration LangGraph.

    Returns:
        Compiled StateGraph ready for execution
    """

    # Initialize graph with state schema
    workflow = StateGraph(ExperimentOrchestrationState)

    # Add recommendation phase nodes (Stages 1-2 only)
    workflow.add_node("analyze_experiment", analyze_experiment_node)
    workflow.add_node("recommend_strategy", recommend_strategy_node)

    # Note: execute_strategy and synthesize_experiment will be called separately after approval

    # Set entry point
    workflow.set_entry_point("analyze_experiment")

    # Stage 1 → Stage 2
    workflow.add_edge("analyze_experiment", "recommend_strategy")

    # Stage 2 → END (stop for user review/approval)
    # Processing (Stages 4-5) will happen separately after approval
    workflow.add_edge("recommend_strategy", END)

    # Compile graph
    return workflow.compile()


# Singleton graph instance (lazy initialization)
_experiment_graph = None


def get_experiment_graph():
    """
    Get or create the experiment orchestration graph.

    Uses lazy initialization to avoid creating the graph at module import time.
    """
    global _experiment_graph
    if _experiment_graph is None:
        _experiment_graph = create_experiment_orchestration_graph()
    return _experiment_graph
