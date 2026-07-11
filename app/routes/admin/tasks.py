"""Administrative background-task routes."""

import logging

from flask import jsonify, render_template

from app.utils.auth_decorators import admin_required

from . import admin_bp

logger = logging.getLogger(__name__)


@admin_bp.route('/admin/tasks')
@admin_required
def background_tasks():
    """View background task status"""
    from app.models.experiment_orchestration_run import ExperimentOrchestrationRun

    # Get Celery task info
    celery_info = {'active': [], 'reserved': [], 'scheduled': []}

    try:
        from celery_config import get_celery
        celery = get_celery()
        inspect = celery.control.inspect()

        active = inspect.active()
        reserved = inspect.reserved()
        scheduled = inspect.scheduled()

        if active:
            for worker, tasks in active.items():
                for task in tasks:
                    celery_info['active'].append({
                        'worker': worker,
                        'id': task.get('id'),
                        'name': task.get('name'),
                        'args': task.get('args'),
                        'time_start': task.get('time_start')
                    })

        if reserved:
            for worker, tasks in reserved.items():
                for task in tasks:
                    celery_info['reserved'].append({
                        'worker': worker,
                        'id': task.get('id'),
                        'name': task.get('name')
                    })

        if scheduled:
            for worker, tasks in scheduled.items():
                for task in tasks:
                    celery_info['scheduled'].append({
                        'worker': worker,
                        'id': task.get('request', {}).get('id'),
                        'name': task.get('request', {}).get('name'),
                        'eta': task.get('eta')
                    })

    except Exception as e:
        logger.warning(f"Could not inspect Celery: {e}")

    # Get recent orchestration runs (database-tracked tasks)
    recent_runs = ExperimentOrchestrationRun.query.order_by(
        ExperimentOrchestrationRun.started_at.desc()
    ).limit(20).all()

    running_runs = [r for r in recent_runs if r.status in ['analyzing', 'recommending', 'executing', 'synthesizing']]
    completed_runs = [r for r in recent_runs if r.status == 'completed']
    failed_runs = [r for r in recent_runs if r.status == 'failed']

    return render_template('admin/tasks.html',
                         celery_info=celery_info,
                         recent_runs=recent_runs,
                         running_runs=running_runs,
                         completed_runs=completed_runs,
                         failed_runs=failed_runs,
                         active_page='tasks',
                         page_title='Background Tasks')

@admin_bp.route('/admin/api/tasks/<task_id>/cancel', methods=['POST'])
@admin_required
def cancel_task(task_id):
    """Cancel a running Celery task"""
    try:
        from celery_config import get_celery
        celery = get_celery()
        celery.control.revoke(task_id, terminate=True)
        return jsonify({'success': True, 'message': f'Task {task_id} cancelled'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
