"""Regression coverage for orchestration processing and run status."""

from datetime import datetime, timedelta

import pytest


def _experiment(db_session, user, suffix):
    from app.models.experiment import Experiment

    experiment = Experiment(
        name=f'Status Experiment {suffix}',
        experiment_type='temporal_evolution',
        user_id=user.id,
        status='draft',
    )
    db_session.add(experiment)
    db_session.commit()
    return experiment


def _link(db_session, experiment, document):
    from app.models.experiment_document import ExperimentDocument

    association = ExperimentDocument(
        experiment_id=experiment.id,
        document_id=document.id,
    )
    db_session.add(association)
    db_session.commit()
    return association


def _operation(db_session, association, processing_type, status='completed'):
    from app.models.experiment_processing import ExperimentDocumentProcessing

    operation = ExperimentDocumentProcessing(
        experiment_document_id=association.id,
        processing_type=processing_type,
        processing_method='test-method',
        status=status,
    )
    db_session.add(operation)
    db_session.commit()
    return operation


def _run(db_session, experiment, user, status, started_at=None, **kwargs):
    from app.models.experiment_orchestration_run import ExperimentOrchestrationRun

    run = ExperimentOrchestrationRun(
        experiment_id=experiment.id,
        user_id=user.id,
        status=status,
        current_stage=kwargs.pop('current_stage', status),
        started_at=started_at or datetime.utcnow(),
        **kwargs,
    )
    db_session.add(run)
    db_session.commit()
    return run


def test_orchestration_status_routes_remain_canonical(app):
    expected = 'app.routes.experiments.orchestration.status'
    for endpoint in (
        'experiments.check_experiment_processing_status',
        'experiments.get_latest_orchestration_run',
        'experiments.get_orchestration_status',
    ):
        assert app.view_functions[endpoint].__module__ == expected


def test_canonical_processing_status_uses_completed_operation_types(
    db_session, test_user, sample_documents
):
    from app.services.orchestration_status_service import OrchestrationStatusService

    experiment = _experiment(db_session, test_user, 'canonical')
    first = _link(db_session, experiment, sample_documents[0])
    second = _link(db_session, experiment, sample_documents[1])
    _operation(db_session, first, 'segmentation')
    _operation(db_session, first, 'entities')
    _operation(db_session, second, 'embeddings', status='failed')

    payload = OrchestrationStatusService.get_experiment_processing_status(
        experiment.id
    )
    statuses = {item['document_id']: item for item in payload['documents']}
    assert payload['total_documents'] == 2
    assert payload['processed_documents'] == 1
    assert payload['has_partial_processing'] is True
    assert statuses[first.document_id]['processing_types'] == [
        'entities',
        'segmentation',
    ]
    assert statuses[second.document_id]['has_processing'] is False


def test_canonical_processing_is_isolated_for_shared_document(
    db_session, test_user, sample_document
):
    from app.services.orchestration_status_service import OrchestrationStatusService

    owner = _experiment(db_session, test_user, 'owner')
    viewer = _experiment(db_session, test_user, 'viewer')
    owner_link = _link(db_session, owner, sample_document)
    _link(db_session, viewer, sample_document)
    _operation(db_session, owner_link, 'embeddings')

    owner_payload = OrchestrationStatusService.get_experiment_processing_status(
        owner.id
    )
    viewer_payload = OrchestrationStatusService.get_experiment_processing_status(
        viewer.id
    )
    assert owner_payload['processed_documents'] == 1
    assert owner_payload['documents'][0]['processing_types'] == ['embeddings']
    assert viewer_payload['processed_documents'] == 0
    assert viewer_payload['documents'][0]['processing_types'] == []


def test_legacy_status_fallback_uses_completed_segments_and_jobs(
    db_session, test_user, sample_documents
):
    from app.models.processing_job import ProcessingJob
    from app.models.text_segment import TextSegment
    from app.services.orchestration_status_service import OrchestrationStatusService

    experiment = _experiment(db_session, test_user, 'legacy')
    first, second, third = sample_documents[:3]
    for document in (first, second, third):
        document.experiment_id = experiment.id
    db_session.add(TextSegment(
        document_id=first.id,
        content='Legacy segment.',
    ))
    db_session.add(ProcessingJob(
        document_id=second.id,
        user_id=test_user.id,
        job_type='entity_extraction',
        status='completed',
    ))
    db_session.add(ProcessingJob(
        document_id=third.id,
        user_id=test_user.id,
        job_type='generate_embeddings',
        status='failed',
    ))
    db_session.commit()

    payload = OrchestrationStatusService.get_experiment_processing_status(
        experiment.id
    )
    statuses = {item['document_id']: item for item in payload['documents']}
    assert statuses[first.id]['processing_types'] == ['segmentation']
    assert statuses[second.id]['processing_types'] == ['entities']
    assert statuses[third.id]['processing_types'] == []
    assert payload['processed_documents'] == 2
    assert payload['unprocessed_documents'] == 1


def test_latest_active_run_respects_window_status_and_experiment(
    db_session, test_user
):
    from app.services.base_service import NotFoundError
    from app.services.orchestration_status_service import OrchestrationStatusService

    experiment = _experiment(db_session, test_user, 'latest')
    other = _experiment(db_session, test_user, 'latest-other')
    clock = datetime(2026, 1, 1, 12, 0, 0)
    _run(
        db_session,
        experiment,
        test_user,
        'reviewing',
        started_at=clock - timedelta(minutes=31),
    )
    active = _run(
        db_session,
        experiment,
        test_user,
        'executing',
        started_at=clock - timedelta(minutes=5),
    )
    _run(
        db_session,
        experiment,
        test_user,
        'completed',
        started_at=clock - timedelta(minutes=1),
    )
    _run(
        db_session,
        other,
        test_user,
        'analyzing',
        started_at=clock,
    )

    payload = OrchestrationStatusService(clock=lambda: clock).get_latest_active_run(
        experiment.id
    )
    assert payload['run_id'] == str(active.id)
    assert payload['status'] == 'executing'

    empty = _experiment(db_session, test_user, 'latest-empty')
    with pytest.raises(NotFoundError, match='No active orchestration run'):
        OrchestrationStatusService(clock=lambda: clock).get_latest_active_run(
            empty.id
        )
    with pytest.raises(NotFoundError, match='Experiment not found'):
        OrchestrationStatusService(clock=lambda: clock).get_latest_active_run(
            999999
        )


def test_reviewing_run_status_contains_strategy_fields(db_session, test_user):
    from app.services.orchestration_status_service import OrchestrationStatusService

    experiment = _experiment(db_session, test_user, 'reviewing')
    run = _run(
        db_session,
        experiment,
        test_user,
        'reviewing',
        current_stage='reviewing',
        current_operation='Awaiting approval',
        experiment_goal='Analyze semantic change',
        recommended_strategy={'1': ['extract_temporal']},
        strategy_reasoning='Temporal evidence is available.',
        confidence=0.91,
    )

    payload = OrchestrationStatusService.get_run_status(run.id)
    assert payload['progress_percentage'] == 50
    assert payload['current_operation'] == 'Awaiting approval'
    assert payload['awaiting_user_approval'] is True
    assert payload['confidence'] == 0.91
    assert payload['stage_completed'] == {
        'analyze_experiment': True,
        'recommend_strategy': True,
        'human_review': False,
        'execute_strategy': False,
        'synthesize_experiment': False,
    }


def test_completed_run_status_contains_duration(db_session, test_user):
    from app.services.orchestration_status_service import OrchestrationStatusService

    experiment = _experiment(db_session, test_user, 'completed')
    started = datetime(2026, 1, 1, 12, 0, 0)
    run = _run(
        db_session,
        experiment,
        test_user,
        'completed',
        started_at=started,
        completed_at=started + timedelta(seconds=125),
        experiment_goal='Goal',
        recommended_strategy={},
        strategy_approved=True,
        processing_results={},
        cross_document_insights='Insights',
    )

    payload = OrchestrationStatusService.get_run_status(run.id)
    assert payload['progress_percentage'] == 100
    assert payload['duration_seconds'] == 125
    assert payload['completed_at'] == run.completed_at.isoformat()
    assert 'confidence' not in payload
    assert all(payload['stage_completed'].values())


def test_orchestration_status_route_contracts(
    client, db_session, test_user, sample_document
):
    experiment = _experiment(db_session, test_user, 'routes')
    association = _link(db_session, experiment, sample_document)
    _operation(db_session, association, 'segmentation')
    run = _run(db_session, experiment, test_user, 'analyzing')

    check = client.get(
        f'/experiments/{experiment.id}/orchestration/check-status'
    )
    latest = client.get(
        f'/experiments/{experiment.id}/orchestration/latest-run'
    )
    status = client.get(f'/experiments/orchestration/status/{run.id}')
    missing_experiment = client.get(
        '/experiments/999999/orchestration/check-status'
    )
    missing_latest = client.get(
        '/experiments/999999/orchestration/latest-run'
    )

    assert check.status_code == 200
    assert check.get_json()['processed_documents'] == 1
    assert latest.status_code == 200
    assert latest.get_json()['run_id'] == str(run.id)
    assert status.status_code == 200
    assert status.get_json()['status'] == 'analyzing'
    assert missing_experiment.status_code == 404
    assert missing_latest.status_code == 404
    assert missing_latest.get_json()['error'] == 'Experiment not found'
