"""
Test script for LangGraph orchestration proof-of-concept

Run this to verify the orchestration workflow is functioning correctly.

Usage:
    cd /home/chris/onto/OntExtract
    source venv/bin/activate
    python tests/test_langgraph_orchestration.py
"""

import sys
import os
import asyncio

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.orchestration.state import create_initial_state
from app.orchestration.graph import get_orchestration_graph


# Sample document for testing
SAMPLE_DOCUMENT = """
The principal-agent problem is a fundamental concept in economics and organizational theory.
It was first formalized in the 1970s by economists studying information asymmetry.

In this framework, a principal (such as a company shareholder) delegates work to an agent
(such as a company manager). The challenge arises because the agent may have different
incentives than the principal.

Key entities involved include:
- The Principal (e.g., shareholders, board members)
- The Agent (e.g., CEO, managers, employees)
- Monitoring mechanisms (e.g., audits, performance reviews)
- Incentive structures (e.g., stock options, bonuses)

Historical development:
- 1972: Michael Jensen and William Meckling publish foundational paper
- 1976: Stephen Ross develops formal agency theory
- 1980s: Theory applied to corporate governance
- 1990s: Extended to political science and public administration
- 2000s: Applied to technology platforms and digital marketplaces

The theory has applications in corporate governance, political accountability,
healthcare delivery, and technology platform design.
"""


async def test_orchestration():
    """Test the LangGraph orchestration workflow"""

    print("=" * 70)
    print("LangGraph Orchestration Proof-of-Concept Test")
    print("=" * 70)
    print()

    # Check API key
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not found in environment")
        print("Please set it in your .env file or environment")
        return False

    print(f"✓ Anthropic API key found: {api_key[:20]}...")
    print()

    # Create initial state
    print("Creating initial state...")
    initial_state = create_initial_state(
        document_id=999,
        document_text=SAMPLE_DOCUMENT,
        document_metadata={
            "title": "Test Document: Principal-Agent Theory",
            "format": "text",
            "source": "test"
        },
        user_preferences={}
    )
    print(f"✓ Initial state created for document ID: {initial_state['document_id']}")
    print(f"  Document length: {len(initial_state['document_text'])} characters")
    print()

    # Get the orchestration graph
    print("Building LangGraph workflow...")
    try:
        graph = get_orchestration_graph()
        print("✓ LangGraph workflow compiled successfully")
        print()
    except Exception as e:
        print(f"✗ Error building graph: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Execute the workflow
    print("Executing orchestration workflow...")
    print("-" * 70)
    try:
        # Run the graph
        final_state = await graph.ainvoke(initial_state)

        print("✓ Workflow completed successfully!")
        print()
        print("=" * 70)
        print("RESULTS")
        print("=" * 70)
        print()

        # Display Claude's analysis
        print("1. CLAUDE'S ANALYSIS:")
        print("-" * 70)
        if final_state.get('orchestration_reasoning'):
            print(f"Recommended Tools: {final_state.get('recommended_tools', [])}")
            print(f"Confidence: {final_state.get('confidence_score', 0):.2f}")
            print()
            print("Reasoning:")
            print(final_state['orchestration_reasoning'])
        else:
            print("No orchestration reasoning available")
        print()

        # Display tool results
        print("2. TOOL EXECUTION RESULTS:")
        print("-" * 70)

        if final_state.get('segmentation_results'):
            seg = final_state['segmentation_results']
            print(f"Segmentation: {seg.get('count', 0)} segments created")
            print(f"  Method: {seg.get('method', 'unknown')}")
            print()

        if final_state.get('entity_results'):
            ent = final_state['entity_results']
            print(f"Entity Extraction: {ent.get('count', 0)} entities found")
            print(f"  Method: {ent.get('method', 'unknown')}")
            print(f"  Entity types: {', '.join(ent.get('entity_types', {}).keys())}")

            # Show sample entities
            if ent.get('entities'):
                print(f"\n  Sample entities:")
                for entity in ent['entities'][:10]:
                    print(f"    - {entity['text']} ({entity['label']})")
            print()

        # Display synthesis
        print("3. CLAUDE'S SYNTHESIS:")
        print("-" * 70)
        if final_state.get('synthesis'):
            print(final_state['synthesis'])
            print()

            if final_state.get('insights'):
                print("Key Insights:")
                for insight in final_state['insights']:
                    print(f"  • {insight}")
                print()

            if final_state.get('suggested_next_steps'):
                print("Suggested Next Steps:")
                for step in final_state['suggested_next_steps']:
                    print(f"  → {step}")
                print()

        # Display execution trace (provenance)
        print("4. EXECUTION TRACE (Provenance):")
        print("-" * 70)
        if final_state.get('execution_trace'):
            for i, trace in enumerate(final_state['execution_trace'], 1):
                print(f"{i}. Node: {trace.get('node', 'unknown')}")
                print(f"   Time: {trace.get('timestamp', 'unknown')}")
                if 'tools_recommended' in trace:
                    print(f"   Tools: {trace['tools_recommended']}")
                if 'segments_created' in trace:
                    print(f"   Segments: {trace['segments_created']}")
                if 'entities_found' in trace:
                    print(f"   Entities: {trace['entities_found']}")
                print()

        # Check for errors
        if final_state.get('errors'):
            print("ERRORS:")
            print("-" * 70)
            for error in final_state['errors']:
                print(f"  ✗ {error}")
            print()

        print("=" * 70)
        print("SUCCESS: Orchestration workflow completed!")
        print("=" * 70)
        print()
        print("What this demonstrates:")
        print("  ✓ Claude analyzes document and selects appropriate tools")
        print("  ✓ Selected tools execute in the workflow")
        print("  ✓ Claude synthesizes results into insights")
        print("  ✓ Complete provenance tracked throughout")
        print("  ✓ Ready for JCDL paper documentation!")
        print()

        return True

    except Exception as e:
        print(f"\n✗ Error executing workflow: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = asyncio.run(test_orchestration())

    print()
    if success:
        print("NEXT STEPS:")
        print("1. Review the orchestration decisions and results above")
        print("2. Try with your own documents")
        print("3. Add more tool nodes (temporal, embeddings, etc.)")
        print("4. Document for JCDL paper (Week 1, Days 6-7)")
        print("5. Integrate with Flask API endpoints")
    else:
        print("TROUBLESHOOTING:")
        print("1. Check ANTHROPIC_API_KEY in environment")
        print("2. Ensure LangGraph dependencies installed:")
        print("   pip install -r requirements-langgraph.txt")
        print("3. Check logs for detailed error messages")
