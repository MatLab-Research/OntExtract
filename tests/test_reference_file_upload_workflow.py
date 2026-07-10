"""Regression coverage for the general reference file upload workflow."""

from io import BytesIO
from types import SimpleNamespace

import pytest
from werkzeug.datastructures import FileStorage, MultiDict


class FakeFileHandler:
    def __init__(self, path, content='Extracted reference text.'):
        self.path = path
        self.content = content
        self.saved = []

    def allowed_file(self, filename):
        return filename.rsplit('.', 1)[-1].lower() in {'txt', 'pdf'}

    def save_file(self, file, upload_folder=None):
        self.path.write_bytes(file.stream.read())
        self.saved.append((file.filename, upload_folder))
        return str(self.path), self.path.stat().st_size

    def extract_text_from_file(self, path, filename):
        return self.content

    @staticmethod
    def get_file_extension(filename):
        return filename.rsplit('.', 1)[-1].lower()


class ProcessingRecorder:
    def __init__(self, error=None):
        self.error = error
        self.documents = []

    def process_document(self, document):
        self.documents.append(document)
        if self.error:
            raise RuntimeError(self.error)
        document.status = 'completed'


class ProvenanceRecorder:
    def __init__(self, error=None):
        self.error = error
        self.reference_calls = []
        self.document_calls = []

    def track_reference_creation(self, **kwargs):
        self.reference_calls.append(kwargs)
        if self.error:
            raise self.error

    def track_document_upload(self, document, user, experiment=None):
        self.document_calls.append((document, user, experiment))


def _file(name='reference.txt', content=b'Reference content'):
    return FileStorage(stream=BytesIO(content), filename=name)


def _workflow(tmp_path, **kwargs):
    from app.services.legacy_upload_workflow import LegacyUploadWorkflow

    path = tmp_path / kwargs.pop('filename', 'saved-reference.txt')
    handler = kwargs.pop('file_handler', FakeFileHandler(path))
    processing = kwargs.pop('processing', ProcessingRecorder())
    provenance = kwargs.pop('provenance', ProvenanceRecorder())
    workflow = LegacyUploadWorkflow(
        file_handler=handler,
        processing_service=processing,
        provenance_service=provenance,
        workflow_logger=kwargs.pop(
            'logger',
            SimpleNamespace(
                info=lambda *args, **kw: None,
                warning=lambda *args, **kw: None,
                error=lambda *args, **kw: None,
            ),
        ),
        **kwargs,
    )
    return workflow, handler, processing, provenance, path


def _user(db_session, suffix):
    from app.models.user import User

    user = User(
        username=f'reference-upload-{suffix}',
        email=f'reference-upload-{suffix}@example.com',
        password='password',
        account_status='active',
    )
    db_session.add(user)
    db_session.commit()
    return user


def test_reference_upload_route_remains_canonical(app):
    assert app.view_functions['references.upload'].__module__ == (
        'app.routes.references.upload.files'
    )


def test_forced_reference_upload_normalizes_content_and_metadata(
    db_session, test_user, tmp_path
):
    workflow, _, processing, provenance, path = _workflow(tmp_path)
    outcome = workflow.upload(
        _file(),
        MultiDict({
            'title': '  Uploaded Reference  ',
            'reference_subtype': 'academic',
            'prov_type': 'prov:Entity/SourceDocument',
            'authors': 'Ada Lovelace, Alan Turing',
            'publication_date': '1843',
            'doi': '10.1000/reference',
            'journal': 'Analytical Engines',
        }),
        test_user,
        str(tmp_path),
        force_document_type='reference',
        prefill_metadata=False,
        validate_file_type=True,
    )

    document = outcome['document']
    assert document.document_type == 'reference'
    assert document.reference_subtype == 'academic'
    assert document.title == 'Uploaded Reference'
    assert document.content == 'Extracted reference text.'
    assert document.publication_date.isoformat() == '1843-01-01'
    assert document.doi == '10.1000/reference'
    assert document.journal == 'Analytical Engines'
    assert document.source_metadata['authors'] == [
        'Ada Lovelace',
        'Alan Turing',
    ]
    assert document.source_metadata['doi'] == '10.1000/reference'
    assert processing.documents == [document]
    assert path.exists()
    assert len(provenance.reference_calls) == 1
    assert provenance.reference_calls[0]['source'] == 'manual'
    assert provenance.document_calls == []


def test_reference_mode_rejects_disallowed_file_before_saving(
    test_user, tmp_path
):
    from app.services.base_service import ValidationError

    workflow, handler, _, _, path = _workflow(tmp_path)
    with pytest.raises(ValidationError, match='File type is not allowed'):
        workflow.upload(
            _file('malware.exe'),
            MultiDict({'title': 'Rejected'}),
            test_user,
            str(tmp_path),
            force_document_type='reference',
            validate_file_type=True,
        )
    assert handler.saved == []
    assert not path.exists()


def test_invalid_experiment_is_rejected_before_file_save(
    test_user, tmp_path
):
    from app.services.base_service import NotFoundError

    workflow, handler, _, _, path = _workflow(tmp_path)
    with pytest.raises(NotFoundError, match='Experiment not found'):
        workflow.upload(
            _file(),
            MultiDict({'experiment_id': '999999'}),
            test_user,
            str(tmp_path),
            force_document_type='reference',
        )
    assert handler.saved == []
    assert not path.exists()


def test_unauthorized_experiment_is_rejected_before_file_save(
    db_session, test_user, temporal_experiment, tmp_path
):
    from app.services.base_service import PermissionError

    stranger = _user(db_session, 'stranger')
    workflow, handler, _, _, path = _workflow(tmp_path)
    with pytest.raises(PermissionError):
        workflow.upload(
            _file(),
            MultiDict({'experiment_id': str(temporal_experiment.id)}),
            stranger,
            str(tmp_path),
            force_document_type='reference',
        )
    assert handler.saved == []
    assert not path.exists()


def test_reference_creation_and_experiment_link_are_atomic(
    db_session, test_user, temporal_experiment, tmp_path
):
    from app.models.experiment import experiment_references

    workflow, _, _, provenance, _ = _workflow(tmp_path)
    outcome = workflow.upload(
        _file(),
        MultiDict({
            'title': 'Linked Reference',
            'experiment_id': str(temporal_experiment.id),
            'include_in_analysis': 'true',
        }),
        test_user,
        str(tmp_path),
        force_document_type='reference',
    )
    document = outcome['document']
    row = db_session.execute(
        experiment_references.select().where(
            experiment_references.c.reference_id == document.id
        )
    ).mappings().one()
    assert row['experiment_id'] == temporal_experiment.id
    assert row['include_in_analysis'] is True
    assert outcome['linked_experiment'] is temporal_experiment
    assert provenance.reference_calls[0]['experiment'] is temporal_experiment


def test_admin_can_upload_reference_to_another_users_experiment(
    db_session, admin_user, temporal_experiment, tmp_path
):
    workflow, _, _, _, _ = _workflow(tmp_path)
    outcome = workflow.upload(
        _file(),
        MultiDict({'experiment_id': str(temporal_experiment.id)}),
        admin_user,
        str(tmp_path),
        force_document_type='reference',
    )
    assert outcome['linked_experiment'] is temporal_experiment


def test_persistence_failure_removes_saved_reference_file(
    monkeypatch, test_user, tmp_path
):
    from app import db

    workflow, _, _, _, path = _workflow(tmp_path)
    monkeypatch.setattr(db.session, 'commit', lambda: (_ for _ in ()).throw(
        RuntimeError('database unavailable')
    ))
    with pytest.raises(RuntimeError, match='database unavailable'):
        workflow.upload(
            _file(),
            MultiDict({'title': 'Failed reference'}),
            test_user,
            str(tmp_path),
            force_document_type='reference',
        )
    assert not path.exists()


def test_processing_and_provenance_failures_do_not_undo_reference(
    db_session, test_user, tmp_path
):
    from app.models.document import Document

    workflow, _, _, _, path = _workflow(
        tmp_path,
        processing=ProcessingRecorder('processor unavailable'),
        provenance=ProvenanceRecorder(RuntimeError('PROV unavailable')),
    )
    outcome = workflow.upload(
        _file(),
        MultiDict({'title': 'Durable reference'}),
        test_user,
        str(tmp_path),
        force_document_type='reference',
    )
    assert outcome['processing_warning'] == 'processor unavailable'
    assert db_session.get(Document, outcome['document'].id) is not None
    assert path.exists()


def test_reference_route_delegates_with_reference_mode(
    app, auth_client, sample_document, monkeypatch
):
    from app.routes.references.upload import files

    calls = []

    def upload(
        self,
        file,
        form,
        user,
        upload_folder,
        **options,
    ):
        calls.append((file.filename, user.id, upload_folder, options))
        sample_document.document_type = 'reference'
        return {
            'document': sample_document,
            'processing_warning': None,
            'linked_experiment': None,
        }

    monkeypatch.setattr(files.LegacyUploadWorkflow, 'upload', upload)
    response = auth_client.post(
        '/references/upload',
        data={
            'file': (BytesIO(b'reference'), 'route.txt'),
            'title': 'Route Reference',
        },
        content_type='multipart/form-data',
    )
    assert response.status_code == 302
    assert response.headers['Location'].endswith(
        f'/references/{sample_document.id}'
    )
    assert calls[0][3]['force_document_type'] == 'reference'
    assert calls[0][3]['validate_file_type'] is True


def test_reference_upload_get_hides_unauthorized_experiment_context(
    app, db_session, test_user, temporal_experiment
):
    stranger = _user(db_session, 'route-context')
    client = app.test_client()
    with client.session_transaction() as session:
        session['_user_id'] = str(stranger.id)
        session['_fresh'] = True
    response = client.get(
        f'/references/upload?tabbed=false&experiment_id={temporal_experiment.id}'
    )
    assert response.status_code == 200
    assert temporal_experiment.name.encode() not in response.data


def test_reference_upload_post_requires_authentication(app):
    response = app.test_client().post('/references/upload', data={})
    assert response.status_code == 401
