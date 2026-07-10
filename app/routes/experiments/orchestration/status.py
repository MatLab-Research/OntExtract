"""Orchestration run and processing status routes."""

from flask import render_template, request, jsonify
from flask_login import current_user
from app.utils.auth_decorators import api_require_login_for_write
from app.services.base_service import ServiceError, NotFoundError
import markdown
from app.models.experiment_orchestration_run import ExperimentOrchestrationRun
from app.models import Experiment
from app import db
from datetime import datetime
from .. import experiments_bp
from .context import logger


@experiments_bp.route('/<int:experiment_id>/orchestration/check-status', methods=['GET'])
def check_experiment_processing_status(experiment_id):
    """
    Check if documents have already been processed.

    Used to warn users before starting LLM orchestration on already-processed documents.

    Returns:
    {
        "experiment_id": 123,
        "total_documents": 5,
        "processed_documents": 2,
        "unprocessed_documents": 3,
        "has_partial_processing": true,
        "has_full_processing": false,
        "documents": [
            {
                "document_id": 217,
                "title": "Document A",
                "has_processing": true,
                "processing_types": ["segmentation", "entities"]
            },
            ...
        ]
    }
    """
    try:
        from app.models import TextSegment, ProcessingJob, ProcessingArtifact, Document

        # Get experiment
        experiment = Experiment.query.get(experiment_id)
        if not experiment:
            return jsonify({'error': 'Experiment not found'}), 404

        # Get all documents for this experiment
        documents = Document.query.filter_by(experiment_id=experiment_id).all()

        processing_status = []
        for doc in documents:
            # Check for existing processing
            has_segments = TextSegment.query.filter_by(document_id=doc.id).first() is not None
            has_entities = ProcessingJob.query.filter_by(
                document_id=doc.id,
                job_type='entity_extraction'
            ).first() is not None
            has_artifacts = ProcessingArtifact.query.filter_by(document_id=doc.id).first() is not None

            status = {
                'document_id': doc.id,
                'title': doc.title,
                'has_processing': has_segments or has_entities or has_artifacts,
                'processing_types': []
            }

            if has_segments:
                status['processing_types'].append('segmentation')
            if has_entities:
                status['processing_types'].append('entities')
            if has_artifacts:
                artifacts = ProcessingArtifact.query.filter_by(document_id=doc.id).all()
                # Get unique tool names
                tool_names = list(set(a.tool_name for a in artifacts))
                status['processing_types'].extend(tool_names)

            processing_status.append(status)

        # Summary
        processed_count = sum(1 for s in processing_status if s['has_processing'])
        total_docs = len(documents)

        return jsonify({
            'experiment_id': experiment_id,
            'total_documents': total_docs,
            'processed_documents': processed_count,
            'unprocessed_documents': total_docs - processed_count,
            'has_partial_processing': 0 < processed_count < total_docs,
            'has_full_processing': processed_count == total_docs and total_docs > 0,
            'documents': processing_status
        }), 200

    except Exception as e:
        logger.error(f"Error checking processing status for experiment {experiment_id}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@experiments_bp.route('/<int:experiment_id>/orchestration/latest-run', methods=['GET'])
def get_latest_orchestration_run(experiment_id):
    """
    Get the latest orchestration run for an experiment (if any in progress).

    Used to resume existing runs instead of creating duplicates.

    Only returns runs that:
    1. Are not completed/failed
    2. Started within the last 30 minutes (prevents resuming stuck/old runs)

    Returns:
    {
        "run_id": "uuid",
        "status": "reviewing|executing|etc",
        "started_at": "timestamp"
    }
    """
    try:
        from datetime import datetime, timedelta

        # Only resume runs that started within the last 30 minutes
        # This prevents picking up stuck/old runs from previous crashes
        time_threshold = datetime.utcnow() - timedelta(minutes=30)

        # Get the most recent non-completed/failed run for this experiment
        latest_run = ExperimentOrchestrationRun.query.filter_by(
            experiment_id=experiment_id
        ).filter(
            ExperimentOrchestrationRun.status.in_(['analyzing', 'recommending', 'reviewing', 'executing', 'synthesizing']),
            ExperimentOrchestrationRun.started_at >= time_threshold
        ).order_by(
            ExperimentOrchestrationRun.started_at.desc()
        ).first()

        if latest_run:
            return jsonify({
                'run_id': str(latest_run.id),
                'status': latest_run.status,
                'current_stage': latest_run.current_stage,
                'started_at': latest_run.started_at.isoformat() if latest_run.started_at else None
            }), 200
        else:
            return jsonify({
                'run_id': None,
                'status': None
            }), 404

    except Exception as e:
        logger.error(f"Error getting latest run for experiment {experiment_id}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@experiments_bp.route('/orchestration/status/<uuid:run_id>', methods=['GET'])
def get_orchestration_status(run_id):
    """
    Get current status of orchestration run

    Returns status, progress, and recommendations when ready
    """
    try:
        run = ExperimentOrchestrationRun.query.get(run_id)
        if not run:
            return jsonify({
                'error': 'Orchestration run not found'
            }), 404

        # Calculate progress percentage
        stage_progress = {
            'analyzing': 20,
            'recommending': 40,
            'reviewing': 50,
            'executing': 70,
            'synthesizing': 90,
            'completed': 100,
            'failed': 0
        }
        progress_percentage = stage_progress.get(run.status, 0)

        response = {
            'run_id': str(run.id),
            'status': run.status,
            'current_stage': run.current_stage or run.status,
            'current_operation': run.current_operation,  # Detailed progress: "Processing doc 3 with extract_entities_spacy (5/21 operations)"
            'progress_percentage': progress_percentage,
            'error_message': run.error_message
        }

        # Add stage completion flags
        response['stage_completed'] = {
            'analyze_experiment': run.experiment_goal is not None,
            'recommend_strategy': run.recommended_strategy is not None,
            'human_review': run.strategy_approved or False,
            'execute_strategy': run.processing_results is not None,
            'synthesize_experiment': run.cross_document_insights is not None
        }

        # If waiting for review, include strategy details
        if run.status == 'reviewing':
            response['awaiting_user_approval'] = True
            response['recommended_strategy'] = run.recommended_strategy
            response['strategy_reasoning'] = run.strategy_reasoning
            response['confidence'] = run.confidence
            response['experiment_goal'] = run.experiment_goal

        # If completed, include summary
        if run.status == 'completed':
            response['completed_at'] = run.completed_at.isoformat() if run.completed_at else None
            response['duration_seconds'] = (
                (run.completed_at - run.started_at).total_seconds()
                if run.completed_at and run.started_at else None
            )

        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Error getting orchestration status for run {run_id}: {e}", exc_info=True)
        return jsonify({
            'error': str(e)
        }), 500
