#!/usr/bin/env python3
"""
Start experiment orchestration using Flask test client (bypasses HTTP auth).
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models.user import User
from app.models.experiment import Experiment
import json

EXPERIMENT_ID = 30

def main():
    app = create_app()

    with app.app_context():
        # Verify experiment exists
        experiment = Experiment.query.get(EXPERIMENT_ID)
        if not experiment:
            print(f"ERROR: Experiment {EXPERIMENT_ID} not found")
            return 1

        # Get user
        user = User.query.filter_by(username='chris').first()
        if not user:
            print("ERROR: User 'chris' not found")
            return 1

        print("="*60)
        print("Agent Semantic Evolution Experiment - Orchestration Workflow")
        print("="*60)
        print(f"Experiment: {experiment.name}")
        print(f"Documents: {experiment.documents.count()}")
        print(f"User: {user.username}")
        print()

        # Use Flask test client
        with app.test_client() as client:
            # Login
            with client.session_transaction() as sess:
                sess['_user_id'] = str(user.id)
                sess['_fresh'] = True

            print("Starting orchestration (Stages 1-2: Analyze + Recommend)...")

            # Start orchestration
            response = client.post(
                f'/orchestration/analyze-experiment/{EXPERIMENT_ID}',
                data=json.dumps({'review_choices': True}),
                content_type='application/json'
            )

            if response.status_code == 200:
                data = response.get_json()
                run_id = data.get('run_id')
                print(f"✓ Orchestration started successfully!")
                print(f"  Run ID: {run_id}")
                print(f"  Status: {data.get('message')}")
                print()
                print("="*60)
                print("Orchestration is now running in the background.")
                print()
                print("To monitor progress:")
                print(f"  1. Open: http://localhost:8765/orchestration/experiment/{run_id}/status")
                print(f"  2. Wait for 'strategy_ready' status")
                print()
                print("To review the strategy:")
                print(f"  Open: http://localhost:8765/orchestration/experiment/{run_id}/review")
                print()
                print("Expected timeline:")
                print("  - Stage 1 (Analyze): ~30-60 seconds")
                print("  - Stage 2 (Recommend): ~60-90 seconds")
                print("  - Total: ~2-3 minutes")
                print("="*60)

                return 0
            else:
                print(f"✗ Failed to start orchestration: {response.status_code}")
                print(f"  Response: {response.get_data(as_text=True)}")
                return 1

if __name__ == '__main__':
    sys.exit(main())
