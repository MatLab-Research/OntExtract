"""Orchestration analysis startup routes."""

from flask import request, jsonify
from flask_login import current_user
from app.utils.auth_decorators import api_require_login_for_write
from app.services.base_service import NotFoundError, PermissionError
from app.services.orchestration_read_service import OrchestrationReadService
from app.models.experiment_orchestration_run import ExperimentOrchestrationRun
from app import db
from datetime import datetime
from .. import experiments_bp
from .context import logger


@experiments_bp.route('/<int:experiment_id>/orchestration/analyze', methods=['POST'])
@api_require_login_for_write
def start_llm_orchestration(experiment_id):
    """
    Start LLM orchestration workflow using LangGraph with PostgreSQL checkpointing.

    Background execution with AsyncPostgresSaver - no Celery worker needed.
    State persists in PostgreSQL, survives Flask restarts.
    Always starts fresh - any in-progress runs are marked as failed.

    POST Body:
    {
        "review_choices": true  // Whether to pause for user review
    }

    Returns immediately with run_id. Client polls /orchestration/status/<run_id> for progress.

    Returns:
    {
        "success": true,
        "run_id": "uuid-here",
        "status": "analyzing",
        "message": "Orchestration started with LangGraph checkpointing"
    }
    """
    try:
        OrchestrationReadService.authorized_experiment(
            experiment_id,
            current_user.id,
        )

        # Mark any existing in-progress runs for this experiment as failed
        existing_runs = ExperimentOrchestrationRun.query.filter_by(
            experiment_id=experiment_id
        ).filter(
            ExperimentOrchestrationRun.status.in_(['analyzing', 'recommending', 'reviewing', 'executing', 'synthesizing'])
        ).all()

        for existing_run in existing_runs:
            existing_run.status = 'failed'
            existing_run.error_message = 'Interrupted by new orchestration run'
            existing_run.completed_at = datetime.utcnow()
            logger.info(f"Marked existing run {existing_run.id} as failed (interrupted)")

        db.session.commit()

        # Get user preferences
        data = request.get_json() or {}
        review_choices = data.get('review_choices', True)

        # Create new orchestration run
        run = ExperimentOrchestrationRun(
            experiment_id=experiment_id,
            user_id=current_user.id,
            status='analyzing',
            current_stage='analyzing'
        )
        db.session.add(run)
        db.session.commit()

        logger.info(f"Created orchestration run {run.id} for experiment {experiment_id}")

        # Execute via Celery task (persists in Redis, survives restarts)
        from app.tasks.orchestration import run_orchestration_task
        task = run_orchestration_task.delay(str(run.id), review_choices)

        # Store Celery task ID for monitoring
        run.celery_task_id = task.id
        db.session.commit()

        logger.info(f"Started Celery task {task.id} for orchestration run {run.id}")

        return jsonify({
            'success': True,
            'run_id': str(run.id),
            'status': 'analyzing',
            'current_stage': 'analyzing',
            'message': 'Orchestration started with LangGraph checkpointing. State persists in PostgreSQL.'
        }), 200

    except NotFoundError:
        return jsonify({'success': False, 'error': 'Experiment not found'}), 404
    except PermissionError:
        return jsonify({'success': False, 'error': 'Permission denied'}), 403
    except Exception as e:
        logger.error(f"Error starting orchestration for experiment {experiment_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to start orchestration'
        }), 500
