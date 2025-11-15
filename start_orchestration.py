#!/usr/bin/env python3
"""
Start experiment orchestration for Agent Semantic Evolution experiment.
"""

import requests
import json
import time
import sys

EXPERIMENT_ID = 30
BASE_URL = "http://localhost:8765"

# Login session (using demo user)
session = requests.Session()

def login():
    """Login to get authenticated session"""
    response = session.post(
        f"{BASE_URL}/auth/login",
        data={
            'username': 'chris',
            'password': 'password'
        },
        allow_redirects=True
    )

    # Check if we have session cookie
    cookies = session.cookies.get_dict()
    print(f"  Cookies: {list(cookies.keys())}")

    if response.status_code == 200 or 'session' in cookies:
        print("✓ Logged in successfully")
        return True
    else:
        print(f"✗ Login failed: {response.status_code}")
        print(f"  Response: {response.text[:200]}")
        return False

def start_orchestration():
    """Start orchestration Stages 1-2 (analyze + recommend)"""
    print(f"\nStarting orchestration for experiment {EXPERIMENT_ID}...")

    response = session.post(
        f"{BASE_URL}/orchestration/analyze-experiment/{EXPERIMENT_ID}",
        json={'review_choices': True},
        headers={'Content-Type': 'application/json'}
    )

    if response.status_code == 200:
        data = response.json()
        run_id = data.get('run_id')
        print(f"✓ Orchestration started")
        print(f"  Run ID: {run_id}")
        print(f"  Message: {data.get('message')}")
        return run_id
    else:
        print(f"✗ Failed to start orchestration: {response.status_code}")
        print(f"  Response: {response.text}")
        return None

def monitor_progress(run_id):
    """Monitor orchestration progress via SSE"""
    print(f"\nMonitoring progress for run {run_id}...")
    print("="*60)

    url = f"{BASE_URL}/orchestration/experiment/{run_id}/status"

    try:
        response = session.get(url, stream=True, timeout=300)

        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    data_str = line_str[6:]  # Remove 'data: ' prefix
                    try:
                        data = json.loads(data_str)

                        if 'heartbeat' in data:
                            print(".", end="", flush=True)
                            continue

                        stage = data.get('stage', 'unknown')
                        status = data.get('status', 'unknown')
                        progress = data.get('progress', 0)
                        message = data.get('message', '')

                        print(f"\n[{progress}%] {stage.upper()}: {message}")

                        # Check if complete
                        if status == 'strategy_ready':
                            print("\n" + "="*60)
                            print("✓ Strategy recommendation complete!")
                            print(f"  Review at: {BASE_URL}/orchestration/experiment/{run_id}/review")
                            return True

                        if status == 'failed':
                            error = data.get('error', 'Unknown error')
                            print(f"\n✗ Orchestration failed: {error}")
                            return False

                    except json.JSONDecodeError:
                        pass

    except Exception as e:
        print(f"\n✗ Error monitoring progress: {e}")
        return False

def main():
    print("="*60)
    print("Agent Semantic Evolution Experiment - Orchestration Workflow")
    print("="*60)

    # Login
    if not login():
        return 1

    # Start orchestration (Stages 1-2)
    run_id = start_orchestration()
    if not run_id:
        return 1

    # Monitor progress
    success = monitor_progress(run_id)

    if success:
        print("\n" + "="*60)
        print("NEXT STEPS:")
        print(f"1. Open browser to: {BASE_URL}/orchestration/experiment/{run_id}/review")
        print("2. Review the recommended strategy")
        print("3. Approve to continue with Stages 4-5 (execute + synthesize)")
        print("="*60)
        return 0
    else:
        return 1

if __name__ == '__main__':
    sys.exit(main())
