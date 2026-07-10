"""Regression coverage for the administrative operational error read model."""

from datetime import datetime, timedelta, timezone


def _failed_job(
    db_session,
    user,
    document,
    message,
    created_at,
    **kwargs,
):
    from app.models.processing_job import ProcessingJob

    job = ProcessingJob(
        job_type=kwargs.pop('job_type', 'entity_extraction'),
        job_name=kwargs.pop('job_name', 'Test extraction'),
        status='failed',
        error_message=message,
        retry_count=kwargs.pop('retry_count', 1),
        max_retries=kwargs.pop('max_retries', 3),
        user_id=user.id,
        document_id=document.id,
        created_at=created_at,
        **kwargs,
    )
    job.set_error_details({'reason': message})
    db_session.add(job)
    db_session.commit()
    return job


def _failed_run(db_session, experiment, user, message, started_at):
    from app.models.experiment_orchestration_run import ExperimentOrchestrationRun

    run = ExperimentOrchestrationRun(
        experiment_id=experiment.id,
        user_id=user.id,
        status='failed',
        current_stage='executing',
        error_message=message,
        started_at=started_at,
    )
    db_session.add(run)
    db_session.commit()
    return run


def _decision_and_tool(db_session, user, message, created_at):
    from app.models.orchestration_logs import (
        OrchestrationDecision,
        ToolExecutionLog,
    )

    decision = OrchestrationDecision(
        activity_status='error',
        term_text='agency',
        reasoning_summary=message,
        decision_factors={'stage': 'selection'},
        created_by=user.id,
        created_at=created_at,
    )
    db_session.add(decision)
    db_session.flush()
    tool = ToolExecutionLog(
        orchestration_decision_id=decision.id,
        tool_name='spacy',
        execution_status='error',
        error_message=f'Tool: {message}',
        output_data={'partial': True},
        started_at=created_at + timedelta(minutes=1),
    )
    db_session.add(tool)
    db_session.commit()
    return decision, tool


def test_admin_error_route_remains_canonical(app):
    assert app.view_functions['admin.error_log'].__module__ == (
        'app.routes.admin.errors'
    )


def test_context_aggregates_and_serializes_all_error_sources(
    db_session,
    test_user,
    sample_document,
    temporal_experiment,
):
    from app.services.admin_error_read_service import AdminErrorReadService

    now = datetime(2026, 1, 1, 12, 0, 0)
    job = _failed_job(
        db_session,
        test_user,
        sample_document,
        'Job failed',
        now - timedelta(minutes=4),
    )
    run = _failed_run(
        db_session,
        temporal_experiment,
        test_user,
        'Run failed',
        now - timedelta(minutes=3),
    )
    decision, tool = _decision_and_tool(
        db_session,
        test_user,
        'Decision failed',
        (now - timedelta(minutes=2)).replace(tzinfo=timezone.utc),
    )

    context = AdminErrorReadService(clock=lambda: now).get_context(
        time_filter='24h'
    )
    errors = context['errors']

    assert [error['source'] for error in errors] == [
        'tool_executions',
        'orchestration_decisions',
        'orchestration_runs',
        'processing_jobs',
    ]
    assert errors[0] == {
        'source': 'tool_executions',
        'source_label': 'Tool Execution',
        'id': str(tool.id),
        'timestamp': tool.started_at,
        'error_message': 'Tool: Decision failed',
        'error_details': {'partial': True},
        'context': 'Tool: spacy',
        'user_id': None,
        'retry_count': 0,
        'can_retry': False,
    }
    processing = errors[-1]
    assert processing['id'] == job.id
    assert processing['error_details'] == {'reason': 'Job failed'}
    assert processing['can_retry'] is True
    orchestration = next(
        error for error in errors if error['source'] == 'orchestration_runs'
    )
    assert orchestration['id'] == str(run.id)
    decision_error = next(
        error
        for error in errors
        if error['source'] == 'orchestration_decisions'
    )
    assert decision_error['id'] == str(decision.id)
    assert context['error_counts'] == {
        'processing_jobs': 1,
        'orchestration_runs': 1,
        'orchestration_decisions': 1,
        'tool_executions': 1,
        'total': 4,
    }


def test_source_time_and_search_filters_are_applied_consistently(
    db_session,
    test_user,
    sample_document,
    temporal_experiment,
):
    from app.services.admin_error_read_service import AdminErrorReadService

    now = datetime(2026, 2, 1, 12, 0, 0)
    _failed_job(
        db_session,
        test_user,
        sample_document,
        'needle recent job',
        now - timedelta(minutes=30),
    )
    _failed_job(
        db_session,
        test_user,
        sample_document,
        'needle old job',
        now - timedelta(days=2),
    )
    _failed_run(
        db_session,
        temporal_experiment,
        test_user,
        'needle recent run',
        now - timedelta(minutes=20),
    )
    _decision_and_tool(
        db_session,
        test_user,
        'needle decision',
        (now - timedelta(minutes=10)).replace(tzinfo=timezone.utc),
    )

    from app.models.orchestration_logs import OrchestrationDecision
    assert OrchestrationDecision.query.filter_by(
        activity_status='error'
    ).count() == 1
    assert OrchestrationDecision.query.filter(
        OrchestrationDecision.created_at >= (
            now - timedelta(hours=1)
        ).replace(tzinfo=timezone.utc),
        OrchestrationDecision.reasoning_summary.ilike('%needle%'),
    ).count() == 1

    service = AdminErrorReadService(clock=lambda: now)
    jobs = service.get_context(
        source='processing_jobs',
        time_filter='1h',
        search_query='needle',
    )
    decisions = service.get_context(
        source='orchestration_decisions',
        time_filter='1h',
        search_query='needle',
    )
    tools = service.get_context(
        source='tool_executions',
        time_filter='1h',
        search_query='needle',
    )

    assert [item['error_message'] for item in jobs['errors']] == [
        'needle recent job'
    ]
    assert len(decisions['errors']) == 1
    assert decisions['errors'][0]['source'] == 'orchestration_decisions'
    assert len(tools['errors']) == 1
    assert tools['errors'][0]['source'] == 'tool_executions'
    assert jobs['error_counts']['total'] == 5


def test_invalid_filters_are_normalized(db_session):
    from app.services.admin_error_read_service import AdminErrorReadService

    context = AdminErrorReadService().get_context(
        source='invalid-source',
        time_filter='invalid-window',
        search_query='  trimmed  ',
    )
    assert context['source'] == 'all'
    assert context['time_filter'] == '24h'
    assert context['search_query'] == 'trimmed'


def test_global_result_limit_applies_after_multi_source_merge(
    db_session,
    test_user,
    sample_document,
    temporal_experiment,
):
    from app.services.admin_error_read_service import AdminErrorReadService

    now = datetime(2026, 3, 1, 12, 0, 0)
    _failed_job(
        db_session,
        test_user,
        sample_document,
        'older job',
        now - timedelta(minutes=4),
    )
    newest_job = _failed_job(
        db_session,
        test_user,
        sample_document,
        'newest job',
        now - timedelta(minutes=1),
    )
    _failed_run(
        db_session,
        temporal_experiment,
        test_user,
        'older run',
        now - timedelta(minutes=3),
    )
    newest_run = _failed_run(
        db_session,
        temporal_experiment,
        test_user,
        'newest run',
        now - timedelta(minutes=2),
    )

    errors = AdminErrorReadService(
        clock=lambda: now,
        result_limit=2,
    ).get_context()['errors']
    assert [item['id'] for item in errors] == [newest_job.id, str(newest_run.id)]


def test_optional_sources_can_be_absent_without_query_failure(
    db_session,
    test_user,
    sample_document,
    monkeypatch,
):
    from app.services.admin_error_read_service import AdminErrorReadService

    _failed_job(
        db_session,
        test_user,
        sample_document,
        'Only required source',
        datetime.utcnow(),
    )
    monkeypatch.setattr(
        AdminErrorReadService,
        '_optional_tables',
        staticmethod(lambda: {
            'orchestration_decisions': False,
            'tool_execution_logs': False,
        }),
    )
    context = AdminErrorReadService().get_context(time_filter='all')
    assert [item['source'] for item in context['errors']] == [
        'processing_jobs'
    ]
    assert context['error_counts']['orchestration_decisions'] == 0
    assert context['error_counts']['tool_executions'] == 0


def test_admin_error_route_renders_filters_and_json_details(
    admin_client,
    db_session,
    admin_user,
    sample_document,
):
    _failed_job(
        db_session,
        admin_user,
        sample_document,
        'Visible admin error',
        datetime.utcnow(),
    )
    response = admin_client.get(
        '/admin/errors?source=processing_jobs&time=all&q=Visible'
    )
    assert response.status_code == 200
    assert b'Visible admin error' in response.data
    assert b'Processing Job' in response.data
    assert b'Error Details' in response.data


def test_admin_error_route_requires_admin(auth_client):
    non_admin = auth_client.get('/admin/errors')
    assert non_admin.status_code == 403


def test_admin_error_route_requires_login(app):
    anonymous = app.test_client().get('/admin/errors')
    assert anonymous.status_code == 302
