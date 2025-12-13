"""
Admin Routes for OntExtract

User management, system settings, and administrative functions.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import current_user
from app import db
from app.models.user import User
from app.utils.auth_decorators import admin_required
from datetime import datetime, timedelta
from sqlalchemy import text
import os
import logging

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/admin')
@admin_required
def dashboard():
    """Admin dashboard with user statistics"""
    # Get user statistics
    total_users = User.query.count()
    active_users = User.query.filter_by(account_status='active').count()
    suspended_users = User.query.filter_by(account_status='suspended').count()
    admin_users = User.query.filter_by(is_admin=True).count()

    # Get recent users
    recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()

    stats = {
        'total_users': total_users,
        'active_users': active_users,
        'suspended_users': suspended_users,
        'admin_users': admin_users,
        'recent_users': recent_users,
        'active_page': 'dashboard',
        'page_title': 'Dashboard'
    }

    return render_template('admin/dashboard.html', **stats)


@admin_bp.route('/admin/users')
@admin_required
def list_users():
    """List all users with management options"""
    page = request.args.get('page', 1, type=int)
    per_page = 20

    # Filter options
    status_filter = request.args.get('status', 'all')
    role_filter = request.args.get('role', 'all')
    search_query = request.args.get('q', '')

    # Build query
    query = User.query

    if status_filter != 'all':
        query = query.filter_by(account_status=status_filter)

    if role_filter == 'admin':
        query = query.filter_by(is_admin=True)
    elif role_filter == 'user':
        query = query.filter_by(is_admin=False)

    if search_query:
        query = query.filter(
            (User.username.ilike(f'%{search_query}%')) |
            (User.email.ilike(f'%{search_query}%'))
        )

    # Paginate results
    pagination = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return render_template('admin/users.html',
                         users=pagination.items,
                         pagination=pagination,
                         status_filter=status_filter,
                         role_filter=role_filter,
                         search_query=search_query,
                         active_page='users',
                         page_title='User Management')


@admin_bp.route('/admin/users/<int:user_id>')
@admin_required
def view_user(user_id):
    """View detailed user information"""
    user = db.session.get(User, user_id)
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('admin.list_users'))

    # Get user's content counts
    from app.models.experiment import Experiment
    from app.models.document import Document
    from app.models.term import Term

    experiments_count = Experiment.query.filter_by(user_id=user_id).count()
    documents_count = Document.query.filter_by(user_id=user_id).count()
    terms_count = Term.query.filter_by(created_by=user_id).count()

    return render_template('admin/user_detail.html',
                         user=user,
                         experiments_count=experiments_count,
                         documents_count=documents_count,
                         terms_count=terms_count,
                         active_page='users',
                         page_title=f'User: {user.username}')


@admin_bp.route('/admin/users/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    """Edit user role and status"""
    user = db.session.get(User, user_id)
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('admin.list_users'))

    # Prevent editing yourself (safety check)
    if user.id == current_user.id:
        flash('You cannot edit your own account from this interface', 'warning')
        return redirect(url_for('admin.view_user', user_id=user_id))

    if request.method == 'POST':
        # Update role
        is_admin = request.form.get('is_admin') == 'true'
        user.is_admin = is_admin

        # Update status
        account_status = request.form.get('account_status')
        if account_status in ['active', 'suspended']:
            user.account_status = account_status
            # Sync is_active with account_status
            user.is_active = (account_status == 'active')

        db.session.commit()
        flash(f'User {user.username} updated successfully', 'success')
        return redirect(url_for('admin.view_user', user_id=user_id))

    return render_template('admin/edit_user.html',
                         user=user,
                         active_page='users',
                         page_title=f'Edit User: {user.username}')


@admin_bp.route('/admin/users/<int:user_id>/set-password', methods=['POST'])
@admin_required
def set_user_password(user_id):
    """Set password for a user (admin only - for demo purposes)"""
    user = db.session.get(User, user_id)
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('admin.list_users'))

    # Prevent setting your own password (use normal password change)
    if user.id == current_user.id:
        flash('You cannot set your own password from this interface. Use the password change feature.', 'warning')
        return redirect(url_for('admin.view_user', user_id=user_id))

    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')

    # Validate passwords
    if not new_password or len(new_password) < 6:
        flash('Password must be at least 6 characters long', 'error')
        return redirect(url_for('admin.view_user', user_id=user_id))

    if new_password != confirm_password:
        flash('Passwords do not match', 'error')
        return redirect(url_for('admin.view_user', user_id=user_id))

    # Set the new password
    user.set_password(new_password)
    db.session.commit()

    flash(f'Password set successfully for user {user.username}', 'success')
    return redirect(url_for('admin.view_user', user_id=user_id))


@admin_bp.route('/admin/users/<int:user_id>/toggle-admin', methods=['POST'])
@admin_required
def toggle_admin(user_id):
    """Toggle user admin status (AJAX)"""
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    # Prevent removing your own admin status
    if user.id == current_user.id:
        return jsonify({'error': 'Cannot modify your own admin status'}), 400

    user.is_admin = not user.is_admin
    db.session.commit()

    return jsonify({
        'success': True,
        'is_admin': user.is_admin,
        'username': user.username
    })


@admin_bp.route('/admin/users/<int:user_id>/suspend', methods=['POST'])
@admin_required
def suspend_user(user_id):
    """Suspend user account"""
    user = db.session.get(User, user_id)
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('admin.list_users'))

    if user.id == current_user.id:
        flash('You cannot suspend your own account', 'error')
        return redirect(url_for('admin.view_user', user_id=user_id))

    user.account_status = 'suspended'
    user.is_active = False
    db.session.commit()

    flash(f'User {user.username} has been suspended', 'success')
    return redirect(url_for('admin.view_user', user_id=user_id))


@admin_bp.route('/admin/users/<int:user_id>/activate', methods=['POST'])
@admin_required
def activate_user(user_id):
    """Activate suspended user account"""
    user = db.session.get(User, user_id)
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('admin.list_users'))

    user.account_status = 'active'
    user.is_active = True
    db.session.commit()

    flash(f'User {user.username} has been activated', 'success')
    return redirect(url_for('admin.view_user', user_id=user_id))


@admin_bp.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    """Delete user and all their content"""
    user = db.session.get(User, user_id)
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('admin.list_users'))

    if user.id == current_user.id:
        flash('You cannot delete your own account', 'error')
        return redirect(url_for('admin.view_user', user_id=user_id))

    username = user.username

    try:
        # Delete user (cascade will handle related content)
        db.session.delete(user)
        db.session.commit()

        flash(f'User {username} and all their content have been deleted', 'success')
        return redirect(url_for('admin.list_users'))

    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting user: {str(e)}', 'error')
        return redirect(url_for('admin.view_user', user_id=user_id))


@admin_bp.route('/admin/make-admin/<username>', methods=['POST'])
@admin_required
def make_admin(username):
    """Quick route to make a user admin (for manual setup)"""
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    user.is_admin = True
    db.session.commit()

    return jsonify({
        'success': True,
        'message': f'{username} is now an admin',
        'username': username
    })


# ============================================================================
# Error Log Routes
# ============================================================================

def get_error_counts():
    """Get counts of errors from all sources"""
    from app.models.processing_job import ProcessingJob
    from app.models.experiment_orchestration_run import ExperimentOrchestrationRun

    counts = {
        'processing_jobs': ProcessingJob.query.filter_by(status='failed').count(),
        'orchestration_runs': ExperimentOrchestrationRun.query.filter_by(status='failed').count(),
        'total': 0
    }

    # Check if orchestration_decisions table exists and has error column
    try:
        from app.models.orchestration_logs import OrchestrationDecision, ToolExecutionLog
        counts['orchestration_decisions'] = OrchestrationDecision.query.filter_by(activity_status='error').count()
        counts['tool_executions'] = ToolExecutionLog.query.filter_by(execution_status='error').count()
    except Exception:
        counts['orchestration_decisions'] = 0
        counts['tool_executions'] = 0

    counts['total'] = sum([
        counts['processing_jobs'],
        counts['orchestration_runs'],
        counts['orchestration_decisions'],
        counts['tool_executions']
    ])

    return counts


@admin_bp.route('/admin/errors')
@admin_required
def error_log():
    """View application error log from multiple sources"""
    from app.models.processing_job import ProcessingJob
    from app.models.experiment_orchestration_run import ExperimentOrchestrationRun

    # Get filter parameters
    source = request.args.get('source', 'all')
    time_filter = request.args.get('time', '24h')
    search_query = request.args.get('q', '')

    # Calculate time cutoff
    now = datetime.utcnow()
    if time_filter == '1h':
        cutoff = now - timedelta(hours=1)
    elif time_filter == '24h':
        cutoff = now - timedelta(hours=24)
    elif time_filter == '7d':
        cutoff = now - timedelta(days=7)
    elif time_filter == '30d':
        cutoff = now - timedelta(days=30)
    else:
        cutoff = None  # All time

    errors = []

    # Processing Jobs
    if source in ['all', 'processing_jobs']:
        query = ProcessingJob.query.filter_by(status='failed')
        if cutoff:
            query = query.filter(ProcessingJob.created_at >= cutoff)
        if search_query:
            query = query.filter(ProcessingJob.error_message.ilike(f'%{search_query}%'))

        for job in query.order_by(ProcessingJob.created_at.desc()).limit(100).all():
            errors.append({
                'source': 'processing_jobs',
                'source_label': 'Processing Job',
                'id': job.id,
                'timestamp': job.created_at,
                'error_message': job.error_message or 'No error message',
                'error_details': job.get_error_details(),
                'context': f'{job.job_type} - {job.job_name or "unnamed"}',
                'user_id': job.user_id,
                'retry_count': job.retry_count,
                'can_retry': job.can_retry()
            })

    # Orchestration Runs
    if source in ['all', 'orchestration_runs']:
        query = ExperimentOrchestrationRun.query.filter_by(status='failed')
        if cutoff:
            query = query.filter(ExperimentOrchestrationRun.started_at >= cutoff)
        if search_query:
            query = query.filter(ExperimentOrchestrationRun.error_message.ilike(f'%{search_query}%'))

        for run in query.order_by(ExperimentOrchestrationRun.started_at.desc()).limit(100).all():
            errors.append({
                'source': 'orchestration_runs',
                'source_label': 'Orchestration Run',
                'id': str(run.id),
                'timestamp': run.started_at,
                'error_message': run.error_message or 'No error message',
                'error_details': None,
                'context': f'Experiment {run.experiment_id} - Stage: {run.current_stage or "unknown"}',
                'user_id': run.user_id,
                'retry_count': 0,
                'can_retry': False
            })

    # Orchestration Decisions
    if source in ['all', 'orchestration_decisions']:
        try:
            from app.models.orchestration_logs import OrchestrationDecision
            query = OrchestrationDecision.query.filter_by(activity_status='error')
            if cutoff:
                query = query.filter(OrchestrationDecision.created_at >= cutoff)

            for decision in query.order_by(OrchestrationDecision.created_at.desc()).limit(100).all():
                errors.append({
                    'source': 'orchestration_decisions',
                    'source_label': 'Orchestration Decision',
                    'id': str(decision.id),
                    'timestamp': decision.created_at,
                    'error_message': decision.reasoning_summary or 'Decision failed',
                    'error_details': decision.decision_factors,
                    'context': f'Term: {decision.term_text or "unknown"}',
                    'user_id': decision.created_by,
                    'retry_count': 0,
                    'can_retry': False
                })
        except Exception as e:
            logger.debug(f"Could not query orchestration_decisions: {e}")

    # Tool Execution Logs
    if source in ['all', 'tool_executions']:
        try:
            from app.models.orchestration_logs import ToolExecutionLog
            query = ToolExecutionLog.query.filter_by(execution_status='error')
            if cutoff:
                query = query.filter(ToolExecutionLog.started_at >= cutoff)
            if search_query:
                query = query.filter(ToolExecutionLog.error_message.ilike(f'%{search_query}%'))

            for log in query.order_by(ToolExecutionLog.started_at.desc()).limit(100).all():
                errors.append({
                    'source': 'tool_executions',
                    'source_label': 'Tool Execution',
                    'id': str(log.id),
                    'timestamp': log.started_at,
                    'error_message': log.error_message or 'Tool execution failed',
                    'error_details': log.output_data,
                    'context': f'Tool: {log.tool_name}',
                    'user_id': None,
                    'retry_count': 0,
                    'can_retry': False
                })
        except Exception as e:
            logger.debug(f"Could not query tool_execution_logs: {e}")

    # Sort all errors by timestamp descending
    errors.sort(key=lambda x: x['timestamp'] or datetime.min, reverse=True)

    # Get error counts for badges
    error_counts = get_error_counts()

    return render_template('admin/errors.html',
                         errors=errors,
                         error_counts=error_counts,
                         source=source,
                         time_filter=time_filter,
                         search_query=search_query,
                         active_page='errors',
                         page_title='Error Log')


# ============================================================================
# System Health Routes
# ============================================================================

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


# ============================================================================
# Background Tasks Routes
# ============================================================================

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


# ============================================================================
# Data Management Routes
# ============================================================================

@admin_bp.route('/admin/data')
@admin_required
def data_management():
    """View data statistics and management options"""
    from app.models.experiment import Experiment
    from app.models.document import Document
    from app.models.processing_job import ProcessingJob
    from app.models.term import Term

    # Experiment stats
    experiment_stats = {
        'total': Experiment.query.count(),
        'draft': Experiment.query.filter_by(status='draft').count(),
        'running': Experiment.query.filter_by(status='running').count(),
        'completed': Experiment.query.filter_by(status='completed').count(),
        'error': Experiment.query.filter_by(status='error').count()
    }

    # Document stats
    document_stats = {
        'total': Document.query.count(),
        'uploaded': Document.query.filter_by(status='uploaded').count(),
        'processing': Document.query.filter_by(status='processing').count(),
        'completed': Document.query.filter_by(status='completed').count(),
        'error': Document.query.filter_by(status='error').count(),
        'orphaned': Document.query.filter(
            ~Document.experiments.any()
        ).count()  # Documents not in any experiment
    }

    # Processing job stats
    job_stats = {
        'total': ProcessingJob.query.count(),
        'pending': ProcessingJob.query.filter_by(status='pending').count(),
        'running': ProcessingJob.query.filter_by(status='running').count(),
        'completed': ProcessingJob.query.filter_by(status='completed').count(),
        'failed': ProcessingJob.query.filter_by(status='failed').count()
    }

    # Term stats
    term_stats = {
        'total': Term.query.count()
    }

    # Storage stats
    storage_stats = check_disk_space()

    return render_template('admin/data.html',
                         experiment_stats=experiment_stats,
                         document_stats=document_stats,
                         job_stats=job_stats,
                         term_stats=term_stats,
                         storage_stats=storage_stats,
                         active_page='data',
                         page_title='Data Management')


@admin_bp.route('/admin/api/data/cleanup-jobs', methods=['POST'])
@admin_required
def cleanup_failed_jobs():
    """Delete all failed processing jobs"""
    from app.models.processing_job import ProcessingJob

    try:
        count = ProcessingJob.query.filter_by(status='failed').delete()
        db.session.commit()
        return jsonify({'success': True, 'deleted': count})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/admin/api/data/cleanup-drafts', methods=['POST'])
@admin_required
def cleanup_draft_experiments():
    """Delete all draft experiments older than 30 days"""
    from app.models.experiment import Experiment

    try:
        cutoff = datetime.utcnow() - timedelta(days=30)
        count = Experiment.query.filter(
            Experiment.status == 'draft',
            Experiment.created_at < cutoff
        ).delete()
        db.session.commit()
        return jsonify({'success': True, 'deleted': count})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
