"""Regression coverage for secure reference CRUD workflows."""

from datetime import date
from types import SimpleNamespace

import pytest


def _reference(db_session, user, suffix, **kwargs):
    from app.models.document import Document

    reference = Document(
        title=f'Reference {suffix}',
        content='Reference content.',
        content_type=kwargs.pop('content_type', 'text'),
        document_type='reference',
        reference_subtype=kwargs.pop('reference_subtype', 'academic'),
        status='completed',
        user_id=user.id,
        **kwargs,
    )
    db_session.add(reference)
    db_session.commit()
    return reference


def _user(db_session, suffix):
    from app.models.user import User

    user = User(
        username=f'reference-crud-{suffix}',
        email=f'reference-crud-{suffix}@example.com',
        password='password',
        account_status='active',
    )
    db_session.add(user)
    db_session.commit()
    return user


def test_reference_crud_routes_remain_canonical(app):
    expected = 'app.routes.references.crud'
    for endpoint in (
        'references.index',
        'references.view',
        'references.edit',
        'references.delete',
        'references.download',
    ):
        assert app.view_functions[endpoint].__module__ == expected


def test_list_and_detail_are_reference_only_and_public(
    client, db_session, test_user, sample_document
):
    from app.services.reference_crud_service import ReferenceCrudService

    first = _reference(db_session, test_user, 'first')
    second = _reference(db_session, test_user, 'second')
    references = ReferenceCrudService.list_references()
    assert references[:2] == [second, first]
    assert sample_document not in references

    context = ReferenceCrudService.detail_context(first.id)
    assert context == {'reference': first, 'experiments_using': []}
    assert client.get('/references/').status_code == 200
    assert client.get(f'/references/{first.id}').status_code == 200
    assert client.get(f'/references/{sample_document.id}').status_code == 404


def test_update_normalizes_clearable_metadata_and_dates(
    db_session, test_user
):
    from app.services.reference_crud_service import ReferenceCrudService

    reference = _reference(
        db_session,
        test_user,
        'update',
        journal='Old journal',
        publication_date=date(2000, 1, 1),
    )
    updated = ReferenceCrudService.update(
        reference.id,
        test_user.id,
        {
            'title': '  Updated Reference  ',
            'reference_subtype': '  dictionary_oed  ',
            'authors': ' Ada Lovelace ',
            'publication_date': '2024-05',
            'access_date': '2026',
            'journal': '',
            'doi': ' 10.1000/example ',
            'entry_term': ' agency ',
            'notes': '  Reviewed. ',
        },
    )
    assert updated.title == 'Updated Reference'
    assert updated.reference_subtype == 'dictionary_oed'
    assert updated.authors == 'Ada Lovelace'
    assert updated.publication_date == date(2024, 5, 1)
    assert updated.access_date == date(2026, 1, 1)
    assert updated.journal is None
    assert updated.doi == '10.1000/example'
    assert updated.entry_term == 'agency'
    assert updated.notes == 'Reviewed.'


@pytest.mark.parametrize(
    ('form', 'message'),
    [
        ({'title': '', 'reference_subtype': 'academic'}, 'Title is required'),
        ({'title': 'Title', 'reference_subtype': ''}, 'Reference type is required'),
        (
            {
                'title': 'Title',
                'reference_subtype': 'academic',
                'publication_date': 'not-a-date',
            },
            'Publication date is invalid',
        ),
    ],
)
def test_update_validates_required_fields_and_dates(
    db_session, test_user, form, message
):
    from app.services.base_service import ValidationError
    from app.services.reference_crud_service import ReferenceCrudService

    reference = _reference(db_session, test_user, f'validation-{len(message)}')
    with pytest.raises(ValidationError, match=message):
        ReferenceCrudService.update(
            reference.id,
            test_user.id,
            form,
        )


def test_edit_and_delete_require_owner_or_admin(
    db_session, test_user, admin_user
):
    from app.services.base_service import PermissionError
    from app.services.reference_crud_service import ReferenceCrudService

    reference = _reference(db_session, test_user, 'permission')
    stranger = _user(db_session, 'stranger')
    with pytest.raises(PermissionError):
        ReferenceCrudService.edit_context(reference.id, stranger.id)
    with pytest.raises(PermissionError):
        ReferenceCrudService().delete(reference.id, stranger.id)
    context = ReferenceCrudService.edit_context(reference.id, admin_user.id)
    assert context['reference'] is reference


def test_delete_blocks_reference_used_by_experiment(
    db_session, test_user, temporal_experiment
):
    from app.models.document import Document
    from app.models.experiment import experiment_references
    from app.services.reference_crud_service import (
        ReferenceCrudService,
        ReferenceInUseError,
    )

    reference = _reference(db_session, test_user, 'linked')
    db_session.execute(experiment_references.insert().values(
        experiment_id=temporal_experiment.id,
        reference_id=reference.id,
        include_in_analysis=True,
    ))
    db_session.commit()
    with pytest.raises(ReferenceInUseError) as exc:
        ReferenceCrudService().delete(reference.id, test_user.id)
    assert exc.value.experiments == [temporal_experiment]
    assert db_session.get(Document, reference.id) is reference


def test_delete_parent_removes_children_files_and_tracks_family_provenance(
    db_session, test_user, tmp_path
):
    from app.models.document import Document
    from app.services.reference_crud_service import ReferenceCrudService

    parent_file = tmp_path / 'parent.txt'
    child_file = tmp_path / 'child.txt'
    parent_file.write_text('parent')
    child_file.write_text('child')
    parent = _reference(
        db_session,
        test_user,
        'parent',
        content_type='file',
        original_filename='parent.txt',
        file_path=str(parent_file),
    )
    child = _reference(
        db_session,
        test_user,
        'child',
        content_type='file',
        original_filename='child.txt',
        file_path=str(child_file),
        parent_document_id=parent.id,
    )
    calls = []
    provenance = SimpleNamespace(
        delete_or_invalidate_document_provenance=lambda document_id: (
            calls.append(document_id)
        )
    )
    deleted_id = ReferenceCrudService(provenance).delete(
        parent.id,
        test_user.id,
    )
    assert deleted_id == parent.id
    assert db_session.get(Document, parent.id) is None
    assert db_session.get(Document, child.id) is None
    assert parent_file.exists() is False
    assert child_file.exists() is False
    assert calls == [parent.id, child.id]


def test_provenance_failure_does_not_undo_deleted_reference(
    db_session, test_user
):
    from app.models.document import Document
    from app.services.reference_crud_service import ReferenceCrudService

    reference = _reference(db_session, test_user, 'provenance')

    class FailingProvenance:
        @staticmethod
        def delete_or_invalidate_document_provenance(document_id):
            raise RuntimeError('PROV unavailable')

    ReferenceCrudService(
        FailingProvenance(),
        SimpleNamespace(warning=lambda message: None),
    ).delete(reference.id, test_user.id)
    assert db_session.get(Document, reference.id) is None


def test_download_is_reference_only_and_requires_existing_file(
    db_session, test_user, sample_document, tmp_path
):
    from app.services.base_service import NotFoundError, ValidationError
    from app.services.reference_crud_service import ReferenceCrudService

    file_path = tmp_path / 'reference.pdf'
    file_path.write_bytes(b'pdf')
    reference = _reference(
        db_session,
        test_user,
        'download',
        content_type='file',
        original_filename='original.pdf',
        file_path=str(file_path),
    )
    assert ReferenceCrudService.download(reference.id) == {
        'path': str(file_path),
        'filename': 'original.pdf',
    }
    with pytest.raises(NotFoundError):
        ReferenceCrudService.download(sample_document.id)
    file_path.unlink()
    with pytest.raises(ValidationError, match='not available'):
        ReferenceCrudService.download(reference.id)


def test_reference_routes_apply_permissions_and_updates(
    auth_client, db_session, test_user
):
    reference = _reference(db_session, test_user, 'routes')
    edit_page = auth_client.get(f'/references/{reference.id}/edit')
    update = auth_client.post(
        f'/references/{reference.id}/edit',
        data={
            'title': 'Route Updated',
            'reference_subtype': 'book',
            'publication_date': '2020',
        },
    )
    assert edit_page.status_code == 200
    assert update.status_code == 302
    assert reference.title == 'Route Updated'
    assert reference.publication_date == date(2020, 1, 1)


def test_reference_mutations_require_authentication(app, db_session, test_user):
    reference = _reference(db_session, test_user, 'anonymous-routes')
    anonymous = app.test_client()
    assert anonymous.get(f'/references/{reference.id}').status_code == 200
    assert anonymous.get(f'/references/{reference.id}/edit').status_code == 302
    assert anonymous.post(f'/references/{reference.id}/delete').status_code == 302


def test_reference_routes_reject_stranger_and_hide_controls(
    app, db_session, test_user
):
    reference = _reference(db_session, test_user, 'route-stranger')
    stranger = _user(db_session, 'route-stranger')
    client = app.test_client()
    with client.session_transaction() as session:
        session['_user_id'] = str(stranger.id)
        session['_fresh'] = True
    detail = client.get(f'/references/{reference.id}')
    edit = client.get(f'/references/{reference.id}/edit')
    delete = client.post(f'/references/{reference.id}/delete')
    assert detail.status_code == 200
    assert b'Edit Metadata' not in detail.data
    assert b'Delete Reference' not in detail.data
    assert edit.status_code == 302
    assert delete.status_code == 302


def test_linked_reference_delete_route_preserves_reference(
    app, db_session, test_user, temporal_experiment
):
    from app.models.document import Document
    from app.models.experiment import experiment_references

    reference = _reference(db_session, test_user, 'route-linked')
    db_session.execute(experiment_references.insert().values(
        experiment_id=temporal_experiment.id,
        reference_id=reference.id,
    ))
    db_session.commit()
    client = app.test_client()
    with client.session_transaction() as session:
        session['_user_id'] = str(test_user.id)
        session['_fresh'] = True
    response = client.post(
        f'/references/{reference.id}/delete',
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b'Cannot delete this reference' in response.data
    assert db_session.get(Document, reference.id) is reference
