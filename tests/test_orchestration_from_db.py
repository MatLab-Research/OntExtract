"""
Test LangGraph orchestration with documents from OntExtract database

Run with document ID: python tests/test_orchestration_from_db.py <doc_id>
"""

import sys
import os
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Flask app setup for database access
from app import create_app
from app.models.document import Document
from app.orchestration.state import create_initial_state
from app.orchestration.graph import get_orchestration_graph


async def test_document_from_db(document_id: int):
    """Test orchestration with document from database"""

    print(f"Testing Orchestration with Document ID: {document_id}")
    print("=" * 70)
    print()

    # Get document from database
    try:
        document = Document.query.get(document_id)
        if not document:
            print(f"ERROR: Document {document_id} not found in database")
            return
    except Exception as e:
        print(f"ERROR: Cannot access database: {e}")
        print("Make sure PostgreSQL is running and database is accessible")
        return

    print(f"Document: {document.title}")
    print(f"Length: {len(document.content)} characters")
    print()

    # Create state
    initial_state = create_initial_state(
        document_id=document.id,
        document_text=document.content,
        document_metadata={
            "title": document.title,
            "format": getattr(document, 'file_format', 'unknown'),
            "source": getattr(document, 'source', 'database')
        }
    )

    # Get graph
    graph = get_orchestration_graph()

    # Execute
    print("Running orchestration workflow...")
    print()
    final_state = await graph.ainvoke(initial_state)

    # Display results
    print("=" * 70)
    print("CLAUDE'S ANALYSIS")
    print("=" * 70)
    print(f"Recommended Tools: {final_state.get('recommended_tools')}")
    print(f"Confidence: {final_state.get('confidence_score'):.2f}")
    print()
    print("Reasoning:")
    print(final_state.get('orchestration_reasoning'))
    print()

    print("=" * 70)
    print("TOOL RESULTS")
    print("=" * 70)

    if final_state.get('segmentation_results'):
        seg = final_state['segmentation_results']
        print(f"\nSegmentation: {seg['count']} segments")
        print(f"Method: {seg['method']}")

    if final_state.get('entity_results'):
        ent = final_state['entity_results']
        print(f"\nEntity Extraction: {ent['count']} entities")
        print(f"Method: {ent['method']}")
        print(f"Types: {', '.join(ent['entity_types'].keys())}")

        # Show sample
        if ent['entities']:
            print(f"\nSample entities:")
            for entity in ent['entities'][:10]:
                print(f"  - {entity['text']} ({entity['label']})")

    print()
    print("=" * 70)
    print("CLAUDE'S SYNTHESIS")
    print("=" * 70)
    print(final_state.get('synthesis'))

    if final_state.get('insights'):
        print()
        print("Key Insights:")
        for insight in final_state['insights']:
            print(f"  • {insight}")

    print()
    print("=" * 70)
    print("SUCCESS!")
    print("=" * 70)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python tests/test_orchestration_from_db.py <document_id>")
        print()
        print("Example:")
        print("  python tests/test_orchestration_from_db.py 5")
        print()
        print("To see available documents:")
        print("  psql -U ontextract_user -d ontextract_db -c 'SELECT id, title FROM documents LIMIT 10;'")
        sys.exit(1)

    doc_id = int(sys.argv[1])

    # Create Flask app context for database access
    app = create_app()
    with app.app_context():
        asyncio.run(test_document_from_db(doc_id))
