"""
Celery Tasks for LLM Orchestration

This module contains background tasks that run orchestration workflows.
Tasks run in separate worker processes with proper Flask app context.
"""
from celery_config import get_celery
from app import db
from app.models.experiment_orchestration_run import ExperimentOrchestrationRun
from app.services.workflow_executor import get_workflow_executor
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Get Celery instance (lazy initialization)
celery = get_celery()
workflow_executor = get_workflow_executor()


@celery.task(bind=True, name='app.tasks.orchestration.run_orchestration')
def run_orchestration_task(self, run_id: str, review_choices: bool):
    """
    Execute full LLM orchestration workflow in background.

    This task runs in a Celery worker process, completely isolated from Flask.
    Progress updates are written to the database for real-time monitoring.

    Args:
        run_id: UUID of the orchestration run
        review_choices: Whether to pause for human review

    Returns:
        dict: Result summary with status

    Raises:
        Exception: Any unhandled errors are caught, logged, and marked in database
    """
    logger.info(f"[Celery Task {self.request.id}] Starting orchestration for run {run_id}")

    try:
        # Update task ID in database for tracking
        run = ExperimentOrchestrationRun.query.get(run_id)
        if not run:
            raise ValueError(f"Run {run_id} not found")

        # Store Celery task ID for monitoring
        run.celery_task_id = self.request.id
        db.session.commit()

        logger.info(f"[Celery Task {self.request.id}] Executing workflow for run {run_id}")

        # Execute recommendation phase (Stages 1-2: Analyze + Recommend)
        result = workflow_executor.execute_recommendation_phase(
            run_id=run_id,
            review_choices=review_choices
        )

        logger.info(f"[Celery Task {self.request.id}] Recommendation phase completed: {result['status']}")

        # If review not required, continue to processing phase (Stages 4-5: Execute + Synthesize)
        if not review_choices and result['status'] == 'executing':
            logger.info(f"[Celery Task {self.request.id}] Continuing to processing phase (no review required)")

            processing_result = workflow_executor.execute_processing_phase(
                run_id=run_id
            )

            logger.info(f"[Celery Task {self.request.id}] Processing phase completed: {processing_result['status']}")
            result = processing_result  # Use final result

        logger.info(f"[Celery Task {self.request.id}] Orchestration completed: {result['status']}")

        return {
            'success': True,
            'run_id': run_id,
            'status': result['status'],
            'message': f"Orchestration completed with status: {result['status']}"
        }

    except Exception as e:
        logger.error(f"[Celery Task {self.request.id}] Orchestration failed: {e}", exc_info=True)

        # Mark run as failed in database
        try:
            run = ExperimentOrchestrationRun.query.get(run_id)
            if run:
                run.status = 'failed'
                run.error_message = str(e)
                run.completed_at = datetime.utcnow()
                db.session.commit()
                logger.info(f"[Celery Task {self.request.id}] Marked run {run_id} as failed in database")
        except Exception as db_error:
            logger.error(f"[Celery Task {self.request.id}] Failed to mark run as failed: {db_error}", exc_info=True)

        # Re-raise for Celery to mark task as failed
        raise
