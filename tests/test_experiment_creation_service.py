"""Regression coverage for authorized, atomic experiment creation."""

import json

import pytest


def _user(db_session, suffix):
    from app.models.user import User

    user = User(
        username=f'experiment-create-{suffix}',
        email=f'experiment-create-{suffix}@example.com',
        password='password',
        account_status='active',
    )
    db_session.add(user)
    db_session.commit()
    return user


def _document(db_session, user, suffix, document_type='document'):
    from app.models.document import Document

    document = Document(
        title=f'Creation Resource {suffix}',
        content=f'Content for {suffix}.',
        content_type='text',
        document_type=document_type,
        status='completed',
        user_id=user.id,
        version_number=1,
        version_type='original',
    )
    db_session.add(document)
    db_session.commit()
    return document


def _term(db_session, user, suffix):
    from app.models.term import Term

    term = Term(
        term_text=f'creation-term-{suffix}',
        status='active',
        created_by=user.id,
    )
    db_session.add(term)
    db_session.commit()
    return term


def _dto(**values):
    from app.dto.experiment_dto import CreateExperimentDTO

    defaults = {
        'name': 'Creation service experiment',
        'experiment_type': 'temporal_evolution',
        'configuration': {'periods': [2000, 2010]},
    }
    defaults.update(values)
    return CreateExperimentDTO(**defaults)


def _client_for(app, user):
    client = app.test_client()
    with client.session_transaction() as session:
        session['_user_id'] = str(user.id)
        session['_fresh'] = True
    return client


def test_creation_routes_remain_canonical(app):
    assert app.view_functions['experiments.create'].__module__ == (
        'app.routes.experiments.crud.creation'
    )
    assert app.view_functions['experiments.create_sample'].__module__ == (
        'app.routes.experiments.crud.creation'
    )


def test_creation_dto_supports_empty_and_legacy_clients():
    empty = _dto()
    legacy = _dto(document_ids=[1], reference_ids=[2])
    assert empty.document_uuids == []
    assert empty.reference_uuids == []
    assert legacy.document_ids == [1]
    assert legacy.reference_ids == [2]


def test_create_with_owned_uuids_is_atomic_and_canonical(
    db_session, test_user
):
    from app import db
    from app.models.experiment import experiment_references
    from app.models.experiment_document import ExperimentDocument
    from app.models.document import Document
    from app.services.experiment_service import ExperimentService

    document = _document(db_session, test_user, 'uuid-document')
    reference = _document(
        db_session,
        test_user,
        'uuid-reference',
        document_type='reference',
    )
    term = _term(db_session, test_user, 'uuid')
    experiment = ExperimentService().create_experiment(
        _dto(
            name='  Owned UUID experiment  ',
            term_id=str(term.id),
            document_uuids=[str(document.uuid), str(document.uuid)],
            reference_uuids=[str(reference.uuid)],
        ),
        test_user.id,
    )

    assert experiment.name == 'Owned UUID experiment'
    assert experiment.term_id == term.id
    association = ExperimentDocument.query.filter_by(
        experiment_id=experiment.id
    ).one()
    version = db_session.get(Document, association.document_id)
    assert version.source_document_id == document.id
    assert version.version_type == 'experimental'
    assert version.experiment_id == experiment.id
    assert list(experiment.documents) == [version]
    reference_row = db_session.execute(
        db.select(experiment_references).where(
            experiment_references.c.experiment_id == experiment.id
        )
    ).mappings().one()
    assert reference_row['reference_id'] == reference.id
    assert reference_row['include_in_analysis'] is True


def test_legacy_integer_ids_use_same_authorization_and_associations(
    db_session, test_user
):
    from app.services.experiment_service import ExperimentService

    document = _document(db_session, test_user, 'legacy-document')
    reference = _document(
        db_session,
        test_user,
        'legacy-reference',
        document_type='reference',
    )
    experiment = ExperimentService().create_experiment(
        _dto(document_ids=[document.id], reference_ids=[reference.id]),
        test_user.id,
    )
    assert experiment.get_document_count() == 1
    assert experiment.get_reference_count() == 1


@pytest.mark.parametrize('resource_kind', ['document', 'reference', 'term'])
def test_foreign_resources_are_rejected_before_experiment_creation(
    db_session, test_user, resource_kind
):
    from app.models.experiment import Experiment
    from app.services.base_service import PermissionError
    from app.services.experiment_service import ExperimentService

    owner = _user(db_session, f'foreign-{resource_kind}')
    values = {}
    if resource_kind == 'document':
        resource = _document(db_session, owner, 'foreign-document')
        values['document_uuids'] = [str(resource.uuid)]
    elif resource_kind == 'reference':
        resource = _document(
            db_session,
            owner,
            'foreign-reference',
            document_type='reference',
        )
        values['reference_uuids'] = [str(resource.uuid)]
    else:
        resource = _term(db_session, owner, 'foreign')
        values['term_id'] = str(resource.id)
    before = Experiment.query.count()

    with pytest.raises(PermissionError):
        ExperimentService().create_experiment(_dto(**values), test_user.id)
    assert Experiment.query.count() == before


def test_admin_can_create_with_foreign_resources(
    db_session, admin_user, test_user
):
    from app.services.experiment_service import ExperimentService

    document = _document(db_session, test_user, 'admin-document')
    reference = _document(
        db_session,
        test_user,
        'admin-reference',
        document_type='reference',
    )
    term = _term(db_session, test_user, 'admin')
    experiment = ExperimentService().create_experiment(
        _dto(
            term_id=str(term.id),
            document_uuids=[str(document.uuid)],
            reference_uuids=[str(reference.uuid)],
        ),
        admin_user.id,
    )
    assert experiment.user_id == admin_user.id
    assert experiment.term_id == term.id
    assert experiment.get_document_count() == 1
    assert experiment.get_reference_count() == 1


def test_unowned_legacy_term_is_available_as_shared_catalog_data(
    db_session, test_user
):
    from app.models.term import Term
    from app.services.experiment_service import ExperimentService

    term = Term(term_text='legacy-global-term', status='active')
    db_session.add(term)
    db_session.commit()
    experiment = ExperimentService().create_experiment(
        _dto(term_id=str(term.id)),
        test_user.id,
    )
    assert experiment.term_id == term.id


@pytest.mark.parametrize(
    'values',
    [
        {'document_uuids': ['not-a-uuid']},
        {'reference_uuids': ['00000000-0000-0000-0000-000000000000']},
        {'term_id': 'not-a-uuid'},
        {'document_ids': [999999]},
    ],
)
def test_missing_creation_resources_are_typed_not_found(
    test_user, values
):
    from app.services.base_service import NotFoundError
    from app.services.experiment_service import ExperimentService

    with pytest.raises(NotFoundError):
        ExperimentService().create_experiment(_dto(**values), test_user.id)


def test_creation_failure_rolls_back_versions_provenance_and_experiment(
    db_session, test_user, monkeypatch
):
    from app.models.document import Document
    from app.models.experiment import Experiment
    from app.models.experiment_document import ExperimentDocument
    from app.models.prov_o_models import ProvActivity, ProvAgent, ProvEntity
    from app.services.base_service import ServiceError
    from app.services.experiment_resource_service import ExperimentResourceService
    from app.services.experiment_service import ExperimentService

    document = _document(db_session, test_user, 'rollback-document')
    reference = _document(
        db_session,
        test_user,
        'rollback-reference',
        document_type='reference',
    )
    baseline = {
        'experiments': Experiment.query.count(),
        'documents': Document.query.count(),
        'associations': ExperimentDocument.query.count(),
        'agents': ProvAgent.query.count(),
        'activities': ProvActivity.query.count(),
        'entities': ProvEntity.query.count(),
    }
    monkeypatch.setattr(
        ExperimentResourceService,
        'add_references',
        staticmethod(lambda experiment, references: (_ for _ in ()).throw(
            RuntimeError('forced reference failure')
        )),
    )

    with pytest.raises(ServiceError, match='Failed to create experiment'):
        ExperimentService().create_experiment(
            _dto(
                document_uuids=[str(document.uuid)],
                reference_uuids=[str(reference.uuid)],
            ),
            test_user.id,
        )
    assert Experiment.query.count() == baseline['experiments']
    assert Document.query.count() == baseline['documents']
    assert ExperimentDocument.query.count() == baseline['associations']
    assert ProvAgent.query.count() == baseline['agents']
    assert ProvActivity.query.count() == baseline['activities']
    assert ProvEntity.query.count() == baseline['entities']


def test_create_route_contracts_and_json_safe_validation(
    app, auth_client, db_session, test_user
):
    foreign_owner = _user(db_session, 'route-foreign')
    foreign = _document(db_session, foreign_owner, 'route-foreign-document')
    invalid = auth_client.post('/experiments/create', json={'name': ' '})
    missing = auth_client.post('/experiments/create', json={
        'name': 'Missing resource',
        'experiment_type': 'entity_extraction',
        'document_uuids': ['not-a-uuid'],
    })
    forbidden = auth_client.post('/experiments/create', json={
        'name': 'Forbidden resource',
        'experiment_type': 'entity_extraction',
        'document_uuids': [str(foreign.uuid)],
    })
    empty = auth_client.post('/experiments/create', json={
        'name': 'Empty draft experiment',
        'experiment_type': 'temporal_evolution',
        'document_ids': [],
    })
    assert invalid.status_code == 400
    assert invalid.get_json()['error'] == 'Validation failed'
    assert json.loads(json.dumps(invalid.get_json()['details']))
    assert missing.status_code == 404
    assert forbidden.status_code == 403
    assert forbidden.get_json()['error'] == 'Permission denied'
    assert empty.status_code == 201


def test_create_route_requires_authentication(app):
    response = app.test_client().post('/experiments/create', json={
        'name': 'Anonymous',
        'experiment_type': 'temporal_evolution',
    })
    assert response.status_code == 401


def test_sample_creation_is_post_only_and_uses_owned_references(
    app, db_session, test_user
):
    from app.models.experiment import Experiment

    owned = _document(
        db_session,
        test_user,
        'sample-owned-reference',
        document_type='reference',
    )
    stranger = _user(db_session, 'sample-stranger')
    foreign = _document(
        db_session,
        stranger,
        'sample-foreign-reference',
        document_type='reference',
    )
    client = _client_for(app, test_user)
    get_response = client.get('/experiments/sample')
    post_response = client.post('/experiments/sample')

    assert get_response.status_code == 405
    assert post_response.status_code == 302
    experiment = Experiment.query.filter_by(
        name='Sample: Agent Domain Comparison',
        user_id=test_user.id,
    ).one()
    assert {item.id for item in experiment.references} == {owned.id}
    assert foreign.id not in {item.id for item in experiment.references}


def test_creation_pages_filter_resources_and_render_uuid_wizard_payload(
    app, db_session, test_user
):
    owned_document = _document(db_session, test_user, 'page-owned-document')
    owned_reference = _document(
        db_session,
        test_user,
        'page-owned-reference',
        document_type='reference',
    )
    owned_term = _term(db_session, test_user, 'page-owned')
    stranger = _user(db_session, 'page-stranger')
    foreign_document = _document(db_session, stranger, 'page-foreign-document')
    foreign_reference = _document(
        db_session,
        stranger,
        'page-foreign-reference',
        document_type='reference',
    )
    foreign_term = _term(db_session, stranger, 'page-foreign')
    client = _client_for(app, test_user)
    new_page = client.get('/experiments/new')
    wizard = client.get('/experiments/wizard')

    assert new_page.status_code == 200
    assert owned_document.title.encode() in new_page.data
    assert owned_reference.title.encode() in new_page.data
    assert owned_term.term_text.encode() in new_page.data
    assert foreign_document.title.encode() not in new_page.data
    assert foreign_reference.title.encode() not in new_page.data
    assert foreign_term.term_text.encode() not in new_page.data
    assert wizard.status_code == 200
    assert str(owned_document.uuid).encode() in wizard.data
    assert str(owned_reference.uuid).encode() in wizard.data
    assert b'document_uuids' in wizard.data
    assert b'reference_uuids' in wizard.data
    assert b'document_ids' not in wizard.data
    assert b'reference_ids' not in wizard.data


def test_single_document_mode_does_not_reveal_foreign_document(
    app, db_session, test_user
):
    stranger = _user(db_session, 'single-document-stranger')
    foreign = _document(db_session, stranger, 'single-document-foreign')
    response = _client_for(app, test_user).get(
        '/experiments/new',
        query_string={
            'mode': 'single_document',
            'document_uuid': str(foreign.uuid),
            'document_title': foreign.title,
        },
    )
    assert response.status_code == 200
    assert b'No documents available' in response.data
    assert str(foreign.uuid).encode() not in response.data
    assert foreign.title.encode() not in response.data
