#!/bin/bash
# Start Flower web UI for Celery monitoring
#
# Usage: ./start_flower.sh
#
# Access Flower UI at: http://localhost:5555
# Monitor tasks, workers, and task history

cd /home/chris/onto/OntExtract
source venv-ontextract/bin/activate

echo "Starting Flower web UI for Celery monitoring..."
echo "Access at: http://localhost:5555"
echo "Log file: /tmp/flower.log"
echo ""

celery -A celery_config.celery flower \
    --port=5555 \
    --logfile=/tmp/flower.log

echo "Flower stopped"
