"""
Test LangGraph orchestration with custom documents

Modify CUSTOM_DOCUMENT below to test with your own text.
"""

import sys
import os
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.orchestration.state import create_initial_state
from app.orchestration.graph import get_orchestration_graph


# EDIT THIS - Put your own document text here
CUSTOM_DOCUMENT = """
[Replace this with your document text]

You can paste any text here:
- Research papers
- News articles
- Historical documents
- Technical specifications
- Legal documents
- Whatever you want to analyze!

The orchestrator will analyze it and recommend appropriate tools.
"""


async def test_custom_document():
    """Test orchestration with custom document"""

    print("Testing LangGraph Orchestration with Custom Document")
    print("=" * 70)
    print()

    # Create state
    initial_state = create_initial_state(
        document_id=1000,
        document_text=CUSTOM_DOCUMENT,
        document_metadata={
            "title": "Custom Test Document",
            "format": "text"
        }
    )

    # Get graph
    graph = get_orchestration_graph()

    # Execute
    print("Analyzing document...")
    print()
    final_state = await graph.ainvoke(initial_state)

    # Display results
    print("=" * 70)
    print("CLAUDE'S ANALYSIS")
    print("=" * 70)
    print(f"Recommended Tools: {final_state.get('recommended_tools')}")
    print(f"Confidence: {final_state.get('confidence_score')}")
    print()
    print("Reasoning:")
    print(final_state.get('orchestration_reasoning'))
    print()

    print("=" * 70)
    print("RESULTS")
    print("=" * 70)

    if final_state.get('segmentation_results'):
        print(f"Segments: {final_state['segmentation_results']['count']}")

    if final_state.get('entity_results'):
        print(f"Entities: {final_state['entity_results']['count']}")
        print(f"Types: {list(final_state['entity_results']['entity_types'].keys())}")

    print()
    print("=" * 70)
    print("SYNTHESIS")
    print("=" * 70)
    print(final_state.get('synthesis'))


if __name__ == '__main__':
    asyncio.run(test_custom_document())
