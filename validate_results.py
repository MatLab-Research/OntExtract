#!/usr/bin/env python3
"""
Validate experiment results against success criteria from implementation plan.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models.experiment_orchestration_run import ExperimentOrchestrationRun
import uuid
import json

RUN_ID = "19c2787d-79d1-4c45-afec-1f82fc9b934a"

# Success criteria from EXPERIMENT_IMPLEMENTATION_PLAN.md
SUCCESS_CRITERIA = {
    "documents": 7,
    "temporal_span": 114,  # years
    "confidence_range": (0.87, 0.94),
    "semantic_shifts": 4,  # minimum expected
    "documents_processed": 7,
    "all_tools_successful": True
}

def main():
    app = create_app()

    with app.app_context():
        run_uuid = uuid.UUID(RUN_ID)
        orchestration_run = ExperimentOrchestrationRun.query.get(run_uuid)
        if not orchestration_run:
            print(f"ERROR: Run {RUN_ID} not found")
            return 1

        experiment = orchestration_run.experiment

        print("="*60)
        print("EXPERIMENT RESULTS VALIDATION")
        print("="*60)
        print(f"Experiment: {experiment.name}")
        print(f"Run ID: {RUN_ID}")
        print()

        results = {
            "success": True,
            "checks": []
        }

        # Check 1: Document count
        doc_count = experiment.documents.count()
        check1 = {
            "criteria": "Total documents",
            "expected": SUCCESS_CRITERIA["documents"],
            "actual": doc_count,
            "pass": doc_count == SUCCESS_CRITERIA["documents"]
        }
        results["checks"].append(check1)

        # Check 2: Temporal span
        config = json.loads(experiment.configuration) if experiment.configuration else {}
        temporal_span = config.get("temporal_span", "").replace(" years", "")
        try:
            temporal_span = int(temporal_span)
        except:
            temporal_span = 0

        check2 = {
            "criteria": "Temporal span",
            "expected": f"{SUCCESS_CRITERIA['temporal_span']} years",
            "actual": f"{temporal_span} years",
            "pass": temporal_span == SUCCESS_CRITERIA["temporal_span"]
        }
        results["checks"].append(check2)

        # Check 3: Confidence score
        confidence = orchestration_run.confidence or 0
        check3 = {
            "criteria": "Confidence score range",
            "expected": f"{SUCCESS_CRITERIA['confidence_range'][0]}-{SUCCESS_CRITERIA['confidence_range'][1]}",
            "actual": f"{confidence:.2f}",
            "pass": SUCCESS_CRITERIA['confidence_range'][0] <= confidence <= SUCCESS_CRITERIA['confidence_range'][1]
        }
        results["checks"].append(check3)

        # Check 4: Semantic shifts identified
        insights = orchestration_run.cross_document_insights or ""
        # Count bullet points in insights (each represents a key finding)
        semantic_shifts = insights.count("•")
        check4 = {
            "criteria": "Semantic shifts identified",
            "expected": f">= {SUCCESS_CRITERIA['semantic_shifts']}",
            "actual": semantic_shifts,
            "pass": semantic_shifts >= SUCCESS_CRITERIA["semantic_shifts"]
        }
        results["checks"].append(check4)

        # Check 5: Complete provenance trail
        execution_trace = orchestration_run.execution_trace or []
        check5 = {
            "criteria": "Provenance records (execution trace)",
            "expected": "Complete for all stages",
            "actual": f"{len(execution_trace)} executions",
            "pass": len(execution_trace) > 0
        }
        results["checks"].append(check5)

        # Check 6: Processing results
        processing_results = orchestration_run.processing_results or {}
        docs_processed = len(processing_results)
        check6 = {
            "criteria": "Documents processed",
            "expected": SUCCESS_CRITERIA["documents_processed"],
            "actual": docs_processed,
            "pass": docs_processed == SUCCESS_CRITERIA["documents_processed"]
        }
        results["checks"].append(check6)

        # Check 7: All stages completed
        check7 = {
            "criteria": "Orchestration status",
            "expected": "completed",
            "actual": orchestration_run.status,
            "pass": orchestration_run.status == "completed"
        }
        results["checks"].append(check7)

        # Print results
        print("VALIDATION RESULTS:")
        print("-" * 60)

        for i, check in enumerate(results["checks"], 1):
            status = "✓ PASS" if check["pass"] else "✗ FAIL"
            print(f"{i}. {check['criteria']}")
            print(f"   Expected: {check['expected']}")
            print(f"   Actual: {check['actual']}")
            print(f"   {status}")
            print()

            if not check["pass"]:
                results["success"] = False

        print("="*60)
        if results["success"]:
            print("SUCCESS: All validation criteria passed! ✓")
        else:
            print("FAILURE: Some validation criteria failed ✗")
        print("="*60)

        return 0 if results["success"] else 1

if __name__ == '__main__':
    sys.exit(main())
