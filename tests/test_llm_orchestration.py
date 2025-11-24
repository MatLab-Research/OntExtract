#!/usr/bin/env python3
"""
Test script for LLM Orchestration Workflow

Tests the 5-stage LangGraph workflow:
1. Analyze Experiment
2. Recommend Strategy
3. Review Strategy (Human-in-the-Loop)
4. Execute Strategy
5. Synthesize Insights

Usage:
    python test_llm_orchestration.py [experiment_id]
"""

import requests
import time
import json
import sys
from typing import Optional

BASE_URL = "http://localhost:8765"
EXPERIMENT_ID = 83  # Default demo experiment

# Demo credentials
DEMO_USERNAME = "demo"
DEMO_PASSWORD = "demo123"

# Global session for authenticated requests
session = requests.Session()


class Colors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_stage(stage_name: str):
    """Print stage header"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}Stage: {stage_name}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}\n")


def print_success(message: str):
    """Print success message"""
    print(f"{Colors.OKGREEN}✓ {message}{Colors.ENDC}")


def print_error(message: str):
    """Print error message"""
    print(f"{Colors.FAIL}✗ {message}{Colors.ENDC}")


def print_info(message: str):
    """Print info message"""
    print(f"{Colors.OKCYAN}ℹ {message}{Colors.ENDC}")


def print_warning(message: str):
    """Print warning message"""
    print(f"{Colors.WARNING}⚠ {message}{Colors.ENDC}")


def login() -> bool:
    """
    Login to OntExtract with demo credentials

    Returns True if successful, False otherwise
    """
    print_stage("0. Authentication")

    url = f"{BASE_URL}/auth/login"
    payload = {
        "username": DEMO_USERNAME,
        "password": DEMO_PASSWORD
    }

    print_info(f"POST {url}")
    print_info(f"Username: {DEMO_USERNAME}")

    try:
        response = session.post(url, data=payload)
        print_info(f"Status Code: {response.status_code}")

        if response.status_code == 200 or response.status_code == 302:
            print_success("Authentication successful")
            return True
        else:
            print_error(f"Failed to authenticate")
            print_error(f"Response: {response.text}")
            return False

    except Exception as e:
        print_error(f"Exception occurred: {e}")
        return False


def start_orchestration(experiment_id: int) -> Optional[str]:
    """
    Start LLM orchestration workflow

    Returns run_id if successful, None otherwise
    """
    print_stage("1. Start LLM Orchestration")

    url = f"{BASE_URL}/experiments/{experiment_id}/orchestration/analyze"
    payload = {
        "review_choices": True  # Enable human-in-the-loop review
    }

    print_info(f"POST {url}")
    print_info(f"Payload: {json.dumps(payload, indent=2)}")

    try:
        response = session.post(url, json=payload)
        print_info(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print_success("Orchestration started successfully")
            print_info(f"Run ID: {data.get('run_id')}")
            print_info(f"Status: {data.get('status')}")
            print_info(f"Current Stage: {data.get('current_stage')}")
            return data.get('run_id')
        else:
            print_error(f"Failed to start orchestration")
            print_error(f"Response: {response.text}")
            return None

    except Exception as e:
        print_error(f"Exception occurred: {e}")
        return None


def poll_orchestration_status(run_id: str, max_polls: int = 60, poll_interval: int = 2) -> dict:
    """
    Poll orchestration status until complete or max_polls reached

    Returns final status dict
    """
    print_stage("2. Poll Orchestration Status")

    url = f"{BASE_URL}/orchestration/status/{run_id}"
    print_info(f"GET {url}")
    print_info(f"Polling every {poll_interval}s for max {max_polls} times...")

    for i in range(max_polls):
        try:
            response = session.get(url)

            if response.status_code == 200:
                data = response.json()
                status = data.get('status')
                current_stage = data.get('current_stage')
                progress = data.get('progress_percentage', 0)

                print(f"\rPoll {i+1}/{max_polls}: Status={status}, Stage={current_stage}, Progress={progress}%", end="")

                # Check if we're waiting for review
                if status == 'reviewing' or data.get('awaiting_user_approval'):
                    print()  # New line
                    print_success("Orchestration reached review stage")
                    print_info(f"Awaiting user approval: {data.get('awaiting_user_approval', False)}")
                    return data

                # Check if completed
                if status == 'completed':
                    print()  # New line
                    print_success("Orchestration completed")
                    return data

                # Check if failed
                if status == 'failed':
                    print()  # New line
                    print_error(f"Orchestration failed: {data.get('error_message')}")
                    return data

            else:
                print()  # New line
                print_error(f"Failed to get status: {response.status_code}")
                print_error(f"Response: {response.text}")
                return {}

            time.sleep(poll_interval)

        except Exception as e:
            print()  # New line
            print_error(f"Exception occurred: {e}")
            return {}

    print()  # New line
    print_warning("Max polls reached - orchestration still running")
    return {}


def display_strategy(status_data: dict):
    """Display recommended strategy details"""
    print_stage("3. Review Recommended Strategy")

    if not status_data:
        print_error("No status data available")
        return

    print_info(f"Experiment Goal:")
    print(f"  {status_data.get('experiment_goal', 'N/A')}")

    print_info(f"\nStrategy Reasoning:")
    print(f"  {status_data.get('strategy_reasoning', 'N/A')}")

    print_info(f"\nConfidence: {status_data.get('confidence', 0.0):.2f}")

    print_info(f"\nRecommended Strategy:")
    strategy = status_data.get('recommended_strategy', {})
    for doc_id, tools in strategy.items():
        print(f"  Document {doc_id}: {', '.join(tools)}")


def approve_strategy(run_id: str, approve: bool = True, modified_strategy: Optional[dict] = None) -> dict:
    """
    Approve or reject strategy

    Returns result dict
    """
    print_stage("4. Approve Strategy")

    url = f"{BASE_URL}/orchestration/approve-strategy/{run_id}"
    payload = {
        "strategy_approved": approve,
        "review_notes": "Test approval - automated test script"
    }

    if modified_strategy:
        payload["modified_strategy"] = modified_strategy

    print_info(f"POST {url}")
    print_info(f"Payload: {json.dumps(payload, indent=2)}")

    try:
        response = session.post(url, json=payload)
        print_info(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print_success("Strategy approval successful")
            print_info(f"Status: {data.get('status')}")
            print_info(f"Message: {data.get('message')}")
            return data
        else:
            print_error(f"Failed to approve strategy")
            print_error(f"Response: {response.text}")
            return {}

    except Exception as e:
        print_error(f"Exception occurred: {e}")
        return {}


def display_results(experiment_id: int, run_id: str):
    """Display orchestration results"""
    print_stage("5. View Results")

    # Get status for final summary
    url = f"{BASE_URL}/orchestration/status/{run_id}"
    print_info(f"GET {url}")

    try:
        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()

            print_success("Orchestration Complete!")
            print_info(f"Status: {data.get('status')}")
            print_info(f"Duration: {data.get('duration_seconds', 0):.1f} seconds")

            # Stage completion
            stages = data.get('stage_completed', {})
            print_info("\nStage Completion:")
            for stage, completed in stages.items():
                status = "✓" if completed else "✗"
                print(f"  {status} {stage}")

            # Results URL
            results_url = f"{BASE_URL}/experiments/{experiment_id}/orchestration/llm-results/{run_id}"
            print_info(f"\nView full results at: {results_url}")

            # Provenance URL
            provenance_url = f"{BASE_URL}/experiments/{experiment_id}/orchestration/llm-provenance/{run_id}"
            print_info(f"Download provenance: {provenance_url}")

        else:
            print_error(f"Failed to get results: {response.status_code}")
            print_error(f"Response: {response.text}")

    except Exception as e:
        print_error(f"Exception occurred: {e}")


def main():
    """Main test workflow"""
    # Get experiment ID from command line or use default
    experiment_id = int(sys.argv[1]) if len(sys.argv) > 1 else EXPERIMENT_ID

    print(f"\n{Colors.BOLD}{Colors.HEADER}LLM Orchestration Workflow Test{Colors.ENDC}")
    print(f"{Colors.BOLD}Experiment ID: {experiment_id}{Colors.ENDC}")
    print(f"{Colors.BOLD}Base URL: {BASE_URL}{Colors.ENDC}\n")

    # Stage 0: Login
    if not login():
        print_error("\nTest failed: Could not authenticate")
        sys.exit(1)

    # Stage 1: Start orchestration
    run_id = start_orchestration(experiment_id)
    if not run_id:
        print_error("\nTest failed: Could not start orchestration")
        sys.exit(1)

    # Stage 2: Poll for status (wait for review stage)
    status_data = poll_orchestration_status(run_id)
    if not status_data:
        print_error("\nTest failed: Could not get orchestration status")
        sys.exit(1)

    # Stage 3: Display strategy
    display_strategy(status_data)

    # Prompt user for approval
    print()
    user_input = input(f"{Colors.BOLD}Approve strategy? (y/n, default=y): {Colors.ENDC}").strip().lower()
    approve = user_input != 'n'

    # Stage 4: Approve/reject strategy
    approval_result = approve_strategy(run_id, approve=approve)
    if not approval_result:
        print_error("\nTest failed: Could not approve strategy")
        sys.exit(1)

    # If rejected, exit
    if not approve:
        print_warning("\nStrategy rejected - test complete")
        sys.exit(0)

    # Wait for execution to complete
    print_info("\nWaiting for execution to complete...")
    final_status = poll_orchestration_status(run_id, max_polls=120, poll_interval=5)

    if final_status.get('status') != 'completed':
        print_error(f"\nTest failed: Orchestration did not complete successfully")
        sys.exit(1)

    # Stage 5: Display results
    display_results(experiment_id, run_id)

    print(f"\n{Colors.OKGREEN}{Colors.BOLD}Test completed successfully!{Colors.ENDC}\n")


if __name__ == "__main__":
    main()
