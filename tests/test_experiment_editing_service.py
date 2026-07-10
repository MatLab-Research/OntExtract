"""Regression coverage for authorized, additive experiment editing."""

import json

import pytest


def _user(db_session, suffix):
    from app.models.user import User

    user = User(
        username=f'experiment-edit-{suffix}',
        email=f'experiment-edit-{suffix}@example.com',
        password='password',
        account_status='active',
    )
    db_session.add(user)
    db_session.commit()
    return user


def _document(db_session, user, suffix, document_type='document'):
    from app.models.document import Document

    document = Document(
        title=f'Edit {suffix}',
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


def _term(db_session, user, suffix, shared=False):
    from app.models.term import Term

    term = Term(
        term_text=f'edit-term-{suffix}',
        status='active',
        created_by=None if shared else user.id,
    )
    db_session.add(term)
    db_session.commit()
    return term


def _experiment(
    db_session,
    user,
    suffix,
    *,
    document=None,
    reference=None,
    term=None,
    status='draft',
):
    from app.dto.experiment_dto import CreateExperimentDTO
    from app.services.experiment_service import ExperimentService

    experiment = ExperimentService().create_experiment(
        CreateExperimentDTO(
            name=f'Edit Experiment {suffix}',
            description='Original description',
            experiment_type='temporal_evolution',
            term_id=str(term.id) if term else None,
            document_uuids=[str(document.uuid)] if document else [],
            reference_uuids=[str(reference.uuid)] if reference else [],
            configuration={
                'terms': ['agency'],
                'periods': ['1900-1950'],
                'preserved': True,
            },
        ),
        user.id,
    )
    experiment.status = status
    db_session.commit()
    return experiment


def _dto(**values):
    from app.dto.experiment_dto import UpdateExperimentDTO

    return UpdateExperimentDTO(**values)


def _client_for(app, user):
    client = app.test_client()
    with client.session_transaction() as session:
        session['_user_id'] = str(user.id)
        session['_fresh'] = True
    return client


def test_experiment_edit_routes_remain_canonical(app):
    assert app.view_functions['experiments.edit'].__module__ == (
        'app.routes.experiments.crud.editing'
    )
    assert app.view_functions['experiments.update'].__module__ == (
        'app.routes.experiments.crud.editing'
    )


def test_edit_context_is_actor_scoped_and_selects_root_resources(
    db_session, test_user
):
    from app.services.experiment_editing_service import ExperimentEditingService

    document = _document(db_session, test_user, 'owned-document')
    reference = _document(
        db_session,
        test_user,
        'owned-reference',
        'reference',
    )
    term = _term(db_session, test_user, 'owned')
    shared_term = _term(db_session, test_user, 'shared', shared=True)
    experiment = _experiment(
        db_session,
        test_user,
        'context',
        document=document,
        reference=reference,
        term=term,
    )
    stranger = _user(db_session, 'context-stranger')
    foreign_document = _document(db_session, stranger, 'foreign-document')
    foreign_reference = _document(
        db_session,
        stranger,
        'foreign-reference',
        'reference',
    )
    foreign_term = _term(db_session, stranger, 'foreign')

    context = ExperimentEditingService.get_context(
        experiment.id,
        test_user.id,
    )
    assert {item.id for item in context['documents']} == {document.id}
    assert {item.id for item in context['references']} == {reference.id}
    assert {item.id for item in context['terms']} == {term.id, shared_term.id}
    assert context['selected_document_uuids'] == {str(document.uuid)}
    assert context['selected_reference_uuids'] == {str(reference.uuid)}
    assert context['selected_term_id'] == str(term.id)
    assert context['configuration']['preserved'] is True
    assert foreign_document not in context['documents']
    assert foreign_reference not in context['references']
    assert foreign_term not in context['terms']


def test_edit_context_requires_owner_and_editable_status(
    db_session, test_user
):
    from app.services.base_service import PermissionError, ValidationError
    from app.services.experiment_editing_service import ExperimentEditingService

    experiment = _experiment(db_session, test_user, 'protected')
    stranger = _user(db_session, 'protected-stranger')
    with pytest.raises(PermissionError):
        ExperimentEditingService.get_context(experiment.id, stranger.id)
    experiment.status = 'completed'
    db_session.commit()
    with pytest.raises(ValidationError, match='draft or error'):
        ExperimentEditingService.get_context(experiment.id, test_user.id)


def test_admin_can_edit_foreign_experiment_and_see_global_options(
    db_session, admin_user, test_user
):
    from app.services.experiment_editing_service import ExperimentEditingService

    document = _document(db_session, test_user, 'admin-document')
    reference = _document(db_session, test_user, 'admin-reference', 'reference')
    term = _term(db_session, test_user, 'admin-term')
    experiment = _experiment(db_session, test_user, 'admin-edit', term=term)
    context = ExperimentEditingService.get_context(experiment.id, admin_user.id)
    assert document in context['documents']
    assert reference in context['references']
    assert term in context['terms']
    ExperimentEditingService.update(
        experiment.id,
        _dto(name='Admin Updated'),
        admin_user.id,
    )
    assert experiment.name == 'Admin Updated'


def test_metadata_configuration_and_term_update_merge_atomically(
    db_session, test_user
):
    from app.services.experiment_editing_service import ExperimentEditingService

    first_term = _term(db_session, test_user, 'first')
    second_term = _term(db_session, test_user, 'second')
    experiment = _experiment(
        db_session,
        test_user,
        'metadata',
        term=first_term,
    )
    ExperimentEditingService.update(
        experiment.id,
        _dto(
            name='  Updated Experiment  ',
            description='Updated description',
            experiment_type='temporal_evolution',
            term_id=str(second_term.id),
            configuration={'periods': ['1950-2000'], 'new_setting': 7},
        ),
        test_user.id,
    )
    db_session.refresh(experiment)
    configuration = json.loads(experiment.configuration)
    assert experiment.name == 'Updated Experiment'
    assert experiment.description == 'Updated description'
    assert experiment.term_id == second_term.id
    assert configuration == {
        'terms': ['agency'],
        'periods': ['1950-2000'],
        'preserved': True,
        'new_setting': 7,
    }


def test_document_updates_are_additive_and_create_experiment_versions(
    db_session, test_user
):
    from app.models.document import Document
    from app.models.experiment_document import ExperimentDocument
    from app.services.experiment_editing_service import ExperimentEditingService

    first = _document(db_session, test_user, 'first-document')
    second = _document(db_session, test_user, 'second-document')
    experiment = _experiment(
        db_session,
        test_user,
        'add-document',
        document=first,
    )
    ExperimentEditingService.update(
        experiment.id,
        _dto(document_uuids=[str(first.uuid), str(second.uuid)]),
        test_user.id,
    )
    versions = Document.query.filter_by(
        experiment_id=experiment.id,
        version_type='experimental',
    ).all()
    assert {version.get_root_document().id for version in versions} == {
        first.id,
        second.id,
    }
    assert ExperimentDocument.query.filter_by(
        experiment_id=experiment.id
    ).count() == 2


def test_existing_documents_cannot_be_removed_in_place(
    db_session, test_user
):
    from app.models.document import Document
    from app.models.experiment_document import ExperimentDocument
    from app.services.base_service import ValidationError
    from app.services.experiment_editing_service import ExperimentEditingService

    document = _document(db_session, test_user, 'protected-document')
    experiment = _experiment(
        db_session,
        test_user,
        'remove-document',
        document=document,
    )
    version_count = Document.query.count()
    association_count = ExperimentDocument.query.filter_by(
        experiment_id=experiment.id
    ).count()
    with pytest.raises(ValidationError, match='cannot be removed'):
        ExperimentEditingService.update(
            experiment.id,
            _dto(document_uuids=[]),
            test_user.id,
        )
    assert Document.query.count() == version_count
    assert ExperimentDocument.query.filter_by(
        experiment_id=experiment.id
    ).count() == association_count


def test_references_can_be_replaced_or_cleared(db_session, test_user):
    from app.services.experiment_editing_service import ExperimentEditingService

    first = _document(db_session, test_user, 'first-reference', 'reference')
    second = _document(db_session, test_user, 'second-reference', 'reference')
    experiment = _experiment(
        db_session,
        test_user,
        'references',
        reference=first,
    )
    ExperimentEditingService.update(
        experiment.id,
        _dto(reference_uuids=[str(second.uuid)]),
        test_user.id,
    )
    assert [reference.id for reference in experiment.references] == [second.id]
    ExperimentEditingService.update(
        experiment.id,
        _dto(reference_uuids=[]),
        test_user.id,
    )
    assert experiment.get_reference_count() == 0


def test_legacy_integer_resources_use_same_authorization(
    db_session, test_user
):
    from app.services.base_service import PermissionError
    from app.services.experiment_editing_service import ExperimentEditingService

    document = _document(db_session, test_user, 'legacy-document')
    reference = _document(db_session, test_user, 'legacy-reference', 'reference')
    experiment = _experiment(db_session, test_user, 'legacy')
    ExperimentEditingService.update(
        experiment.id,
        _dto(document_ids=[document.id], reference_ids=[reference.id]),
        test_user.id,
    )
    assert experiment.get_document_count() == 1
    assert experiment.get_reference_count() == 1

    stranger = _user(db_session, 'legacy-stranger')
    foreign = _document(db_session, stranger, 'legacy-foreign')
    with pytest.raises(PermissionError):
        ExperimentEditingService.update(
            experiment.id,
            _dto(document_ids=[document.id, foreign.id]),
            test_user.id,
        )


def test_foreign_resources_and_term_are_forbidden_before_writes(
    db_session, test_user
):
    from app.services.base_service import PermissionError
    from app.services.experiment_editing_service import ExperimentEditingService

    experiment = _experiment(db_session, test_user, 'foreign-resource')
    original_name = experiment.name
    stranger = _user(db_session, 'resource-stranger')
    foreign_document = _document(db_session, stranger, 'resource-document')
    foreign_term = _term(db_session, stranger, 'resource-term')
    for data in (
        _dto(name='Should not persist', document_uuids=[str(foreign_document.uuid)]),
        _dto(name='Should not persist', term_id=str(foreign_term.id)),
    ):
        with pytest.raises(PermissionError):
            ExperimentEditingService.update(
                experiment.id,
                data,
                test_user.id,
            )
        db_session.refresh(experiment)
        assert experiment.name == original_name


def test_type_and_state_are_immutable(db_session, test_user):
    from app.services.base_service import ValidationError
    from app.services.experiment_editing_service import ExperimentEditingService

    experiment = _experiment(db_session, test_user, 'immutable')
    with pytest.raises(ValidationError, match='type cannot be changed'):
        ExperimentEditingService.update(
            experiment.id,
            _dto(experiment_type='entity_extraction'),
            test_user.id,
        )
    experiment.status = 'running'
    db_session.commit()
    with pytest.raises(ValidationError, match='draft or error'):
        ExperimentEditingService.update(
            experiment.id,
            _dto(name='Blocked'),
            test_user.id,
        )


def test_temporal_term_cannot_be_cleared(db_session, test_user):
    from app.services.base_service import ValidationError
    from app.services.experiment_editing_service import ExperimentEditingService

    term = _term(db_session, test_user, 'required')
    experiment = _experiment(
        db_session,
        test_user,
        'required-term',
        term=term,
    )
    with pytest.raises(ValidationError, match='focus term is required'):
        ExperimentEditingService.update(
            experiment.id,
            _dto(term_id=None),
            test_user.id,
        )


def test_update_failure_rolls_back_metadata_versions_and_references(
    db_session, test_user, monkeypatch
):
    from app.models.document import Document
    from app.models.experiment_document import ExperimentDocument
    from app.services.base_service import ServiceError
    from app.services.experiment_editing_service import ExperimentEditingService
    from app.services.experiment_resource_service import ExperimentResourceService

    document = _document(db_session, test_user, 'rollback-document')
    reference = _document(db_session, test_user, 'rollback-reference', 'reference')
    experiment = _experiment(db_session, test_user, 'rollback')
    baseline_documents = Document.query.count()
    baseline_associations = ExperimentDocument.query.count()
    monkeypatch.setattr(
        ExperimentResourceService,
        'replace_references',
        staticmethod(lambda *args: (_ for _ in ()).throw(
            RuntimeError('forced reference replacement failure')
        )),
    )
    with pytest.raises(ServiceError, match='Failed to update experiment'):
        ExperimentEditingService.update(
            experiment.id,
            _dto(
                name='Rolled back name',
                document_uuids=[str(document.uuid)],
                reference_uuids=[str(reference.uuid)],
            ),
            test_user.id,
        )
    db_session.refresh(experiment)
    assert experiment.name != 'Rolled back name'
    assert Document.query.count() == baseline_documents
    assert ExperimentDocument.query.count() == baseline_associations


def test_edit_page_and_update_route_contracts(
    app, db_session, test_user
):
    document = _document(db_session, test_user, 'route-document')
    reference = _document(db_session, test_user, 'route-reference', 'reference')
    term = _term(db_session, test_user, 'route-term')
    experiment = _experiment(
        db_session,
        test_user,
        'route',
        document=document,
        reference=reference,
        term=term,
    )
    client = _client_for(app, test_user)
    page = client.get(f'/experiments/{experiment.id}/edit')
    success = client.post(f'/experiments/{experiment.id}/update', json={
        'name': 'Route Updated',
        'experiment_type': 'temporal_evolution',
        'term_id': str(term.id),
        'document_uuids': [str(document.uuid)],
        'reference_uuids': [str(reference.uuid)],
        'configuration': {'route': True},
    })
    invalid = client.post(f'/experiments/{experiment.id}/update', json={
        'name': '   ',
    })
    missing = client.post('/experiments/999999/update', json={'name': 'Missing'})
    assert page.status_code == 200
    assert str(document.uuid).encode() in page.data
    assert b'document_uuids: documentUuids' in page.data
    assert b'reference_uuids: referenceUuids' in page.data
    assert b'term_id: termId' in page.data
    assert success.status_code == 200
    assert success.get_json()['success'] is True
    assert invalid.status_code == 400
    assert invalid.get_json()['error'] == 'Validation failed'
    assert missing.status_code == 404


def test_edit_routes_require_authentication(app, db_session, test_user):
    experiment = _experiment(db_session, test_user, 'authentication')
    client = app.test_client()
    assert client.get(f'/experiments/{experiment.id}/edit').status_code == 302
    assert client.post(
        f'/experiments/{experiment.id}/update',
        json={},
    ).status_code == 401


def test_foreign_edit_routes_are_forbidden(app, db_session, test_user):
    owner = _user(db_session, 'route-owner')
    experiment = _experiment(db_session, owner, 'foreign-route')
    client = _client_for(app, test_user)
    assert client.get(f'/experiments/{experiment.id}/edit').status_code == 403
    response = client.post(
        f'/experiments/{experiment.id}/update',
        json={'name': 'Forbidden'},
    )
    assert response.status_code == 403
    assert response.get_json()['error'] == 'Permission denied'
