"""Regression coverage for SSE upload metadata extraction."""

import json
import threading
import time
from io import BytesIO
from types import SimpleNamespace

from flask import has_app_context
from werkzeug.datastructures import FileStorage


class FakeUploadService:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.cleaned = []
        self.extraction_calls = []

    @staticmethod
    def save_to_temp(file):
        return SimpleNamespace(
            success=True,
            temp_path='/tmp/streamed-paper.pdf',
            filename=file.filename,
            error=None,
        )

    def extract_metadata_from_pdf_streaming(self, path, progress_callback):
        self.extraction_calls.append((path, has_app_context()))
        progress_callback('Analyzing PDF')
        progress_callback('Checking CrossRef')
        if self.error:
            raise self.error
        return self.result

    def cleanup_temp(self, path):
        self.cleaned.append(path)


def _file(filename='paper.pdf'):
    return FileStorage(stream=BytesIO(b'pdf'), filename=filename)


def _events(stream):
    events = []
    for frame in stream:
        assert frame.startswith('data: ')
        events.append(json.loads(frame[6:].strip()))
    return events


def _result(**metadata):
    from app.services.upload_service import MetadataExtractionResult

    values = {
        'title': 'Matched Paper',
        'authors': 'Ada Lovelace',
        'extracted_title': 'PDF Paper',
        'extracted_authors': 'PDF Author',
        'extraction_method': 'title_from_pdf',
        'confidence_level': 'high',
        'confidence_value': 0.92,
    }
    values.update(metadata)
    return MetadataExtractionResult(
        success=True,
        metadata=values,
        source='crossref',
        progress=['Analyzing PDF', 'Checking CrossRef'],
    )


def test_streaming_route_remains_canonical(app):
    assert app.view_functions['upload.extract_metadata_stream'].__module__ == (
        'app.routes.upload.streaming'
    )


def test_shared_workflow_builds_complete_streaming_review_payload():
    from app.services.upload_metadata_workflow import UploadMetadataWorkflow

    workflow = UploadMetadataWorkflow(
        upload_service=SimpleNamespace(),
        logger=SimpleNamespace(),
    )
    payload = workflow.build_streaming_payload(
        _result(),
        '/tmp/review.pdf',
        'review.pdf',
        title='User title',
        enable_crossref=True,
    )

    assert payload['success'] is True
    assert payload['metadata']['title'] == 'Matched Paper'
    assert payload['metadata']['filename'] == 'review.pdf'
    assert payload['temp_path'] == '/tmp/review.pdf'
    assert payload['crossref_enabled'] is True
    assert payload['crossref_found'] is True
    assert payload['extraction_method'] == 'title_from_pdf'
    assert payload['confidence_level'] == 'high'
    assert payload['match_score'] == 0.92
    assert payload['pdf_extracted_metadata'] == {
        'title': 'PDF Paper',
        'authors': 'PDF Author',
    }
    assert payload['provenance']['title']['source'] == 'crossref'
    assert payload['provenance']['filename']['source'] == 'file'
    assert 'Please review' in payload['message']


def test_shared_workflow_preserves_fallback_pdf_metadata():
    from app.services.upload_metadata_workflow import UploadMetadataWorkflow
    from app.services.upload_service import MetadataExtractionResult

    result = MetadataExtractionResult(
        success=False,
        metadata={'title': 'Embedded PDF Title', 'authors': 'PDF Author'},
        source='pdf_analysis',
        error='No external match',
        progress=['Using PDF metadata'],
    )
    payload = UploadMetadataWorkflow(
        SimpleNamespace(),
        SimpleNamespace(),
    ).build_streaming_payload(
        result,
        '/tmp/fallback.pdf',
        'fallback.pdf',
        enable_crossref=True,
    )

    assert payload['metadata'] == {'filename': 'fallback.pdf'}
    assert payload['crossref_found'] is False
    assert payload['pdf_extracted_title'] == 'Embedded PDF Title'
    assert payload['pdf_extracted_metadata']['authors'] == 'PDF Author'
    assert 'No CrossRef match found' in payload['message']


def test_shared_workflow_accepts_dictionary_result():
    from app.services.upload_metadata_workflow import UploadMetadataWorkflow

    payload = UploadMetadataWorkflow(
        SimpleNamespace(),
        SimpleNamespace(),
    ).build_streaming_payload(
        {
            'success': True,
            'metadata': {'title': 'Dictionary Result'},
            'progress': ['Complete'],
        },
        '/tmp/dictionary.pdf',
        'dictionary.pdf',
        enable_crossref=False,
    )
    assert payload['metadata']['title'] == 'Dictionary Result'
    assert payload['progress'] == ['Complete']
    assert payload['crossref_enabled'] is False
    assert payload['message'] == (
        'Document uploaded. Please review metadata before saving.'
    )


def test_stream_emits_progress_and_completion_under_app_context(app):
    from app.services.streaming_metadata_service import StreamingMetadataService

    upload = FakeUploadService(_result())
    service = StreamingMetadataService(
        upload,
        SimpleNamespace(),
        heartbeat_seconds=0.01,
    )
    events = _events(service.create_stream(
        _file(),
        'User title',
        True,
        app,
    ))

    assert [event['type'] for event in events] == [
        'progress',
        'progress',
        'complete',
    ]
    assert events[0]['message'] == 'Analyzing PDF'
    assert events[-1]['data']['metadata']['title'] == 'Matched Paper'
    assert upload.extraction_calls == [('/tmp/streamed-paper.pdf', True)]
    assert upload.cleaned == []


def test_crossref_disabled_skips_extraction_and_transfers_temp_ownership(app):
    from app.services.streaming_metadata_service import StreamingMetadataService

    upload = FakeUploadService()
    events = _events(StreamingMetadataService(
        upload,
        SimpleNamespace(),
        heartbeat_seconds=0.01,
    ).create_stream(_file(), '', False, app))

    assert [event['type'] for event in events] == ['complete']
    payload = events[0]['data']
    assert payload['metadata'] == {'filename': 'paper.pdf'}
    assert payload['crossref_enabled'] is False
    assert upload.extraction_calls == []
    assert upload.cleaned == []


def test_extraction_error_emits_error_and_cleans_temp_file(app):
    from app.services.streaming_metadata_service import StreamingMetadataService

    upload = FakeUploadService(error=RuntimeError('CrossRef unavailable'))
    events = _events(StreamingMetadataService(
        upload,
        SimpleNamespace(),
        heartbeat_seconds=0.01,
    ).create_stream(_file(), '', True, app))

    assert [event['type'] for event in events] == [
        'progress',
        'progress',
        'error',
    ]
    assert events[-1]['message'] == 'CrossRef unavailable'
    assert '/tmp/streamed-paper.pdf' in upload.cleaned


def test_abandoned_stream_cleans_temp_file(app):
    from app.services.streaming_metadata_service import StreamingMetadataService

    release = threading.Event()

    class BlockingUpload(FakeUploadService):
        def extract_metadata_from_pdf_streaming(self, path, progress_callback):
            progress_callback('Started')
            release.wait(timeout=1)
            return _result()

    upload = BlockingUpload()
    stream = StreamingMetadataService(
        upload,
        SimpleNamespace(),
        heartbeat_seconds=0.01,
        join_timeout=0.01,
    ).create_stream(_file(), '', True, app)
    first = json.loads(next(stream)[6:].strip())
    assert first == {'type': 'progress', 'message': 'Started'}
    stream.close()
    release.set()
    time.sleep(0.03)
    assert '/tmp/streamed-paper.pdf' in upload.cleaned


def test_streaming_route_returns_sse_headers_and_completion(
    auth_client, monkeypatch
):
    from app.routes.upload import streaming

    upload = FakeUploadService(_result())
    monkeypatch.setattr(streaming, 'upload_service', upload)
    response = auth_client.post(
        '/upload/extract_metadata_stream',
        data={
            'document_file': (BytesIO(b'pdf'), 'route.pdf'),
            'title': 'Route title',
            'enable_crossref': 'true',
        },
        content_type='multipart/form-data',
    )

    assert response.status_code == 200
    assert response.mimetype == 'text/event-stream'
    assert response.headers['Cache-Control'] == 'no-cache'
    assert response.headers['X-Accel-Buffering'] == 'no'
    frames = [
        json.loads(part[6:])
        for part in response.get_data(as_text=True).strip().split('\n\n')
    ]
    assert frames[-1]['type'] == 'complete'
    assert frames[-1]['data']['metadata']['filename'] == 'route.pdf'


def test_streaming_route_maps_validation(auth_client):
    missing = auth_client.post('/upload/extract_metadata_stream', data={})
    assert missing.status_code == 400
    assert missing.get_json()['error'] == 'No file uploaded'


def test_streaming_route_requires_authentication(app):
    anonymous = app.test_client().post('/upload/extract_metadata_stream', data={})
    assert anonymous.status_code == 401


def test_streaming_client_propagates_server_error_message():
    from pathlib import Path

    template = (
        Path(__file__).resolve().parents[1]
        / 'app/templates/text_input/upload_enhanced.html'
    ).read_text()
    assert "streamError = data.message || 'Metadata extraction failed'" in template
    assert 'if (streamError)' in template
    assert 'throw new Error(streamError)' in template
