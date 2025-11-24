-- Add Celery task ID column for tracking background tasks
-- This allows monitoring Celery tasks from the database
-- Run with: PGPASSWORD=PASS psql -U postgres -h localhost -d ontextract_db -f db_migration/add_celery_task_id.sql

ALTER TABLE experiment_orchestration_runs
ADD COLUMN IF NOT EXISTS celery_task_id VARCHAR(255) NULL;

CREATE INDEX IF NOT EXISTS idx_orchestration_runs_celery_task_id
ON experiment_orchestration_runs(celery_task_id);

COMMENT ON COLUMN experiment_orchestration_runs.celery_task_id IS
'Celery task ID for tracking background orchestration task. NULL for runs before Celery migration.';
