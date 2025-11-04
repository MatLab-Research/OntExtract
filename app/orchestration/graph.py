"""
LangGraph orchestration graph builder

Constructs the document processing workflow as a state graph.
Uses LangGraph 1.0+ best practices (January 2025).
"""

import logging
from typing import List, Literal

from langgraph.graph import StateGraph, END

from app.orchestration.state import OrchestratorState
from app.orchestration.nodes import (
    analyze_document_node,
    segment_paragraph_node,
    extract_entities_spacy_node,
    synthesize_results_node
)

logger = logging.getLogger(__name__)


def should_run_segmentation(state: OrchestratorState) -> bool:
    """Check if segmentation should run based on recommended tools"""
    recommended = state.get("recommended_tools", [])
    return any(tool.startswith("segment_") for tool in recommended)


def should_run_entities(state: OrchestratorState) -> bool:
    """Check if entity extraction should run based on recommended tools"""
    recommended = state.get("recommended_tools", [])
    return any("entities" in tool for tool in recommended)


def route_after_analysis(state: OrchestratorState) -> List[str]:
    """
    Route to appropriate tool nodes after Claude's analysis.

    This is the key orchestration decision point where we route
    to different tools based on Claude's recommendations.

    Args:
        state: Current state with recommended_tools

    Returns:
        List of node names to execute next
    """
    recommended = state.get("recommended_tools", [])

    if not recommended:
        logger.warning("No tools recommended, skipping to synthesis")
        return ["synthesize"]

    # Map tool recommendations to node names
    tool_to_node = {
        "segment_paragraph": "segment_paragraph",
        "segment_sentence": "segment_paragraph",  # Use same node for now
        "extract_entities_spacy": "extract_entities",
        "extract_entities_langextract": "extract_entities",  # Use same node for now
    }

    # Determine which nodes to activate
    nodes_to_run = set()
    for tool in recommended:
        if tool in tool_to_node:
            nodes_to_run.add(tool_to_node[tool])

    logger.info(f"Routing to nodes: {nodes_to_run}")

    return list(nodes_to_run) if nodes_to_run else ["synthesize"]


def build_orchestration_graph():
    """
    Build the LangGraph orchestration workflow.

    Graph structure:
        START
          ↓
        [analyze] - Claude analyzes document
          ↓
        [conditional routing based on recommendations]
          ↙     ↘
    [segment]  [entities]  (parallel execution)
          ↘     ↙
        [synthesize] - Claude interprets results
          ↓
        END

    Returns:
        Compiled LangGraph workflow
    """

    logger.info("Building LangGraph orchestration workflow")

    # Create state graph
    workflow = StateGraph(OrchestratorState)

    # Add nodes
    workflow.add_node("analyze", analyze_document_node)
    workflow.add_node("segment_paragraph", segment_paragraph_node)
    workflow.add_node("extract_entities", extract_entities_spacy_node)
    workflow.add_node("synthesize", synthesize_results_node)

    # Set entry point
    workflow.set_entry_point("analyze")

    # Conditional routing after analysis
    # This is where Claude's decisions determine which tools run
    workflow.add_conditional_edges(
        "analyze",
        route_after_analysis,
        {
            "segment_paragraph": "segment_paragraph",
            "extract_entities": "extract_entities",
            "synthesize": "synthesize"  # Skip to synthesis if no tools
        }
    )

    # All tool nodes converge to synthesis
    workflow.add_edge("segment_paragraph", "synthesize")
    workflow.add_edge("extract_entities", "synthesize")

    # Synthesis is the final step
    workflow.add_edge("synthesize", END)

    # Compile the graph
    compiled_graph = workflow.compile()

    logger.info("LangGraph workflow compiled successfully")

    return compiled_graph


# Singleton instance
_graph_instance = None


def get_orchestration_graph():
    """
    Get or create the orchestration graph instance.

    Returns:
        Compiled LangGraph workflow (singleton)
    """
    global _graph_instance

    if _graph_instance is None:
        _graph_instance = build_orchestration_graph()

    return _graph_instance
