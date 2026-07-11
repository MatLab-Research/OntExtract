"""Regression coverage for reviewed upload persistence."""

from types import SimpleNamespace


class RecordingProvenanceService:
    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        def record(*args, **kwargs):
            self.calls.append((name, args, kwargs))
        return record


class FakeUploadService:
    def __init__(self, final_path, *, extraction_error=None):
        self.final_path = str(final_path)
        self.extraction_error = extraction_error

    def save_permanent(self, temp_path, upload_dir, filename):
        self.final_path_obj.write_bytes(self.temp_path_obj.read_bytes())
        self.temp_path_obj.unlink()
        return SimpleNamespace(
            success=True,
            file_path=self.final_path,
            error=None,
        )

    def extract_text_content(self, file_path, filename):
        if self.extraction_error:
            return None, self.extraction_error, None
        return 'Extracted document text.', None, 'test-extractor'

    def bind_paths(self, temp_path, final_path):
        self.temp_path_obj = temp_path
        self.final_path_obj = final_path
        return self


def _service(tmp_path, extraction_error=None):
    from app.services.upload_persistence_service import UploadPersistenceService

    temp_path = tmp_path / 'temporary.pdf'
    final_path = tmp_path / 'permanent.pdf'
    temp_path.write_bytes(b'pdf content')
    upload = FakeUploadService(
        final_path,
        extraction_error=extraction_error,
    ).bind_paths(temp_path, final_path)
    provenance = RecordingProvenanceService()
    return (
        UploadPersistenceService(upload, provenance),
        provenance,
        temp_path,
        final_path,
    )


def test_upload_persistence_route_remains_canonical(app):
    assert app.view_functions['upload.save_document'].__module__ == (
        'app.routes.upload.persistence'
    )


def test_persist_reviewed_upload_normalizes_metadata_and_temporal_year(
    db_session, test_user, tmp_path
):
    from app.models.document import Document
    from app.models.temporal_experiment import DocumentTemporalMetadata

    service, provenance, temp_path, final_path = _service(tmp_path)
    result = service.persist_reviewed_upload(
        {
            'metadata': {
                'title': 'Reviewed Paper',
                'authors': ['Ada Lovelace', 'Alan Turing'],
                'publication_year': '2020-05',
                'access_date': '2024-06-15',
                'journal': '',
                'doi': '10.1000/reviewed',
                'abstract': 'An abstract.',
                'discipline': 'computer science',
            },
            'provenance': {
                'title': {
                    'source': 'crossref',
                    'raw_value': 'Reviewed Paper',
                },
                'authors': {
                    'source': 'manual',
                    'raw_value': ['Ada Lovelace', 'Alan Turing'],
                },
                'match_score': {'raw_value': 0.87},
            },
            'temp_path': str(temp_path),
            'filename': 'reviewed.pdf',
        },
        test_user,
        str(tmp_path),
    )

    document = db_session.get(Document, result['document_id'])
    temporal = DocumentTemporalMetadata.query.filter_by(
        document_id=document.id
    ).one()
    assert document.title == 'Reviewed Paper'
    assert document.authors == 'Ada Lovelace, Alan Turing'
    assert document.publication_date.isoformat() == '2020-05-01'
    assert document.access_date.isoformat() == '2024-06-15'
    assert document.journal is None
    assert document.file_path == str(final_path)
    assert document.content == 'Extracted document text.'
    assert temporal.publication_year == 2020
    assert temporal.discipline == 'computer science'
    call_names = [call[0] for call in provenance.calls]
    assert call_names[0:2] == [
        'track_document_upload',
        'track_text_extraction',
    ]
    assert call_names[-1] == 'track_document_save'
    extraction_calls = [
        call for call in provenance.calls
        if call[0] == 'track_metadata_extraction'
    ]
    assert {call[1][2] for call in extraction_calls} == {
        'crossref',
        'manual',
    }
    crossref_call = next(call for call in extraction_calls if call[1][2] == 'crossref')
    assert crossref_call[1][4] == 0.87


def test_extraction_failure_removes_moved_permanent_file(
    db_session, test_user, tmp_path
):
    import pytest

    from app.models.document import Document
    from app.services.base_service import ValidationError

    service, _, temp_path, final_path = _service(
        tmp_path,
        extraction_error='Unreadable PDF',
    )

    with pytest.raises(ValidationError, match='Unreadable PDF'):
        service.persist_reviewed_upload(
            {
                'metadata': {'title': 'Unreadable'},
                'temp_path': str(temp_path),
                'filename': 'unreadable.pdf',
            },
            test_user,
            str(tmp_path),
        )

    assert final_path.exists() is False
    assert Document.query.filter_by(title='Unreadable').count() == 0


def test_provenance_failure_does_not_undo_document(
    db_session, test_user, tmp_path
):
    from app.models.document import Document
    from app.services.upload_persistence_service import UploadPersistenceService

    service, _, temp_path, final_path = _service(tmp_path)

    class FailingProvenance:
        def track_document_upload(self, document, user):
            raise RuntimeError('Provenance unavailable')

    service = UploadPersistenceService(service.upload_service, FailingProvenance())
    result = service.persist_reviewed_upload(
        {
            'metadata': {'title': 'Saved despite provenance'},
            'temp_path': str(temp_path),
            'filename': 'saved.pdf',
        },
        test_user,
        str(tmp_path),
    )

    assert db_session.get(Document, result['document_id']) is not None
    assert final_path.exists() is True


def test_upload_persistence_validates_payload(test_user, tmp_path):
    import pytest

    from app.services.base_service import ValidationError

    service, _, temp_path, _ = _service(tmp_path)
    cases = [
        (None, 'No data provided'),
        ({'metadata': {'title': 'Title'}}, 'No document file to save'),
        ({'temp_path': str(temp_path), 'metadata': {}}, 'Title is required'),
    ]
    for payload, message in cases:
        with pytest.raises(ValidationError, match=message):
            service.persist_reviewed_upload(
                payload,
                test_user,
                str(tmp_path),
            )


def test_save_document_route_delegates_and_returns_success(
    auth_client, monkeypatch
):
    from app.routes.upload import persistence

    calls = []

    def persist(self, data, user, upload_dir):
        calls.append((data, user.id, upload_dir))
        return {
            'success': True,
            'message': 'Document saved successfully',
            'document_id': 42,
            'document_uuid': '00000000-0000-0000-0000-000000000042',
        }

    monkeypatch.setattr(
        persistence.UploadPersistenceService,
        'persist_reviewed_upload',
        persist,
    )
    response = auth_client.post(
        '/upload/save_document',
        json={
            'metadata': {'title': 'Delegated'},
            'temp_path': '/tmp/delegated.pdf',
        },
    )

    assert response.status_code == 200
    assert response.get_json()['document_id'] == 42
    assert calls and calls[0][0]['metadata']['title'] == 'Delegated'


def test_save_document_route_maps_validation(auth_client):
    response = auth_client.post(
        '/upload/save_document',
        json={'metadata': {'title': 'No file'}},
    )

    assert response.status_code == 400
    assert response.get_json()['error'] == 'No document file to save'
