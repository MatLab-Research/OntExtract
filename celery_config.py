"""
Celery Configuration for OntExtract

This module creates and configures Celery for background task processing.
Celery provides robust task queue functionality with persistence and monitoring.

IMPORTANT: This module should only be imported when starting the Celery worker,
not when running the Flask app. This prevents blueprint registration issues.
"""
from celery import Celery
import logging

logger = logging.getLogger(__name__)

# Lazy initialization - only create app when needed
_celery_instance = None


def get_celery():
    """
    Get or create Celery instance (lazy initialization).

    This ensures the Flask app is only created when Celery is actually needed,
    preventing blueprint registration issues during Flask startup.

    Returns:
        Celery: Configured Celery instance
    """
    global _celery_instance

    if _celery_instance is None:
        from app import create_app

        app = create_app()

        celery = Celery(
            app.import_name,
            broker='redis://localhost:6379/0',
            backend='redis://localhost:6379/0',
            include=['app.tasks.orchestration']
        )

        # Configure Celery
        celery.conf.update(
            task_serializer='json',
            accept_content=['json'],
            result_serializer='json',
            timezone='UTC',
            enable_utc=True,
            task_track_started=True,
            task_time_limit=3600,  # 1 hour hard limit
            task_soft_time_limit=3000,  # 50 minutes soft limit
            worker_prefetch_multiplier=1,  # One task at a time
            worker_max_tasks_per_child=50,  # Restart worker after 50 tasks
            broker_connection_retry_on_startup=True
        )

        # Set Flask app context for all tasks
        class ContextTask(celery.Task):
            """Base task class that runs in Flask app context."""

            def __call__(self, *args, **kwargs):
                with app.app_context():
                    return self.run(*args, **kwargs)

        celery.Task = ContextTask
        _celery_instance = celery

        logger.info("Celery configured successfully")

    return _celery_instance


# For Celery worker command line: celery -A celery_config.celery worker
celery = get_celery()
