"""Regression coverage for pasted-text and compatibility file input."""

from io import BytesIO
from types import SimpleNamespace

import pytest
from werkzeug.datastructures import FileStorage


class FakeFileHandler:
    def __init__(self, content='Extracted file content.'):
        self.content = content

    @staticmethod
    def get_file_extension(filename):
        return filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''

    def extract_text_from_file(self, file_path, original_filename):
        return self.content


def _service(content='Extracted file content.'):
    from app.services.document_input_service import DocumentInputService

    return DocumentInputService(
        file_handler=FakeFileHandler(content),
        language_detector=lambda text: ('en', 0.98),
        uuid_factory=lambda: SimpleNamespace(hex='fixed-id'),
    )


def _file(filename='sample.txt', content=b'file bytes'):
    return FileStorage(stream=BytesIO(content), filename=filename)


def test_document_input_routes_remain_canonical(app):
    expected = 'app.routes.text_input.forms'
    for endpoint in (
        'text_input.upload_form',
        'text_input.paste_form',
        'text_input.submit_text',
        'text_input.upload_file',
    ):
        assert app.view_functions[endpoint].__module__ == expected


def test_create_text_trims_content_and_generates_title(
    db_session, test_user
):
    document = _service().create_text(
        {'title': '  ', 'content': '  First line\nSecond line  '},
        test_user.id,
    )

    assert document.title == 'First line'
    assert document.content == 'First line\nSecond line'
    assert document.content_type == 'text'
    assert document.detected_language == 'en'
    assert document.language_confidence == 0.98
    assert document.word_count == 4
    assert document.character_count == len(document.content)
    assert db_session.get(type(document), document.id) is document


def test_create_text_truncates_long_first_line(test_user):
    first_line = 'A' * 60
    document = _service().create_text(
        {'content': f'{first_line}\nMore'},
        test_user.id,
    )
    assert document.title == ('A' * 50) + '...'


@pytest.mark.parametrize('payload', [None, {}, {'content': ''}, {'content': 42}])
def test_create_text_requires_string_content(test_user, payload):
    from app.services.base_service import ValidationError

    with pytest.raises(ValidationError, match='Content is required'):
        _service().create_text(payload, test_user.id)


def test_create_file_persists_extracted_document(
    db_session, test_user, tmp_path
):
    document = _service().create_file(
        _file('Research Notes.TXT'),
        '  Custom title  ',
        test_user.id,
        str(tmp_path),
        {'txt', 'pdf'},
    )

    assert document.title == 'Custom title'
    assert document.original_filename == 'Research Notes.TXT'
    assert document.file_type == 'txt'
    assert document.file_path.endswith('fixed-id_Research_Notes.TXT')
    assert document.content == 'Extracted file content.'
    assert document.file_size == len(b'file bytes')
    assert (tmp_path / 'fixed-id_Research_Notes.TXT').exists()
    assert db_session.get(type(document), document.id) is document


def test_create_file_uses_filename_title(test_user, tmp_path):
    document = _service().create_file(
        _file('source.document.md'),
        '',
        test_user.id,
        str(tmp_path),
        {'md'},
    )
    assert document.title == 'source.document'


def test_create_file_rejects_missing_and_disallowed_files(test_user, tmp_path):
    from app.services.base_service import ValidationError

    service = _service()
    with pytest.raises(ValidationError, match='No file selected'):
        service.create_file(None, '', test_user.id, str(tmp_path), {'txt'})
    with pytest.raises(ValidationError, match='File type not allowed'):
        service.create_file(
            _file('malware.exe'),
            '',
            test_user.id,
            str(tmp_path),
            {'txt', 'pdf'},
        )
    assert list(tmp_path.iterdir()) == []


def test_extraction_failure_removes_saved_file(test_user, tmp_path):
    from app.services.base_service import ValidationError

    with pytest.raises(ValidationError, match='Could not extract text'):
        _service(content=None).create_file(
            _file(),
            '',
            test_user.id,
            str(tmp_path),
            {'txt'},
        )
    assert list(tmp_path.iterdir()) == []


def test_database_failure_removes_saved_file(
    test_user, tmp_path, monkeypatch
):
    from app import db

    def fail_commit():
        raise RuntimeError('Database unavailable')

    monkeypatch.setattr(db.session, 'commit', fail_commit)
    with pytest.raises(RuntimeError, match='Database unavailable'):
        _service().create_file(
            _file(),
            '',
            test_user.id,
            str(tmp_path),
            {'txt'},
        )
    assert list(tmp_path.iterdir()) == []


def test_submit_text_json_contract(auth_client):
    response = auth_client.post(
        '/input/submit_text',
        json={'title': '', 'content': 'Submitted through JSON.'},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['success'] is True
    assert payload['message'] == 'Text submitted successfully'
    assert payload['redirect_url'].startswith('/input/document/')


def test_submit_text_form_redirect_and_validation(auth_client):
    success = auth_client.post(
        '/input/submit_text',
        data={'title': 'Form text', 'content': 'Submitted through a form.'},
    )
    invalid_json = auth_client.post('/input/submit_text', json={'content': ''})
    invalid_form = auth_client.post('/input/submit_text', data={'content': ''})

    assert success.status_code == 302
    assert '/input/document/' in success.headers['Location']
    assert invalid_json.status_code == 400
    assert invalid_json.get_json()['error'] == 'Content is required'
    assert invalid_form.status_code == 302
    assert invalid_form.headers['Location'].endswith('/input/paste')


def test_upload_file_json_and_form_contracts(auth_client, tmp_path):
    auth_client.application.config['UPLOAD_FOLDER'] = str(tmp_path)
    json_error = auth_client.post('/input/upload_file', json={})
    form_success = auth_client.post(
        '/input/upload_file',
        data={
            'title': 'Uploaded text',
            'file': (BytesIO(b'Plain text upload.'), 'upload.txt'),
        },
        content_type='multipart/form-data',
    )
    disallowed = auth_client.post(
        '/input/upload_file',
        data={'file': (BytesIO(b'binary'), 'bad.exe')},
        content_type='multipart/form-data',
    )

    assert json_error.status_code == 400
    assert json_error.get_json()['error'] == 'No file selected'
    assert form_success.status_code == 302
    assert '/input/document/' in form_success.headers['Location']
    assert disallowed.status_code == 302
    assert disallowed.headers['Location'].endswith('/upload/')


def test_document_input_writes_require_authentication(app):
    client = app.test_client()
    text = client.post('/input/submit_text', json={'content': 'text'})
    file = client.post('/input/upload_file', json={})

    assert text.status_code == 401
    assert file.status_code == 401


def test_input_pages_keep_existing_navigation(auth_client):
    assert auth_client.get('/input/').headers['Location'].endswith('/upload/')
    assert auth_client.get('/input/upload').headers['Location'].endswith('/upload/')
    assert auth_client.get('/input/paste').status_code == 200
