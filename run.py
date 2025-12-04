#!/usr/bin/env python3
"""
OntExtract Application Runner

This script starts the OntExtract Flask application.
"""

import os
import subprocess
from dotenv import load_dotenv

# Load environment variables from .env BEFORE any app imports
# This ensures API keys are available when services are initialized
load_dotenv()

# Fix for libblis/SpaCy threading crash - must be set before importing any NLP libraries
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('MKL_NUM_THREADS', '1')

from app import create_app

# Expose a module-level Flask app for Gunicorn (run:app)
app = create_app()


def check_redis():
    """Check if Redis is running."""
    try:
        import redis
        from urllib.parse import urlparse

        # Get Redis URL from environment (supports Docker networking)
        redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
        parsed = urlparse(redis_url)
        host = parsed.hostname or 'localhost'
        port = parsed.port or 6379

        r = redis.Redis(host=host, port=port, socket_timeout=1)
        r.ping()
        return True
    except Exception:
        return False


def check_celery_worker():
    """Check if Celery worker is running."""
    try:
        result = subprocess.run(
            ['pgrep', '-f', 'celery.*worker.*ontextract'],
            capture_output=True,
            timeout=2
        )
        return result.returncode == 0
    except Exception:
        return False


def main():
    """Main entry point for the application."""

    # Set environment variables if not already set
    os.environ.setdefault('FLASK_ENV', 'development')
    os.environ.setdefault('FLASK_DEBUG', '1')

    # Use the module-level app
    global app

    # Print startup information
    print("=" * 60)
    print("OntExtract")
    print("=" * 60)

    # Check background services
    redis_ok = check_redis()
    celery_ok = check_celery_worker()

    print(f"Redis: {'Running' if redis_ok else 'NOT RUNNING'}")
    print(f"Celery Worker: {'Running' if celery_ok else 'NOT RUNNING'}")

    if not redis_ok:
        print("  Start Redis with: redis-server")
    if not celery_ok:
        print("  Start Celery with: ./start_celery_worker.sh")
        print("  LLM orchestration will not work without Celery.")

    print("-" * 60)

    # Check API keys
    anthropic_key = bool(os.environ.get('ANTHROPIC_API_KEY'))
    print(f"Anthropic API Key: {'Present' if anthropic_key else 'Missing'}")
    if not anthropic_key:
        print("  LLM orchestration requires ANTHROPIC_API_KEY in .env")

    # Show OED API configuration status
    try:
        oed_enabled = bool(app.config.get('OED_USE_API'))
        app_id_set = bool(app.config.get('OED_APP_ID'))
        key_set = bool(app.config.get('OED_ACCESS_KEY'))
        oed_ready = oed_enabled and app_id_set and key_set
        print(f"OED API: {'Ready' if oed_ready else 'Not configured'}")
    except Exception:
        pass

    print("=" * 60)
    print("http://localhost:8765")
    print("Ctrl+C to stop")
    print("=" * 60)

    # Run the Flask app
    # Note: use_reloader disabled to prevent killing long-running orchestration workflows
    # Enable with FLASK_USE_RELOADER=1 if needed for active development
    use_reloader = os.environ.get('FLASK_USE_RELOADER', '0') == '1'

    app.run(
        host='0.0.0.0',
        port=8765,
        debug=True,
        use_reloader=use_reloader
    )

if __name__ == '__main__':
    main()
