"""Administrative system-health checks and routes."""

import os

from flask import current_app, jsonify, render_template
from sqlalchemy import text

from app import db
from app.utils.auth_decorators import admin_required

from . import admin_bp


def check_database():
    """Check PostgreSQL connectivity"""
    try:
        result = db.session.execute(text('SELECT 1'))
        result.fetchone()
        return {'status': 'ok', 'message': 'Connected'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

def check_redis():
    """Check Redis connectivity"""
    try:
        import redis
        redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
        r = redis.from_url(redis_url)
        if r.ping():
            return {'status': 'ok', 'message': 'Connected'}
        return {'status': 'error', 'message': 'Ping failed'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

def check_celery():
    """Check Celery worker connectivity"""
    try:
        from celery_config import get_celery
        celery = get_celery()
        inspect = celery.control.inspect()
        ping_result = inspect.ping()
        if ping_result:
            workers = list(ping_result.keys())
            return {'status': 'ok', 'message': f'{len(workers)} worker(s): {", ".join(workers)}'}
        return {'status': 'warning', 'message': 'No workers responding'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

def check_disk_space():
    """Check disk space in uploads folder"""
    try:
        from flask import current_app
        uploads_path = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        if not os.path.exists(uploads_path):
            uploads_path = '.'

        statvfs = os.statvfs(uploads_path)
        total_gb = (statvfs.f_frsize * statvfs.f_blocks) / (1024**3)
        free_gb = (statvfs.f_frsize * statvfs.f_bavail) / (1024**3)
        used_percent = ((total_gb - free_gb) / total_gb) * 100

        if used_percent > 90:
            status = 'error'
        elif used_percent > 75:
            status = 'warning'
        else:
            status = 'ok'

        return {
            'status': status,
            'message': f'{free_gb:.1f} GB free of {total_gb:.1f} GB ({used_percent:.0f}% used)'
        }
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

def check_api_keys():
    """Check presence of API keys"""
    keys = {
        'ANTHROPIC_API_KEY': bool(os.environ.get('ANTHROPIC_API_KEY')),
        'OPENAI_API_KEY': bool(os.environ.get('OPENAI_API_KEY')),
    }

    present = sum(keys.values())
    if present == 0:
        return {'status': 'warning', 'message': 'No API keys configured', 'keys': keys}

    return {'status': 'ok', 'message': f'{present} API key(s) configured', 'keys': keys}

@admin_bp.route('/admin/system')
@admin_required
def system_health():
    """View system health status"""
    checks = {
        'database': check_database(),
        'redis': check_redis(),
        'celery': check_celery(),
        'disk_space': check_disk_space(),
        'api_keys': check_api_keys()
    }

    # Calculate overall status
    statuses = [c['status'] for c in checks.values()]
    if 'error' in statuses:
        overall = 'error'
    elif 'warning' in statuses:
        overall = 'warning'
    else:
        overall = 'ok'

    return render_template('admin/system.html',
                         checks=checks,
                         overall_status=overall,
                         active_page='system',
                         page_title='System Health')

@admin_bp.route('/admin/api/health')
@admin_required
def api_health():
    """Quick health check API endpoint"""
    checks = {
        'database': check_database(),
        'redis': check_redis(),
        'celery': check_celery(),
    }
    return jsonify(checks)
