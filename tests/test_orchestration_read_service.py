"""Regression coverage for authorized orchestration read boundaries."""

from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest


def _user(db_session, suffix):
    from app.models.user import User

    user = User(
        username=f'orchestration-read-{suffix}',
        email=f'orchestration-read-{suffix}@example.com',
        password='password',
        account_status='active',
    )
    db_session.add(user)
    db_session.commit()
    return user


def _experiment(db_session, user, suffix, configuration=None):
    from app.models.experiment import Experiment

    experiment = Experiment(
        name=f'Orchestration Read {suffix}',
        experiment_type='temporal_evolution',
        user_id=user.id,
        status='draft',
        configuration=configuration or '{}',
    )
    db_session.add(experiment)
    db_session.commit()
    return experiment


def _document(db_session, user, suffix):
    from app.models.document import Document

    document = Document(
        title=f'Orchestration Document {suffix}',
        content='Orchestration document content.',
        content_type='text',
        document_type='document',
        status='completed',
        user_id=user.id,
        version_number=1,
        version_type='original',
    )
    db_session.add(document)
    db_session.commit()
    return document


def _link(db_session, experiment, document):
    from app.models.experiment_document import ExperimentDocument

    association = ExperimentDocument(
        experiment_id=experiment.id,
        document_id=document.id,
    )
    db_session.add(association)
    db_session.commit()
    return association


def _run(db_session, experiment, user, status='completed', **kwargs):
    from app.models.experiment_orchestration_run import ExperimentOrchestrationRun

    started_at = kwargs.pop('started_at', datetime(2026, 1, 1, 12, 0, 0))
    completed_at = kwargs.pop(
        'completed_at',
        started_at + timedelta(seconds=125) if status == 'completed' else None,
    )
    run = ExperimentOrchestrationRun(
        experiment_id=experiment.id,
        user_id=user.id,
        status=status,
        current_stage=status,
        started_at=started_at,
        completed_at=completed_at,
        **kwargs,
    )
    db_session.add(run)
    db_session.commit()
    return run


def _client_for(app, user):
    client = app.test_client()
    with client.session_transaction() as session:
        session['_user_id'] = str(user.id)
        session['_fresh'] = True
    return client


def test_orchestration_read_routes_remain_canonical(app):
    expected = {
        'experiments.llm_orchestration_results': (
            'app.routes.experiments.orchestration.results'
        ),
        'experiments.orchestration_provenance_json': (
            'app.routes.experiments.orchestration.provenance'
        ),
        'experiments.download_llm_provenance': (
            'app.routes.experiments.orchestration.provenance'
        ),
        'experiments.check_experiment_processing_status': (
            'app.routes.experiments.orchestration.status'
        ),
        'experiments.get_latest_orchestration_run': (
            'app.routes.experiments.orchestration.status'
        ),
        'experiments.get_orchestration_status': (
            'app.routes.experiments.orchestration.status'
        ),
        'experiments.orchestration_review_page': (
            'app.routes.experiments.orchestration.review'
        ),
    }
    assert {
        endpoint: app.view_functions[endpoint].__module__
        for endpoint in expected
    } == expected


def test_results_context_uses_canonical_documents_and_normalizes_results(
    db_session, test_user
):
    from app.services.orchestration_read_service import OrchestrationReadService

    experiment = _experiment(
        db_session,
        test_user,
        'context',
        configuration='{"named_periods": [{"name": "Early"}]}',
    )
    first = _document(db_session, test_user, 'first')
    second = _document(db_session, test_user, 'second')
    _link(db_session, experiment, first)
    experiment.documents.append(second)
    db_session.commit()
    run = _run(
        db_session,
        experiment,
        test_user,
        processing_results={
            str(first.id): {
                'extract_entities': {'status': ' Executed ', 'count': 2},
                'extract_temporal': {'count': 1},
            },
            str(second.id): 'malformed-document-results',
            'unknown': {'tool': 'plain result'},
        },
        cross_document_insights=(
            '**Evidence**\n\n<script>alert(1)</script>\n\n'
            '[unsafe](javascript:alert(3))'
        ),
        term_evolution_analysis=(
            '<img src=x onerror=alert(2)> evolution\n\n'
            '![unsafe](data:text/html,boom)'
        ),
    )

    context = OrchestrationReadService.results_context(
        experiment.id,
        run.id,
        test_user.id,
    )
    assert context['document_count'] == 2
    assert set(context['document_lookup']) == {str(first.id), str(second.id)}
    assert context['processing_results'] == {
        str(first.id): {
            'extract_entities': {'status': 'executed', 'count': 2},
            'extract_temporal': {'count': 1, 'status': 'success'},
        },
        'unknown': {
            'tool': {'results': 'plain result', 'status': 'success'},
        },
    }
    assert context['total_operations'] == 3
    assert context['duration'] == {'seconds': 125.0, 'formatted': '2m 5s'}
    assert context['temporal_periods'] == [{'name': 'Early'}]
    assert '<strong>Evidence</strong>' in context['insights_html']
    assert '<script>' not in context['insights_html']
    assert '&lt;script&gt;' in context['insights_html']
    assert 'javascript:' not in context['insights_html']
    assert '<a' not in context['insights_html']
    assert '<img' not in context['evolution_html']
    assert '&lt;img' in context['evolution_html']
    assert 'data:text/html' not in context['evolution_html']


def test_malformed_result_and_configuration_shapes_are_safe(
    db_session, test_user
):
    from app.services.orchestration_read_service import OrchestrationReadService

    experiment = _experiment(
        db_session,
        test_user,
        'malformed',
        configuration='not-json',
    )
    run = _run(
        db_session,
        experiment,
        test_user,
        processing_results=['not', 'a', 'mapping'],
        execution_trace={'not': 'a list'},
        recommended_strategy=['not', 'a', 'mapping'],
    )
    context = OrchestrationReadService.results_context(
        experiment.id,
        run.id,
        test_user.id,
    )
    provenance = OrchestrationReadService.run_provenance(
        experiment.id,
        run.id,
        test_user.id,
    )
    assert context['processing_results'] == {}
    assert context['total_operations'] == 0
    assert context['temporal_periods'] == []
    assert provenance['strategy']['recommended_strategy'] == {}
    assert provenance['execution_trace'] == []


def test_run_pairing_and_actor_authorization(
    db_session, test_user, admin_user
):
    from app.services.base_service import NotFoundError, PermissionError
    from app.services.orchestration_read_service import OrchestrationReadService

    experiment = _experiment(db_session, test_user, 'authorized')
    other = _experiment(db_session, test_user, 'other')
    run = _run(db_session, experiment, test_user)
    stranger = _user(db_session, 'stranger')

    assert OrchestrationReadService.authorized_run(
        run.id,
        test_user.id,
    ) == (experiment, run)
    assert OrchestrationReadService.authorized_run(
        run.id,
        admin_user.id,
    ) == (experiment, run)
    with pytest.raises(PermissionError):
        OrchestrationReadService.authorized_run(run.id, stranger.id)
    with pytest.raises(NotFoundError, match='run not found'):
        OrchestrationReadService.authorized_run(
            run.id,
            test_user.id,
            experiment_id=other.id,
        )


def test_run_provenance_has_stable_bundle_structure(db_session, test_user):
    from app.services.orchestration_read_service import OrchestrationReadService

    experiment = _experiment(db_session, test_user, 'provenance')
    run = _run(
        db_session,
        experiment,
        test_user,
        recommended_strategy={'1': ['extract_entities']},
        modified_strategy={'1': ['extract_temporal']},
        execution_trace=[{'node': 'execute'}],
        cross_document_insights='Insights',
    )
    payload = OrchestrationReadService.run_provenance(
        experiment.id,
        run.id,
        test_user.id,
    )
    assert payload['@type'] == 'prov:Bundle'
    assert payload['experiment']['@id'] == f'experiment:{experiment.id}'
    assert payload['orchestration_run']['@id'] == f'run:{run.id}'
    assert payload['strategy']['recommended_strategy'] == {
        '1': ['extract_entities']
    }
    assert payload['execution_trace'] == [{'node': 'execute'}]


def test_experiment_provenance_authorizes_before_delegate(
    db_session, test_user
):
    from app.services.base_service import PermissionError
    from app.services.orchestration_read_service import OrchestrationReadService

    experiment = _experiment(db_session, test_user, 'delegate')
    stranger = _user(db_session, 'delegate-stranger')
    calls = []
    delegate = SimpleNamespace(
        get_orchestration_provenance=lambda experiment_id: calls.append(
            experiment_id
        ) or {'experiment_id': experiment_id}
    )
    assert OrchestrationReadService.experiment_provenance(
        experiment.id,
        test_user.id,
        delegate,
    ) == {'experiment_id': experiment.id}
    with pytest.raises(PermissionError):
        OrchestrationReadService.experiment_provenance(
            experiment.id,
            stranger.id,
            delegate,
        )
    assert calls == [experiment.id]


def test_private_orchestration_get_routes_require_authentication(
    app, db_session, test_user
):
    experiment = _experiment(db_session, test_user, 'authentication')
    run = _run(db_session, experiment, test_user, status='reviewing')
    client = app.test_client()
    paths = (
        f'/experiments/{experiment.id}/orchestration/llm-results/{run.id}',
        f'/experiments/{experiment.id}/orchestration/llm-provenance/{run.id}',
        f'/experiments/{experiment.id}/orchestration-provenance.json',
        f'/experiments/{experiment.id}/orchestration/check-status',
        f'/experiments/{experiment.id}/orchestration/latest-run',
        f'/experiments/orchestration/status/{run.id}',
        f'/experiments/{experiment.id}/orchestration/review/{run.id}',
    )
    assert all(client.get(path).status_code == 302 for path in paths)


def test_owner_routes_render_and_return_scoped_json(
    app, db_session, test_user
):
    experiment = _experiment(db_session, test_user, 'owner-route')
    document = _document(db_session, test_user, 'owner-route')
    _link(db_session, experiment, document)
    run = _run(
        db_session,
        experiment,
        test_user,
        processing_results={str(document.id): {'tool': {'status': 'success'}}},
        cross_document_insights='Owner insight',
    )
    client = _client_for(app, test_user)
    results = client.get(
        f'/experiments/{experiment.id}/orchestration/llm-results/{run.id}'
    )
    provenance = client.get(
        f'/experiments/{experiment.id}/orchestration/llm-provenance/{run.id}'
    )
    status = client.get(f'/experiments/orchestration/status/{run.id}')
    processing = client.get(
        f'/experiments/{experiment.id}/orchestration/check-status'
    )
    assert results.status_code == 200
    assert b'Owner insight' in results.data
    assert provenance.status_code == 200
    assert provenance.get_json()['@type'] == 'prov:Bundle'
    assert status.status_code == 200
    assert status.get_json()['status'] == 'completed'
    assert processing.status_code == 200


def test_foreign_routes_are_forbidden(
    app, db_session, test_user
):
    owner = _user(db_session, 'foreign-owner')
    experiment = _experiment(db_session, owner, 'foreign')
    run = _run(db_session, experiment, owner, status='reviewing')
    client = _client_for(app, test_user)
    html_paths = (
        f'/experiments/{experiment.id}/orchestration/llm-results/{run.id}',
        f'/experiments/{experiment.id}/orchestration/review/{run.id}',
    )
    json_paths = (
        f'/experiments/{experiment.id}/orchestration/llm-provenance/{run.id}',
        f'/experiments/{experiment.id}/orchestration-provenance.json',
        f'/experiments/{experiment.id}/orchestration/check-status',
        f'/experiments/{experiment.id}/orchestration/latest-run',
        f'/experiments/orchestration/status/{run.id}',
    )
    assert all(client.get(path).status_code == 403 for path in html_paths)
    for path in json_paths:
        response = client.get(path)
        assert response.status_code == 403
        assert response.get_json()['error'] == 'Permission denied'


def test_start_route_rejects_foreign_experiment_before_run_creation(
    app, db_session, test_user
):
    from app.models.experiment_orchestration_run import ExperimentOrchestrationRun

    owner = _user(db_session, 'start-owner')
    experiment = _experiment(db_session, owner, 'start-foreign')
    before = ExperimentOrchestrationRun.query.count()
    response = _client_for(app, test_user).post(
        f'/experiments/{experiment.id}/orchestration/analyze',
        json={'review_choices': True},
    )
    assert response.status_code == 403
    assert response.get_json()['error'] == 'Permission denied'
    assert ExperimentOrchestrationRun.query.count() == before


def test_approval_service_rejects_foreign_reviewer_before_mutation(
    db_session, test_user
):
    from app.services.base_service import PermissionError
    from app.services.orchestration_review_service import OrchestrationApprovalService

    owner = _user(db_session, 'approval-owner')
    experiment = _experiment(db_session, owner, 'approval')
    run = _run(db_session, experiment, owner, status='reviewing')
    with pytest.raises(PermissionError):
        OrchestrationApprovalService.apply_decision(
            run.id,
            {'strategy_approved': False},
            test_user.id,
        )
    db_session.refresh(run)
    assert run.status == 'reviewing'
