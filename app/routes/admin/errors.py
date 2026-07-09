"""Administrative error-log routes."""

from datetime import datetime, timedelta
import logging

from flask import render_template, request

from app.utils.auth_decorators import admin_required

from . import admin_bp

logger = logging.getLogger(__name__)


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
