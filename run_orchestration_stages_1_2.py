#!/usr/bin/env python3
"""
Run orchestration Stages 1-2 and save to database (bypasses Flask background thread issue).
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models.experiment import Experiment
from app.models.experiment_orchestration_run import ExperimentOrchestrationRun
from app.orchestration.experiment_state import create_initial_experiment_state
from app.orchestration.experiment_nodes import analyze_experiment_node, recommend_strategy_node
import asyncio
import uuid
from datetime import datetime

EXPERIMENT_ID = 30
USER_ID = 1  # chris

async def run_stages():
    app = create_app()

    with app.app_context():
        # Get experiment and documents
        experiment = Experiment.query.get(EXPERIMENT_ID)
        if not experiment:
            print(f"ERROR: Experiment {EXPERIMENT_ID} not found")
            return None

        documents = []
        for doc in experiment.documents.all():
            documents.append({
                'id': str(doc.id),
                'title': doc.title,
                'content': doc.content or '',
                'metadata': {
                    'word_count': doc.word_count,
                    'file_type': doc.file_type
                }
            })

        print("="*60)
        print("Agent Semantic Evolution - Orchestration Stages 1-2")
        print("="*60)
        print(f"Experiment: {experiment.name}")
        print(f"Documents: {len(documents)}")
        print()

        # Create orchestration run record
        run_id = uuid.uuid4()
        orchestration_run = ExperimentOrchestrationRun(
            id=run_id,
            experiment_id=EXPERIMENT_ID,
            user_id=USER_ID,
            status='analyzing',
            current_stage='analyzing',
            started_at=datetime.utcnow()
        )
        db.session.add(orchestration_run)
        db.session.commit()

        print(f"Created orchestration run: {run_id}")
        print()

        # Create initial state
        state = create_initial_experiment_state(
            experiment_id=str(EXPERIMENT_ID),
            run_id=str(run_id),
            documents=documents,
            focus_term="agent",
            user_preferences={'review_choices': True}
        )

        # Stage 1: Analyze
        print("[Stage 1] Analyzing experiment...")
        result1 = await analyze_experiment_node(state)
        state.update(result1)

        orchestration_run.experiment_goal = result1.get('experiment_goal')
        orchestration_run.term_context = result1.get('term_context')
        orchestration_run.current_stage = 'recommending'
        db.session.commit()

        print(f"✓ Experiment Goal: {result1.get('experiment_goal', '')[:150]}...")
        print()

        # Stage 2: Recommend
        print("[Stage 2] Recommending processing strategy...")
        result2 = await recommend_strategy_node(state)
        state.update(result2)

        orchestration_run.recommended_strategy = result2.get('recommended_strategy', {})
        orchestration_run.strategy_reasoning = result2.get('strategy_reasoning')
        orchestration_run.confidence = result2.get('confidence')
        orchestration_run.status = 'strategy_ready'
        orchestration_run.current_stage = 'reviewing'
        db.session.commit()

        print(f"✓ Strategy recommended (Confidence: {result2.get('confidence', 0)})")
        print()
        print("Recommended Tools per Document:")
        for doc_id, tools in result2.get('recommended_strategy', {}).items():
            doc = next((d for d in documents if d['id'] == doc_id), None)
            if doc:
                print(f"  {doc['title'][:60]}:")
                print(f"    {', '.join(tools)}")
        print()

        print("="*60)
        print("SUCCESS: Stages 1-2 Complete!")
        print("="*60)
        print(f"Run ID: {run_id}")
        print(f"Status: {orchestration_run.status}")
        print()
        print("Next Step:")
        print(f"  Open: http://localhost:8765/orchestration/experiment/{run_id}/review")
        print("="*60)

        return str(run_id)

def main():
    try:
        run_id = asyncio.run(run_stages())
        return 0 if run_id else 1
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
