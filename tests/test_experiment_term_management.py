"""Regression coverage for domain-comparison experiment term management."""

import json
from types import SimpleNamespace

import pytest


def _domain_experiment(db_session, user, suffix='terms'):
    from app.models.experiment import Experiment

    experiment = Experiment(
        name=f'Domain Experiment {suffix}',
        description='Compare terminology across domains.',
        experiment_type='domain_comparison',
        user_id=user.id,
        status='draft',
        configuration=json.dumps({
            'target_terms': ['agent'],
            'domains': ['Philosophy', 'Computer Science'],
            'preserved': {'value': True},
        }),
    )
    db_session.add(experiment)
    db_session.commit()
    return experiment


def _user(db_session, suffix):
    from app.models.user import User

    user = User(
        username=f'term-manager-{suffix}',
        email=f'term-manager-{suffix}@example.com',
        password='password',
        account_status='active',
    )
    db_session.add(user)
    db_session.commit()
    return user


def test_experiment_term_routes_remain_canonical(app):
    expected = 'app.routes.experiments.terms'
    for endpoint in (
        'experiments.manage_terms',
        'experiments.update_terms',
        'experiments.get_terms',
        'experiments.fetch_definitions',
    ):
        assert app.view_functions[endpoint].__module__ == expected


def test_get_term_configuration_and_default_domains(db_session, test_user):
    from app.services.term_service import get_term_service

    experiment = _domain_experiment(db_session, test_user, 'configuration')
    config = get_term_service().get_term_configuration(experiment.id)
    assert config['terms'] == ['agent']
    assert config['domains'] == ['Philosophy', 'Computer Science']
    assert config['definitions'] == {}

    experiment.configuration = json.dumps({'target_terms': ['agency']})
    db_session.commit()
    defaults = get_term_service().get_term_configuration(experiment.id)
    assert defaults['domains'] == ['Computer Science', 'Philosophy', 'Law']


def test_parse_configuration_tolerates_dictionary():
    from app.services.term_service import get_term_service

    experiment = SimpleNamespace(
        id=42,
        configuration={'target_terms': ['agency'], 'domains': ['Law']},
    )
    parsed = get_term_service()._parse_configuration(experiment)
    assert parsed == {'target_terms': ['agency'], 'domains': ['Law']}
    assert parsed is not experiment.configuration


def test_update_terms_normalizes_and_preserves_configuration(
    db_session, test_user
):
    from app.services.term_service import get_term_service

    experiment = _domain_experiment(db_session, test_user, 'update')
    get_term_service().update_term_configuration(
        experiment.id,
        terms=[' agent ', 'agency', 'agent'],
        domains=[' Law ', 'Philosophy', 'Law'],
        definitions={'agent': {'Law': {'text': 'A legal actor.'}}},
        actor_id=test_user.id,
    )
    stored = json.loads(experiment.configuration)
    assert stored['target_terms'] == ['agent', 'agency']
    assert stored['domains'] == ['Law', 'Philosophy']
    assert stored['term_definitions']['agent']['Law']['text'] == 'A legal actor.'
    assert stored['preserved'] == {'value': True}


@pytest.mark.parametrize(
    ('terms', 'domains', 'message'),
    [
        (['agent', ' '], ['Law'], 'Terms cannot contain blank values'),
        (['agent'], ['Law', 3], 'All domains must be strings'),
    ],
)
def test_update_terms_rejects_invalid_items(
    db_session, test_user, terms, domains, message
):
    from app.services.base_service import ValidationError
    from app.services.term_service import get_term_service

    experiment = _domain_experiment(db_session, test_user, f'invalid-{len(message)}')
    with pytest.raises(ValidationError, match=message):
        get_term_service().update_term_configuration(
            experiment.id,
            terms=terms,
            domains=domains,
            actor_id=test_user.id,
        )


def test_term_mutations_require_owner_or_admin(
    db_session, test_user, admin_user
):
    from app.services.base_service import PermissionError
    from app.services.term_service import get_term_service

    experiment = _domain_experiment(db_session, test_user, 'permissions')
    stranger = _user(db_session, 'stranger')
    with pytest.raises(PermissionError):
        get_term_service().update_term_configuration(
            experiment.id,
            ['agent'],
            ['Law'],
            actor_id=stranger.id,
        )
    with pytest.raises(PermissionError):
        get_term_service().fetch_definitions(
            experiment.id,
            'agent',
            ['Law'],
            actor_id=stranger.id,
        )

    updated = get_term_service().update_term_configuration(
        experiment.id,
        ['agency'],
        ['Law'],
        actor_id=admin_user.id,
    )
    assert json.loads(updated.configuration)['target_terms'] == ['agency']


def test_fetch_definitions_uses_references_and_ontology_mapping(
    db_session, test_user, sample_document
):
    from app.services.term_service import get_term_service

    experiment = _domain_experiment(db_session, test_user, 'definitions')
    sample_document.document_type = 'reference'
    sample_document.title = 'Agency Reference'
    sample_document.content = (
        'Introduction\n'
        'An agent is an entity responsible for an activity.\n'
        'Further discussion.'
    )
    experiment.references.append(sample_document)
    db_session.commit()

    result = get_term_service().fetch_definitions(
        experiment.id,
        ' agent ',
        [' Philosophy ', 'Philosophy'],
        actor_id=test_user.id,
    )

    assert list(result['definitions']) == ['Philosophy']
    assert 'agent is an entity' in result['definitions']['Philosophy']['text'].lower()
    assert result['definitions']['Philosophy']['source']
    assert result['ontology_mappings']['Philosophy'][0]['label'] == 'prov:Agent'


def test_manage_terms_and_get_terms_are_public(
    client, db_session, test_user
):
    experiment = _domain_experiment(db_session, test_user, 'public')

    page = client.get(f'/experiments/{experiment.id}/manage_terms')
    api = client.get(f'/experiments/{experiment.id}/get_terms')

    assert page.status_code == 200
    assert b'Manage Terms' in page.data
    assert api.status_code == 200
    assert api.get_json()['terms'] == ['agent']


def test_update_and_fetch_routes_persist_for_owner(
    auth_client, db_session, test_user, sample_document
):
    experiment = _domain_experiment(db_session, test_user, 'routes')
    sample_document.document_type = 'reference'
    sample_document.content = 'Agent means a responsible actor.'
    experiment.references.append(sample_document)
    db_session.commit()

    update = auth_client.post(
        f'/experiments/{experiment.id}/update_terms',
        json={
            'terms': ['agent', 'agency'],
            'domains': ['Philosophy'],
            'definitions': {},
        },
    )
    fetched = auth_client.post(
        f'/experiments/{experiment.id}/fetch_definitions',
        json={'term': 'agent', 'domains': ['Philosophy']},
    )

    assert update.status_code == 200
    assert update.get_json()['success'] is True
    assert fetched.status_code == 200
    assert fetched.get_json()['success'] is True
    assert 'Philosophy' in fetched.get_json()['definitions']


def test_term_routes_enforce_ownership_and_validation(
    app, db_session, test_user
):
    experiment = _domain_experiment(db_session, test_user, 'errors')
    stranger = _user(db_session, 'route-stranger')
    stranger_client = _authenticated_client(app, stranger)
    forbidden_update = stranger_client.post(
        f'/experiments/{experiment.id}/update_terms',
        json={'terms': ['agent'], 'domains': ['Law']},
    )
    forbidden_fetch = stranger_client.post(
        f'/experiments/{experiment.id}/fetch_definitions',
        json={'term': 'agent', 'domains': ['Law']},
    )

    invalid = _authenticated_client(app, test_user).post(
        f'/experiments/{experiment.id}/fetch_definitions',
        json={'term': '', 'domains': []},
    )
    missing = app.test_client().get('/experiments/999999/get_terms')

    assert forbidden_update.status_code == 403
    assert forbidden_fetch.status_code == 403
    assert invalid.status_code == 400
    assert invalid.get_json()['error'] == 'Validation failed'
    assert missing.status_code == 404


def test_term_route_validation_details_are_json_serializable(
    auth_client, db_session, test_user
):
    experiment = _domain_experiment(db_session, test_user, 'json-validation')
    response = auth_client.post(
        f'/experiments/{experiment.id}/fetch_definitions',
        json={'term': '', 'domains': []},
    )

    assert response.status_code == 400
    payload = response.get_json()
    assert payload['error'] == 'Validation failed'
    assert isinstance(payload['details'], list)
    assert json.loads(json.dumps(payload['details'])) == payload['details']


def test_term_write_routes_require_authentication(
    app, db_session, test_user
):
    experiment = _domain_experiment(db_session, test_user, 'authentication')
    client = app.test_client()

    update = client.post(
        f'/experiments/{experiment.id}/update_terms',
        json={'terms': [], 'domains': []},
    )
    fetch = client.post(
        f'/experiments/{experiment.id}/fetch_definitions',
        json={'term': 'agent', 'domains': ['Law']},
    )

    assert update.status_code == 401
    assert fetch.status_code == 401


def _authenticated_client(app, user):
    client = app.test_client()
    with client.session_transaction() as session:
        session['_user_id'] = str(user.id)
        session['_fresh'] = True
    return client


def test_non_domain_experiment_redirects_or_rejects(
    client, auth_client, temporal_experiment
):
    page = client.get(f'/experiments/{temporal_experiment.id}/manage_terms')
    api = client.get(f'/experiments/{temporal_experiment.id}/get_terms')
    update = auth_client.post(
        f'/experiments/{temporal_experiment.id}/update_terms',
        json={'terms': ['agent'], 'domains': ['Law']},
    )

    assert page.status_code == 302
    assert api.status_code == 400
    assert update.status_code == 400
