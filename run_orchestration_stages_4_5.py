#!/usr/bin/env python3
"""
Approve strategy and run Stages 4-5 (Execute + Synthesize).
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models.experiment import Experiment
from app.models.experiment_orchestration_run import ExperimentOrchestrationRun
from app.orchestration.experiment_nodes import execute_strategy_node, synthesize_experiment_node
import asyncio
from datetime import datetime
import uuid

RUN_ID = "19c2787d-79d1-4c45-afec-1f82fc9b934a"
USER_ID = 1  # chris

async def run_stages():
    app = create_app()

    with app.app_context():
        # Get orchestration run
        run_uuid = uuid.UUID(RUN_ID)
        orchestration_run = ExperimentOrchestrationRun.query.get(run_uuid)
        if not orchestration_run:
            print(f"ERROR: Orchestration run {RUN_ID} not found")
            return None

        if orchestration_run.status != 'strategy_ready':
            print(f"ERROR: Run status is {orchestration_run.status}, expected 'strategy_ready'")
            return None

        # Get experiment
        experiment = orchestration_run.experiment

        print("="*60)
        print("Agent Semantic Evolution - Orchestration Stages 4-5")
        print("="*60)
        print(f"Run ID: {RUN_ID}")
        print(f"Experiment: {experiment.name}")
        print()

        # Stage 3: Approve (auto-approve)
        print("[Stage 3] Auto-approving strategy...")
        orchestration_run.strategy_approved = True
        orchestration_run.reviewed_by = USER_ID
        orchestration_run.reviewed_at = datetime.utcnow()
        orchestration_run.review_notes = "Auto-approved via script"
        orchestration_run.status = 'executing'
        orchestration_run.current_stage = 'executing'
        db.session.commit()
        print("✓ Strategy approved")
        print()

        # Prepare state for stages 4-5
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

        state = {
            'experiment_id': str(experiment.id),
            'run_id': RUN_ID,
            'documents': documents,
            'focus_term': 'agent',
            'user_preferences': {'review_choices': True},

            # Stage 1-2 results from database
            'experiment_goal': orchestration_run.experiment_goal,
            'term_context': orchestration_run.term_context,
            'recommended_strategy': orchestration_run.recommended_strategy,
            'strategy_reasoning': orchestration_run.strategy_reasoning,
            'confidence': orchestration_run.confidence,

            # Stage 3 (just approved)
            'strategy_approved': True,
            'modified_strategy': None,
            'review_notes': 'Auto-approved via script',

            # Initialize Stage 4-5 fields
            'processing_results': {},
            'execution_trace': [],
            'cross_document_insights': '',
            'term_evolution_analysis': None,
            'comparative_summary': '',
            'current_stage': 'executing',
            'error_message': None
        }

        # Stage 4: Execute Strategy
        print("[Stage 4] Executing processing strategy...")
        print("Processing all documents with recommended tools...")
        print()

        try:
            result4 = await execute_strategy_node(state)
            state.update(result4)

            orchestration_run.processing_results = result4.get('processing_results', {})
            orchestration_run.execution_trace = result4.get('execution_trace', [])
            orchestration_run.current_stage = 'synthesizing'
            db.session.commit()

            print("✓ Stage 4 complete - All documents processed")

            # Show processing summary
            processing_results = result4.get('processing_results', {})
            print(f"\nProcessing Summary:")
            for doc_id, doc_results in processing_results.items():
                doc = next((d for d in documents if d['id'] == doc_id), None)
                if doc:
                    print(f"  {doc['title'][:60]}:")
                    for tool, result in doc_results.items():
                        status = "✓" if result else "✗"
                        print(f"    {status} {tool}")
            print()

        except Exception as e:
            print(f"✗ Stage 4 failed: {e}")
            import traceback
            traceback.print_exc()
            orchestration_run.status = 'failed'
            orchestration_run.error_message = str(e)
            db.session.commit()
            return None

        # Stage 5: Synthesize Experiment
        print("[Stage 5] Synthesizing cross-document insights...")

        try:
            result5 = await synthesize_experiment_node(state)
            state.update(result5)

            orchestration_run.cross_document_insights = result5.get('cross_document_insights')
            orchestration_run.term_evolution_analysis = result5.get('term_evolution_analysis')
            orchestration_run.comparative_summary = result5.get('comparative_summary')
            orchestration_run.status = 'completed'
            orchestration_run.current_stage = 'completed'
            orchestration_run.completed_at = datetime.utcnow()
            db.session.commit()

            print("✓ Stage 5 complete - Synthesis generated")
            print()

        except Exception as e:
            print(f"✗ Stage 5 failed: {e}")
            import traceback
            traceback.print_exc()
            orchestration_run.status = 'failed'
            orchestration_run.error_message = str(e)
            db.session.commit()
            return None

        print("="*60)
        print("SUCCESS: All Stages Complete!")
        print("="*60)
        print(f"Status: {orchestration_run.status}")
        print()
        print("Cross-Document Insights:")
        print(orchestration_run.cross_document_insights[:500] + "...")
        print()
        print("="*60)
        print("View Results:")
        print(f"  http://localhost:8765/orchestration/experiment/{RUN_ID}/results")
        print("="*60)

        return RUN_ID

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
