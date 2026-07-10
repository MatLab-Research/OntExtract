"""Regression coverage for actor-scoped provenance visualization."""

import uuid

import pytest


def _user(db_session, suffix):
    from app.models.user import User

    user = User(
        username=f'provenance-view-{suffix}',
        email=f'provenance-view-{suffix}@example.com',
        password='password',
        account_status='active',
    )
    db_session.add(user)
    db_session.commit()
    return user


def _experiment(db_session, user, suffix):
    from app.models.experiment import Experiment

    experiment = Experiment(
        name=f'Provenance Experiment {suffix}',
        experiment_type='temporal_evolution',
        user_id=user.id,
        status='draft',
    )
    db_session.add(experiment)
    db_session.commit()
    return experiment


def _document(db_session, user, suffix):
    from app.models.document import Document

    document = Document(
        title=f'Provenance Document {suffix}',
        content='Provenance content.',
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


def _term(db_session, user, suffix, shared=False):
    from app.models.term import Term

    term = Term(
        term_text=f'provenance-term-{suffix}',
        status='active',
        created_by=None if shared else user.id,
    )
    db_session.add(term)
    db_session.commit()
    return term


def _provenance(db_session, user, parameters=None, activity_type='tool_execution'):
    from app.models.prov_o_models import ProvActivity, ProvAgent, ProvEntity

    agent = ProvAgent.query.filter_by(foaf_name=f'researcher:{user.id}').first()
    if not agent:
        agent = ProvAgent(
            agent_type='Person',
            foaf_name=f'researcher:{user.id}',
            agent_metadata={'username': user.username},
        )
        db_session.add(agent)
        db_session.flush()
    activity = ProvActivity(
        activity_type=activity_type,
        activity_status='completed',
        wasassociatedwith=agent.agent_id,
        activity_parameters=parameters or {},
    )
    db_session.add(activity)
    db_session.flush()
    entity = ProvEntity(
        entity_type='tool_result',
        wasgeneratedby=activity.activity_id,
        wasattributedto=agent.agent_id,
        entity_value={'owner_id': user.id},
    )
    db_session.add(entity)
    db_session.commit()
    return agent, activity, entity


def _client_for(app, user):
    client = app.test_client()
    with client.session_transaction() as session:
        session['_user_id'] = str(user.id)
        session['_fresh'] = True
    return client


def test_provenance_visualization_routes_remain_canonical(app):
    expected = {
        'provenance.timeline': 'app.routes.provenance_visualization.timeline',
        'provenance.experiment_timeline': (
            'app.routes.provenance_visualization.timeline'
        ),
        'provenance.provenance_graph': (
            'app.routes.provenance_visualization.graphs'
        ),
        'provenance.api_timeline': 'app.routes.provenance_visualization.api',
        'provenance.api_graph': 'app.routes.provenance_visualization.api',
        'provenance.entity_lineage': (
            'app.routes.provenance_visualization.lineage'
        ),
    }
    assert {
        endpoint: app.view_functions[endpoint].__module__
        for endpoint in expected
    } == expected


def test_timeline_user_filter_is_non_mutating(db_session, test_user):
    from app.models.prov_o_models import ProvAgent
    from app.services.provenance_service import provenance_service

    before = ProvAgent.query.count()
    assert provenance_service.get_timeline(user_id=test_user.id) == []
    assert ProvAgent.query.count() == before


def test_timeline_and_graph_queries_isolate_user_agents(
    db_session, test_user
):
    from app.services.provenance_service import provenance_service

    stranger = _user(db_session, 'query-stranger')
    _, owner_activity, _ = _provenance(db_session, test_user)
    _provenance(db_session, stranger)

    timeline = provenance_service.get_timeline(user_id=test_user.id)
    graph = provenance_service.get_graph_data(user_id=test_user.id)
    assert [item['activity']['id'] for item in timeline] == [
        str(owner_activity.activity_id)
    ]
    activity_ids = {
        node['data']['id']
        for node in graph['nodes']
        if 'activity' in node['classes']
    }
    assert activity_ids == {str(owner_activity.activity_id)}


def test_timeline_context_filters_options_and_bounds_limits(
    db_session, test_user, monkeypatch
):
    from app.services.provenance_visualization_service import (
        ProvenanceVisualizationService,
    )
    from app.services import provenance_visualization_service as module

    owned_experiment = _experiment(db_session, test_user, 'owned')
    owned_document = _document(db_session, test_user, 'owned')
    owned_term = _term(db_session, test_user, 'owned')
    shared_term = _term(db_session, test_user, 'shared', shared=True)
    stranger = _user(db_session, 'options-stranger')
    foreign_experiment = _experiment(db_session, stranger, 'foreign')
    foreign_document = _document(db_session, stranger, 'foreign')
    foreign_term = _term(db_session, stranger, 'foreign')
    calls = []
    monkeypatch.setattr(
        module.provenance_service,
        'get_timeline',
        lambda **kwargs: calls.append(kwargs) or [],
    )

    context = ProvenanceVisualizationService.timeline_context(
        {'limit': '500'},
        test_user.id,
    )
    assert context['limit'] == 200
    assert calls == [{
        'experiment_id': None,
        'document_ids': None,
        'activity_type': None,
        'term_id': None,
        'limit': 200,
        'include_invalidated': False,
        'user_id': test_user.id,
    }]
    assert {item.id for item in context['experiments']} == {
        owned_experiment.id
    }
    assert {item.id for item in context['documents']} == {owned_document.id}
    assert {item.id for item in context['terms']} == {
        owned_term.id,
        shared_term.id,
    }
    assert foreign_experiment not in context['experiments']
    assert foreign_document not in context['documents']
    assert foreign_term not in context['terms']


def test_authorized_resource_filter_keeps_software_agent_activities(
    db_session, test_user, monkeypatch
):
    from app.services import provenance_visualization_service as module
    from app.services.provenance_visualization_service import (
        ProvenanceVisualizationService,
    )

    experiment = _experiment(db_session, test_user, 'resource-scope')
    calls = []
    monkeypatch.setattr(
        module.provenance_service,
        'get_timeline',
        lambda **kwargs: calls.append(kwargs) or [],
    )
    ProvenanceVisualizationService.timeline_data(
        {'experiment_id': str(experiment.id)},
        test_user.id,
    )
    assert calls[0]['experiment_id'] == experiment.id
    assert calls[0]['user_id'] is None


@pytest.mark.parametrize(
    ('args', 'error_type'),
    [
        ({'limit': 'invalid'}, 'ValidationError'),
        ({'document_uuid': 'not-a-uuid'}, 'ValidationError'),
        ({'term_id': 'not-a-uuid'}, 'ValidationError'),
        ({'activity_type': 'not-supported'}, 'ValidationError'),
        ({'experiment_id': '999999'}, 'NotFoundError'),
    ],
)
def test_filter_validation_is_typed(db_session, test_user, args, error_type):
    from app.services import base_service
    from app.services.provenance_visualization_service import (
        ProvenanceVisualizationService,
    )

    with pytest.raises(getattr(base_service, error_type)):
        ProvenanceVisualizationService.timeline_data(args, test_user.id)


def test_foreign_filters_and_deleted_data_are_forbidden(
    db_session, test_user
):
    from app.services.base_service import PermissionError
    from app.services.provenance_visualization_service import (
        ProvenanceVisualizationService,
    )

    stranger = _user(db_session, 'filter-stranger')
    experiment = _experiment(db_session, stranger, 'filter-foreign')
    document = _document(db_session, stranger, 'filter-foreign')
    term = _term(db_session, stranger, 'filter-foreign')
    for args in (
        {'experiment_id': experiment.id},
        {'document_id': document.id},
        {'term_id': str(term.id)},
        {'include_deleted': 'true'},
    ):
        with pytest.raises(PermissionError):
            ProvenanceVisualizationService.timeline_context(args, test_user.id)


def test_admin_can_view_global_and_invalidated_provenance(
    db_session, admin_user, test_user, monkeypatch
):
    from app.services import provenance_visualization_service as module
    from app.services.provenance_visualization_service import (
        ProvenanceVisualizationService,
    )

    _experiment(db_session, test_user, 'admin-visible')
    calls = []
    monkeypatch.setattr(
        module.provenance_service,
        'get_timeline',
        lambda **kwargs: calls.append(kwargs) or [],
    )
    context = ProvenanceVisualizationService.timeline_context(
        {'include_deleted': 'true'},
        admin_user.id,
    )
    assert calls[0]['user_id'] is None
    assert calls[0]['include_invalidated'] is True
    assert context['include_deleted'] is True


def test_lineage_requires_entity_scope(
    app, db_session, test_user
):
    from app.services.base_service import PermissionError
    from app.services.provenance_visualization_service import (
        ProvenanceVisualizationService,
    )

    owner_client = _client_for(app, test_user)
    stranger = _user(db_session, 'lineage-stranger')
    _, _, entity = _provenance(db_session, test_user)

    with pytest.raises(PermissionError):
        ProvenanceVisualizationService.lineage_context(
            entity.entity_id,
            stranger.id,
        )
    owner_response = owner_client.get(
        f'/provenance/entity/{entity.entity_id}/lineage'
    )
    invalid = owner_client.get('/provenance/entity/not-a-uuid/lineage')
    missing = owner_client.get(
        f'/provenance/entity/{uuid.uuid4()}/lineage'
    )
    assert owner_response.status_code == 200
    assert str(entity.entity_id).encode() in owner_response.data
    assert invalid.status_code == 400
    assert missing.status_code == 404


def test_live_provenance_routes_require_authentication(app):
    client = app.test_client()
    for path in (
        '/provenance/timeline',
        '/provenance/graph',
        '/provenance/api/timeline',
        '/provenance/api/graph',
    ):
        assert client.get(path).status_code == 302
    assert client.get('/provenance/graph/compact').status_code == 200
    assert client.get('/provenance/graph/simple').status_code == 200


def test_route_filters_map_permission_validation_and_not_found(
    app, db_session, test_user
):
    stranger = _user(db_session, 'route-filter-stranger')
    foreign_experiment = _experiment(db_session, stranger, 'route-foreign')
    client = _client_for(app, test_user)
    forbidden_page = client.get(
        f'/provenance/timeline?experiment_id={foreign_experiment.id}'
    )
    forbidden_api = client.get(
        f'/provenance/api/graph?experiment_id={foreign_experiment.id}'
    )
    invalid_page = client.get('/provenance/timeline?document_uuid=invalid')
    invalid_api = client.get('/provenance/api/timeline?limit=invalid')
    missing_api = client.get('/provenance/api/graph?document_id=999999')
    deleted = client.get('/provenance/timeline?include_deleted=true')
    assert forbidden_page.status_code == 403
    assert forbidden_api.status_code == 403
    assert forbidden_api.get_json()['error'] == 'Permission denied'
    assert invalid_page.status_code == 400
    assert invalid_api.status_code == 400
    assert missing_api.status_code == 404
    assert deleted.status_code == 403


def test_experiment_timeline_requires_experiment_owner(
    app, db_session, test_user
):
    stranger = _user(db_session, 'experiment-timeline-stranger')
    experiment = _experiment(db_session, stranger, 'protected')
    response = _client_for(app, test_user).get(
        f'/provenance/experiment/{experiment.id}'
    )
    assert response.status_code == 403
