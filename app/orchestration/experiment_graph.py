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

    # Add all nodes
    workflow.add_node("analyze_experiment", analyze_experiment_node)
    workflow.add_node("recommend_strategy", recommend_strategy_node)
    workflow.add_node("human_review", human_review_node)
    workflow.add_node("execute_strategy", execute_strategy_node)
    workflow.add_node("synthesize_experiment", synthesize_experiment_node)

    # Set entry point
    workflow.set_entry_point("analyze_experiment")

    # Stage 1 → Stage 2
    workflow.add_edge("analyze_experiment", "recommend_strategy")

    # Stage 2 → Conditional: Review or Execute?
    def should_review(state: ExperimentOrchestrationState) -> Literal["human_review", "execute_strategy"]:
        """
        Decide whether to route through human review.

        If review_choices=True in user_preferences, go to human_review node.
        Otherwise, proceed directly to execution.
        """
        if state['user_preferences'].get('review_choices', False):
            return "human_review"
        else:
            return "execute_strategy"

    workflow.add_conditional_edges(
        "recommend_strategy",
        should_review,
        {
            "human_review": "human_review",
            "execute_strategy": "execute_strategy"
        }
    )

    # Stage 3 → Stage 4 (after review approval)
    workflow.add_edge("human_review", "execute_strategy")

    # Stage 4 → Stage 5
    workflow.add_edge("execute_strategy", "synthesize_experiment")

    # Stage 5 → END
    workflow.add_edge("synthesize_experiment", END)

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
