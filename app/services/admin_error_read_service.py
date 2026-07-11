"""Administrative read model for failed processing and orchestration records."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import inspect

from app import db
from app.models.experiment_orchestration_run import ExperimentOrchestrationRun
from app.models.processing_job import ProcessingJob


class AdminErrorReadService:
    """Aggregate failed records from operational data sources."""

    SOURCES = {
        'all',
        'processing_jobs',
        'orchestration_runs',
        'orchestration_decisions',
        'tool_executions',
    }
    TIME_WINDOWS = {
        '1h': timedelta(hours=1),
        '24h': timedelta(hours=24),
        '7d': timedelta(days=7),
        '30d': timedelta(days=30),
        'all': None,
    }

    def __init__(self, clock=None, result_limit=100):
        self.clock = clock or datetime.utcnow
        self.result_limit = max(1, min(int(result_limit), 500))

    def get_context(self, source='all', time_filter='24h', search_query=''):
        source = source if source in self.SOURCES else 'all'
        time_filter = (
            time_filter if time_filter in self.TIME_WINDOWS else '24h'
        )
        search_query = search_query.strip() if search_query else ''
        window = self.TIME_WINDOWS[time_filter]
        cutoff = self.clock() - window if window else None
        available = self._optional_tables()

        errors = []
        if source in ('all', 'processing_jobs'):
            errors.extend(self._processing_jobs(cutoff, search_query))
        if source in ('all', 'orchestration_runs'):
            errors.extend(self._orchestration_runs(cutoff, search_query))
        if (
            source in ('all', 'orchestration_decisions')
            and available['orchestration_decisions']
        ):
            errors.extend(self._orchestration_decisions(cutoff, search_query))
        if (
            source in ('all', 'tool_executions')
            and available['tool_execution_logs']
        ):
            errors.extend(self._tool_executions(cutoff, search_query))
        errors.sort(key=self._timestamp_key, reverse=True)

        counts = self._counts(available)
        return {
            'errors': errors[:self.result_limit],
            'error_counts': counts,
            'source': source,
            'time_filter': time_filter,
            'search_query': search_query,
            'active_page': 'errors',
            'page_title': 'Error Log',
        }

    def _processing_jobs(self, cutoff, search_query):
        query = ProcessingJob.query.filter_by(status='failed')
        if cutoff:
            query = query.filter(ProcessingJob.created_at >= cutoff)
        if search_query:
            query = query.filter(
                ProcessingJob.error_message.ilike(f'%{search_query}%')
            )
        jobs = query.order_by(ProcessingJob.created_at.desc()).limit(
            self.result_limit
        ).all()
        return [
            {
                'source': 'processing_jobs',
                'source_label': 'Processing Job',
                'id': job.id,
                'timestamp': job.created_at,
                'error_message': job.error_message or 'No error message',
                'error_details': job.get_error_details(),
                'context': f'{job.job_type} - {job.job_name or "unnamed"}',
                'user_id': job.user_id,
                'retry_count': job.retry_count,
                'can_retry': job.can_retry(),
            }
            for job in jobs
        ]

    def _orchestration_runs(self, cutoff, search_query):
        query = ExperimentOrchestrationRun.query.filter_by(status='failed')
        if cutoff:
            query = query.filter(
                ExperimentOrchestrationRun.started_at >= cutoff
            )
        if search_query:
            query = query.filter(
                ExperimentOrchestrationRun.error_message.ilike(
                    f'%{search_query}%'
                )
            )
        runs = query.order_by(
            ExperimentOrchestrationRun.started_at.desc()
        ).limit(self.result_limit).all()
        return [
            {
                'source': 'orchestration_runs',
                'source_label': 'Orchestration Run',
                'id': str(run.id),
                'timestamp': run.started_at,
                'error_message': run.error_message or 'No error message',
                'error_details': None,
                'context': (
                    f'Experiment {run.experiment_id} - Stage: '
                    f'{run.current_stage or "unknown"}'
                ),
                'user_id': run.user_id,
                'retry_count': 0,
                'can_retry': False,
            }
            for run in runs
        ]

    def _orchestration_decisions(self, cutoff, search_query):
        from app.models.orchestration_logs import OrchestrationDecision

        query = OrchestrationDecision.query.filter_by(activity_status='error')
        if cutoff:
            query = query.filter(
                OrchestrationDecision.created_at >= self._utc_aware(cutoff)
            )
        if search_query:
            query = query.filter(
                OrchestrationDecision.reasoning_summary.ilike(
                    f'%{search_query}%'
                )
            )
        decisions = query.order_by(
            OrchestrationDecision.created_at.desc()
        ).limit(self.result_limit).all()
        return [
            {
                'source': 'orchestration_decisions',
                'source_label': 'Orchestration Decision',
                'id': str(decision.id),
                'timestamp': decision.created_at,
                'error_message': (
                    decision.reasoning_summary or 'Decision failed'
                ),
                'error_details': decision.decision_factors,
                'context': f'Term: {decision.term_text or "unknown"}',
                'user_id': decision.created_by,
                'retry_count': 0,
                'can_retry': False,
            }
            for decision in decisions
        ]

    def _tool_executions(self, cutoff, search_query):
        from app.models.orchestration_logs import ToolExecutionLog

        query = ToolExecutionLog.query.filter_by(execution_status='error')
        if cutoff:
            query = query.filter(
                ToolExecutionLog.started_at >= self._utc_aware(cutoff)
            )
        if search_query:
            query = query.filter(
                ToolExecutionLog.error_message.ilike(f'%{search_query}%')
            )
        logs = query.order_by(ToolExecutionLog.started_at.desc()).limit(
            self.result_limit
        ).all()
        return [
            {
                'source': 'tool_executions',
                'source_label': 'Tool Execution',
                'id': str(log.id),
                'timestamp': log.started_at,
                'error_message': log.error_message or 'Tool execution failed',
                'error_details': log.output_data,
                'context': f'Tool: {log.tool_name}',
                'user_id': None,
                'retry_count': 0,
                'can_retry': False,
            }
            for log in logs
        ]

    @staticmethod
    def _counts(available):
        counts = {
            'processing_jobs': ProcessingJob.query.filter_by(
                status='failed'
            ).count(),
            'orchestration_runs': ExperimentOrchestrationRun.query.filter_by(
                status='failed'
            ).count(),
            'orchestration_decisions': 0,
            'tool_executions': 0,
        }
        if available['orchestration_decisions']:
            from app.models.orchestration_logs import OrchestrationDecision

            counts['orchestration_decisions'] = (
                OrchestrationDecision.query.filter_by(
                    activity_status='error'
                ).count()
            )
        if available['tool_execution_logs']:
            from app.models.orchestration_logs import ToolExecutionLog

            counts['tool_executions'] = ToolExecutionLog.query.filter_by(
                execution_status='error'
            ).count()
        counts['total'] = sum(counts.values())
        return counts

    @staticmethod
    def _optional_tables():
        inspector = inspect(db.engine)
        return {
            'orchestration_decisions': inspector.has_table(
                'orchestration_decisions'
            ),
            'tool_execution_logs': inspector.has_table('tool_execution_logs'),
        }

    @staticmethod
    def _timestamp_key(error):
        value = error.get('timestamp')
        if not value:
            return float('-inf')
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.timestamp()

    @staticmethod
    def _utc_aware(value):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
