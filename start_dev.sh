#!/bin/bash
# Start all OntExtract development services
# Usage: ./start_dev.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================================"
echo "Starting OntExtract Development Environment"
echo "============================================================"

# Check if Redis is running
if ! pgrep -x "redis-server" > /dev/null; then
    echo "Starting Redis..."
    redis-server --daemonize yes
    sleep 1
fi

if pgrep -x "redis-server" > /dev/null; then
    echo "Redis: Running"
else
    echo "Redis: FAILED TO START"
    echo "Install with: sudo apt install redis-server"
    exit 1
fi

# Start Celery worker in background
if pgrep -f "celery.*worker.*ontextract" > /dev/null; then
    echo "Celery Worker: Already running"
else
    echo "Starting Celery worker..."
    ./start_celery_worker.sh &
    sleep 2
    if pgrep -f "celery.*worker.*ontextract" > /dev/null; then
        echo "Celery Worker: Running"
    else
        echo "Celery Worker: FAILED TO START"
        echo "Check /tmp/celery_ontextract.log for errors"
    fi
fi

echo "------------------------------------------------------------"
echo "Starting Flask..."
echo "Celery logs: /tmp/celery_ontextract.log"
echo "============================================================"

# Activate venv and run Flask (foreground)
source venv-ontextract/bin/activate
python run.py
