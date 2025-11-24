#!/bin/bash
# Start Celery worker for LLM orchestration
#
# Usage: ./start_celery_worker.sh
#
# This worker handles background LLM orchestration tasks.
# Tasks survive Flask restarts and can be monitored via Flower UI.

cd /home/chris/onto/OntExtract
source venv-ontextract/bin/activate

# Set environment variables
export FLASK_ENV=production
export FLASK_DEBUG=0

echo "Starting Celery worker for OntExtract LLM orchestration..."
echo "Broker: redis://localhost:6379/0"
echo "Backend: redis://localhost:6379/0"
echo "Log file: /tmp/celery_ontextract.log"
echo ""

# Start worker with logging
celery -A celery_config.celery worker \
    --loglevel=info \
    --logfile=/tmp/celery_ontextract.log \
    --pidfile=/tmp/celery_ontextract.pid \
    --concurrency=2 \
    --pool=prefork \
    --max-tasks-per-child=50 \
    --time-limit=3600 \
    --soft-time-limit=3000

echo "Celery worker stopped"
