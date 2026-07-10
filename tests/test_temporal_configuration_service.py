"""Regression coverage for temporal experiment configuration workflows."""

import json
from datetime import date, datetime

import pytest


def _experiment(db_session, user, suffix, experiment_type='temporal_evolution'):
    from app.models.experiment import Experiment

    experiment = Experiment(
        name=f'Temporal Configuration {suffix}',
        experiment_type=experiment_type,
        user_id=user.id,
        status='draft',
        configuration=json.dumps({
            'semantic_events': [{'id': 'preserved-event'}],
            'preserved': {'value': True},
        }),
    )
    db_session.add(experiment)
    db_session.commit()
    return experiment


def _document(db_session, user, suffix, **kwargs):
    from app.models.document import Document

    document = Document(
        title=f'Temporal document {suffix}',
        content='Temporal document content.',
        content_type='text',
        document_type='document',
        status='completed',
        user_id=user.id,
        **kwargs,
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


def _user(db_session, suffix):
    from app.models.user import User

    user = User(
        username=f'temporal-config-{suffix}',
        email=f'temporal-config-{suffix}@example.com',
        password='password',
        account_status='active',
    )
    db_session.add(user)
    db_session.commit()
    return user


def test_temporal_configuration_routes_remain_canonical(app):
    expected = 'app.routes.experiments.temporal.configuration'
    for endpoint in (
        'experiments.update_temporal_terms',
        'experiments.get_temporal_terms',
        'experiments.generate_periods_from_documents',
    ):
        assert app.view_functions[endpoint].__module__ == expected


def test_update_normalizes_and_preserves_configuration(
    db_session, test_user
):
    from app.services.temporal_service import get_temporal_service

    experiment = _experiment(db_session, test_user, 'update')
    get_temporal_service().update_temporal_configuration(
        experiment.id,
        terms=[' agency ', 'Agency', '', 'action'],
        periods=[2000, 1990, 2000],
        temporal_data={
            'period_metadata': {
                '1990': {
                    'boundary_type': 'start',
                    'period_id': 'era-1',
                    'period_name': 'Early Era',
                    'period_description': 'Beginning.',
                },
                '2000': {
                    'boundary_type': 'end',
                    'period_id': 'era-1',
                },
                'invalid': {
                    'boundary_type': 'start',
                    'period_id': 'invalid-era',
                },
            },
            'period_documents': {'1990': []},
        },
        actor_id=test_user.id,
    )

    stored = json.loads(experiment.configuration)
    assert stored['target_terms'] == ['agency', 'action']
    assert stored['time_periods'] == [1990, 2000]
    assert stored['semantic_events'] == [{'id': 'preserved-event'}]
    assert stored['preserved'] == {'value': True}
    assert stored['named_periods'] == [{
        'id': 'era-1',
        'name': 'Early Era',
        'description': 'Beginning.',
        'start_year': 1990,
        'end_year': 2000,
    }]


def test_explicit_named_periods_are_preserved(db_session, test_user):
    from app.services.temporal_service import get_temporal_service

    experiment = _experiment(db_session, test_user, 'named')
    named = [{
        'id': 'explicit',
        'name': 'Explicit Era',
        'start_year': 1980,
        'end_year': 1990,
    }]
    get_temporal_service().update_temporal_configuration(
        experiment.id,
        terms=[],
        periods=[],
        temporal_data={'named_periods': named},
        actor_id=test_user.id,
    )
    assert json.loads(experiment.configuration)['named_periods'] == named


def test_temporal_mutations_require_owner_or_admin(
    db_session, test_user, admin_user
):
    from app.services.base_service import PermissionError
    from app.services.temporal_service import get_temporal_service

    experiment = _experiment(db_session, test_user, 'permissions')
    stranger = _user(db_session, 'stranger')
    service = get_temporal_service()
    with pytest.raises(PermissionError):
        service.update_temporal_configuration(
            experiment.id,
            terms=[],
            periods=[],
            temporal_data={},
            actor_id=stranger.id,
        )
    service.update_temporal_configuration(
        experiment.id,
        terms=['admin update'],
        periods=[2000],
        temporal_data={},
        actor_id=admin_user.id,
    )
    assert json.loads(experiment.configuration)['target_terms'] == ['admin update']


def test_configuration_operations_reject_non_temporal_experiment(
    db_session, test_user
):
    from app.services.base_service import ValidationError
    from app.services.temporal_service import get_temporal_service

    experiment = _experiment(
        db_session,
        test_user,
        'wrong-type',
        experiment_type='entity_extraction',
    )
    service = get_temporal_service()
    with pytest.raises(ValidationError, match='only available for temporal'):
        service.get_temporal_configuration(experiment.id)
    with pytest.raises(ValidationError, match='only available for temporal'):
        service.generate_periods_from_documents(experiment.id, test_user.id)


def test_generate_periods_uses_canonical_latest_documents_and_isolates_experiments(
    db_session, test_user
):
    from app.services.temporal_service import get_temporal_service

    experiment = _experiment(db_session, test_user, 'canonical')
    other = _experiment(db_session, test_user, 'other')
    root = _document(
        db_session,
        test_user,
        'root',
        publication_date=date(1980, 1, 1),
        version_number=1,
        version_type='original',
    )
    latest = _document(
        db_session,
        test_user,
        'latest',
        publication_date=date(2000, 1, 1),
        source_document_id=root.id,
        version_number=2,
        version_type='processed',
    )
    other_document = _document(
        db_session,
        test_user,
        'other-only',
        publication_date=date(2050, 1, 1),
    )
    _link(db_session, experiment, root)
    _link(db_session, experiment, latest)
    _link(db_session, other, other_document)

    result = get_temporal_service().generate_periods_from_documents(
        experiment.id,
        test_user.id,
    )
    stored = json.loads(experiment.configuration)

    assert result['periods'] == [2000]
    assert result['document_count'] == 1
    assert result['date_range'] == {'min_year': 2000, 'max_year': 2000}
    assert stored['period_documents']['2000'][0]['id'] == latest.id
    assert '1980' not in stored['period_documents']
    assert '2050' not in stored['period_documents']
    assert stored['semantic_events'] == [{'id': 'preserved-event'}]


def test_generate_periods_supports_legacy_links_and_upload_date_fallback(
    db_session, test_user
):
    from app.services.temporal_service import get_temporal_service

    experiment = _experiment(db_session, test_user, 'legacy')
    document = _document(
        db_session,
        test_user,
        'legacy-document',
        experiment_id=experiment.id,
        created_at=datetime(2012, 6, 1),
    )
    result = get_temporal_service().generate_periods_from_documents(
        experiment.id,
        test_user.id,
    )
    assert result['periods'] == [2012]
    assert result['using_fallback'] is True
    assert result['source_type'] == 'upload dates'
    stored = json.loads(experiment.configuration)
    assert stored['period_documents']['2012'][0] == {
        'id': document.id,
        'uuid': str(document.uuid),
        'title': document.title,
        'date_source': 'upload_date',
    }


def test_generate_periods_rejects_empty_experiment(db_session, test_user):
    from app.services.base_service import ValidationError
    from app.services.temporal_service import get_temporal_service

    experiment = _experiment(db_session, test_user, 'empty')
    with pytest.raises(ValidationError, match='No documents found'):
        get_temporal_service().generate_periods_from_documents(
            experiment.id,
            test_user.id,
        )


def test_temporal_configuration_route_contracts(
    app, db_session, test_user
):
    experiment = _experiment(db_session, test_user, 'routes')
    document = _document(
        db_session,
        test_user,
        'routes-document',
        publication_date=date(1995, 1, 1),
    )
    _link(db_session, experiment, document)
    client = app.test_client()
    with client.session_transaction() as session:
        session['_user_id'] = str(test_user.id)
        session['_fresh'] = True
    public_get = client.get(
        f'/experiments/{experiment.id}/get_temporal_terms'
    )
    update = client.post(
        f'/experiments/{experiment.id}/update_temporal_terms',
        json={
            'terms': ['agency'],
            'periods': [1990, 2000],
            'temporal_data': {'period_metadata': {}},
        },
    )
    generate = client.post(
        f'/experiments/{experiment.id}/generate_periods_from_documents'
    )
    missing = client.get('/experiments/999999/get_temporal_terms')

    assert public_get.status_code == 200
    assert update.status_code == 200
    assert update.get_json()['success'] is True
    assert generate.status_code == 200
    assert generate.get_json()['periods'] == [1995]
    assert missing.status_code == 404


def test_temporal_configuration_writes_require_authentication(
    app, temporal_experiment
):
    client = app.test_client()
    update = client.post(
        f'/experiments/{temporal_experiment.id}/update_temporal_terms',
        json={},
    )
    generate = client.post(
        f'/experiments/{temporal_experiment.id}/generate_periods_from_documents'
    )
    assert update.status_code == 401
    assert generate.status_code == 401


def test_temporal_routes_map_permission_and_type_errors(
    app, db_session, test_user
):
    stranger = _user(db_session, 'route-stranger')
    experiment = _experiment(db_session, test_user, 'route-permission')
    wrong_type = _experiment(
        db_session,
        stranger,
        'route-wrong-type',
        experiment_type='entity_extraction',
    )
    client = app.test_client()
    with client.session_transaction() as session:
        session['_user_id'] = str(stranger.id)
        session['_fresh'] = True
    forbidden = client.post(
        f'/experiments/{experiment.id}/update_temporal_terms',
        json={},
    )
    invalid_type = client.get(
        f'/experiments/{wrong_type.id}/get_temporal_terms'
    )
    invalid_payload = client.post(
        f'/experiments/{wrong_type.id}/update_temporal_terms',
        json={'periods': [999]},
    )
    assert forbidden.status_code == 403
    assert invalid_type.status_code == 400
    assert invalid_payload.status_code == 400
    assert invalid_payload.get_json()['error'] == 'Validation failed'
