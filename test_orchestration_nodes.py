#!/usr/bin/env python3
"""
Test orchestration nodes directly to debug the issue.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models.experiment import Experiment
from app.orchestration.experiment_state import create_initial_experiment_state
from app.orchestration.experiment_nodes import analyze_experiment_node, recommend_strategy_node
import asyncio

EXPERIMENT_ID = 30

async def test_orchestration():
    app = create_app()

    with app.app_context():
        # Get experiment and documents
        experiment = Experiment.query.get(EXPERIMENT_ID)
        if not experiment:
            print(f"ERROR: Experiment {EXPERIMENT_ID} not found")
            return

        documents = []
        for doc in experiment.documents.all():
            documents.append({
                'id': str(doc.id),
                'title': doc.title,
                'content': doc.content[:2000] if doc.content else '',  # First 2000 chars
                'metadata': {
                    'word_count': doc.word_count,
                    'file_type': doc.file_type
                }
            })

        print(f"Experiment: {experiment.name}")
        print(f"Documents loaded: {len(documents)}")
        print()

        # Create initial state
        state = create_initial_experiment_state(
            experiment_id=str(EXPERIMENT_ID),
            run_id="test-run",
            documents=documents,
            focus_term="agent",
            user_preferences={'review_choices': True}
        )

        print("="*60)
        print("STAGE 1: Analyze Experiment")
        print("="*60)

        # Test Stage 1
        result1 = await analyze_experiment_node(state)
        print(f"✓ Stage 1 complete")
        print(f"Experiment Goal: {result1.get('experiment_goal', 'N/A')[:200]}...")
        print()

        # Update state
        state.update(result1)

        print("="*60)
        print("STAGE 2: Recommend Strategy")
        print("="*60)

        # Test Stage 2
        result2 = await recommend_strategy_node(state)
        print(f"✓ Stage 2 complete")
        print(f"Confidence: {result2.get('confidence', 0)}")
        print(f"Recommended Strategy:")
        for doc_id, tools in result2.get('recommended_strategy', {}).items():
            doc = next((d for d in documents if d['id'] == doc_id), None)
            doc_title = doc['title'][:50] if doc else doc_id
            print(f"  - {doc_title}: {tools}")
        print()
        print(f"Reasoning: {result2.get('strategy_reasoning', 'N/A')[:300]}...")

        print()
        print("="*60)
        print("SUCCESS: Both stages completed successfully!")
        print("="*60)

def main():
    try:
        asyncio.run(test_orchestration())
        return 0
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
