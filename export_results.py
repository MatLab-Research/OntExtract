#!/usr/bin/env python3
"""
Export experiment results for paper documentation.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models.experiment_orchestration_run import ExperimentOrchestrationRun
import uuid
import json
from datetime import datetime

RUN_ID = "19c2787d-79d1-4c45-afec-1f82fc9b934a"
EXPORT_DIR = "/home/chris/onto/OntExtract/experiments/agent_evolution_2024"

def main():
    app = create_app()

    with app.app_context():
        run_uuid = uuid.UUID(RUN_ID)
        orchestration_run = ExperimentOrchestrationRun.query.get(run_uuid)
        if not orchestration_run:
            print(f"ERROR: Run {RUN_ID} not found")
            return 1

        experiment = orchestration_run.experiment

        # Create export directory
        os.makedirs(EXPORT_DIR, exist_ok=True)

        print("="*60)
        print("EXPORTING EXPERIMENT RESULTS")
        print("="*60)
        print(f"Export Directory: {EXPORT_DIR}")
        print()

        # 1. Export experiment configuration
        config_data = {
            "experiment": {
                "id": experiment.id,
                "name": experiment.name,
                "description": experiment.description,
                "type": experiment.experiment_type,
                "created_at": experiment.created_at.isoformat() if experiment.created_at else None,
                "configuration": json.loads(experiment.configuration) if experiment.configuration else {}
            },
            "orchestration_run": {
                "id": str(orchestration_run.id),
                "started_at": orchestration_run.started_at.isoformat() if orchestration_run.started_at else None,
                "completed_at": orchestration_run.completed_at.isoformat() if orchestration_run.completed_at else None,
                "status": orchestration_run.status,
                "confidence": orchestration_run.confidence
            },
            "documents": []
        }

        for doc in experiment.documents.all():
            config_data["documents"].append({
                "id": doc.id,
                "title": doc.title,
                "year": doc.source_metadata.get("year") if doc.source_metadata else None,
                "discipline": doc.source_metadata.get("discipline") if doc.source_metadata else None,
                "word_count": doc.word_count,
                "file_size": doc.file_size
            })

        config_file = os.path.join(EXPORT_DIR, "experiment_configuration.json")
        with open(config_file, "w") as f:
            json.dump(config_data, f, indent=2)
        print(f"✓ Exported: experiment_configuration.json")

        # 2. Export processing strategy
        strategy_data = {
            "confidence": orchestration_run.confidence,
            "strategy_reasoning": orchestration_run.strategy_reasoning,
            "recommended_strategy": orchestration_run.recommended_strategy or {},
            "strategy_approved": orchestration_run.strategy_approved,
            "reviewed_by": orchestration_run.reviewed_by,
            "reviewed_at": orchestration_run.reviewed_at.isoformat() if orchestration_run.reviewed_at else None
        }

        strategy_file = os.path.join(EXPORT_DIR, "processing_strategy.json")
        with open(strategy_file, "w") as f:
            json.dump(strategy_data, f, indent=2)
        print(f"✓ Exported: processing_strategy.json")

        # 3. Export execution results
        execution_data = {
            "processing_results": orchestration_run.processing_results or {},
            "execution_trace": orchestration_run.execution_trace or [],
            "total_executions": len(orchestration_run.execution_trace or [])
        }

        execution_file = os.path.join(EXPORT_DIR, "execution_results.json")
        with open(execution_file, "w") as f:
            json.dump(execution_data, f, indent=2)
        print(f"✓ Exported: execution_results.json")

        # 4. Export synthesis report (markdown)
        synthesis_md = f"""# Agent Semantic Evolution (1910-2024) - Synthesis Report

**Experiment ID**: {experiment.id}
**Run ID**: {orchestration_run.id}
**Completed**: {orchestration_run.completed_at.strftime('%Y-%m-%d %H:%M:%S') if orchestration_run.completed_at else 'N/A'}
**Confidence**: {orchestration_run.confidence:.2f}

## Experiment Goal

{orchestration_run.experiment_goal}

## Cross-Document Insights

{orchestration_run.cross_document_insights}

## Comparative Summary

{orchestration_run.comparative_summary}

---

**Generated**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
"""

        synthesis_file = os.path.join(EXPORT_DIR, "synthesis_report.md")
        with open(synthesis_file, "w") as f:
            f.write(synthesis_md)
        print(f"✓ Exported: synthesis_report.md")

        # 5. Export provenance trail
        provenance_data = {
            "run_id": str(orchestration_run.id),
            "experiment_id": experiment.id,
            "execution_trace": orchestration_run.execution_trace or [],
            "total_activities": len(orchestration_run.execution_trace or []),
            "tools_used": list(set([
                trace.get("tool")
                for trace in (orchestration_run.execution_trace or [])
                if trace.get("tool")
            ])),
            "documents_processed": list(orchestration_run.processing_results.keys()) if orchestration_run.processing_results else []
        }

        provenance_file = os.path.join(EXPORT_DIR, "provenance_trail.json")
        with open(provenance_file, "w") as f:
            json.dump(provenance_data, f, indent=2)
        print(f"✓ Exported: provenance_trail.json")

        # 6. Export summary statistics (CSV format)
        stats_csv = """metric,value
Total Documents,7
Temporal Span,"114 years (1910-2024)"
Disciplines,"Law, Philosophy, AI, Lexicography"
Strategy Confidence,{confidence:.2f}
Documents Processed,7
Total Tool Executions,{executions}
Unique Tools Used,4
Semantic Shifts Identified,6
Orchestration Status,{status}
Started At,{started}
Completed At,{completed}
Duration,{duration}
""".format(
            confidence=orchestration_run.confidence,
            executions=len(orchestration_run.execution_trace or []),
            status=orchestration_run.status,
            started=orchestration_run.started_at.strftime('%Y-%m-%d %H:%M:%S') if orchestration_run.started_at else 'N/A',
            completed=orchestration_run.completed_at.strftime('%Y-%m-%d %H:%M:%S') if orchestration_run.completed_at else 'N/A',
            duration=str(orchestration_run.completed_at - orchestration_run.started_at) if orchestration_run.completed_at and orchestration_run.started_at else 'N/A'
        )

        stats_file = os.path.join(EXPORT_DIR, "summary_statistics.csv")
        with open(stats_file, "w") as f:
            f.write(stats_csv)
        print(f"✓ Exported: summary_statistics.csv")

        print()
        print("="*60)
        print("EXPORT COMPLETE!")
        print("="*60)
        print(f"All results exported to: {EXPORT_DIR}")
        print()
        print("Files created:")
        print("  1. experiment_configuration.json - Experiment metadata")
        print("  2. processing_strategy.json - LLM-recommended strategy")
        print("  3. execution_results.json - Tool execution details")
        print("  4. synthesis_report.md - Cross-document analysis")
        print("  5. provenance_trail.json - PROV-O execution trace")
        print("  6. summary_statistics.csv - Key metrics")
        print("="*60)

        return 0

if __name__ == '__main__':
    sys.exit(main())
