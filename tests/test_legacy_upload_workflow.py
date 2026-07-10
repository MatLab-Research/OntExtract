"""Regression coverage for the direct multipart upload compatibility flow."""

from io import BytesIO

from werkzeug.datastructures import FileStorage, MultiDict


class FakeFileHandler:
    def __init__(self, path, content='Extracted text'):
        self.path = path
        self.content = content

    def save_file(self, file, upload_folder=None):
        self.path.write_bytes(file.stream.read())
        return str(self.path), self.path.stat().st_size

    def extract_text_from_file(self, path, filename):
        return self.content

    @staticmethod
    def get_file_extension(filename):
        return filename.rsplit('.', 1)[-1].lower()


class RecordingProcessingService:
    def __init__(self, error=None):
        self.documents = []
        self.error = error

    def process_document(self, document):
        self.documents.append(document)
        if self.error:
            raise RuntimeError(self.error)
        document.status = 'completed'


class RecordingProvenance:
    def __init__(self):
        self.calls = []

    def track_document_upload(self, document, user, experiment=None):
        self.calls.append((document.id, user.id, experiment.id if experiment else None))


def _file(name='uploaded.txt', content=b'Uploaded content'):
    return FileStorage(stream=BytesIO(content), filename=name)


def _workflow(tmp_path, **kwargs):
    from app.services.legacy_upload_workflow import LegacyUploadWorkflow

    path = tmp_path / kwargs.pop('filename', 'saved.txt')
    processing = kwargs.pop('processing', RecordingProcessingService())
    provenance = kwargs.pop('provenance', RecordingProvenance())
    workflow = LegacyUploadWorkflow(
        file_handler=kwargs.pop('file_handler', FakeFileHandler(path)),
        processing_service=processing,
        provenance_service=provenance,
        language_detector=kwargs.pop(
            'language_detector',
            lambda content: ('en', 0.99),
        ),
        **kwargs,
    )
    return workflow, processing, provenance, path


def test_legacy_upload_route_remains_canonical(app):
    assert app.view_functions['upload.upload_document'].__module__ == (
        'app.routes.upload.legacy'
    )


def test_legacy_upload_normalizes_document_metadata(
    db_session, test_user, tmp_path
):
    workflow, processing, provenance, path = _workflow(tmp_path)
    outcome = workflow.upload(
        _file(),
        MultiDict({
            'title': 'Direct Upload',
            'prov_type': 'prov:Entity/SourceDocument',
            'authors': 'Ada Lovelace',
            'publication_date': '1843',
            'access_date': '2025-04-02',
            'doi': '10.1000/direct',
            'auto_detect_language': 'on',
        }),
        test_user,
        str(tmp_path),
    )

    document = outcome['document']
    assert document.title == 'Direct Upload'
    assert document.document_type == 'document'
    assert document.file_path == str(path)
    assert document.content == 'Extracted text'
    assert document.publication_date.isoformat() == '1843-01-01'
    assert document.access_date.isoformat() == '2025-04-02'
    assert document.detected_language == 'en'
    assert document.language_confidence == 0.99
    assert document.source_metadata['prov_type'] == (
        'prov:Entity/SourceDocument'
    )
    assert processing.documents == [document]
    assert provenance.calls == [(document.id, test_user.id, None)]
    assert outcome['processing_warning'] is None


def test_legacy_upload_classifies_reference_and_enriches_zotero(
    test_user, tmp_path
):
    class Enricher:
        def __init__(self, use_zotero):
            assert use_zotero is True

        def extract_with_zotero(self, *args, **kwargs):
            return {
                'zotero_key': 'ABC123',
                'zotero_match_score': 0.92,
                'title': 'Do not overwrite normalized title',
            }

    workflow, _, _, _ = _workflow(
        tmp_path,
        filename='paper.pdf',
        enricher_factory=Enricher,
    )
    outcome = workflow.upload(
        _file('paper.pdf'),
        MultiDict({
            'title': 'Academic Paper',
            'prov_type': 'prov:Entity/AcademicPaper',
            'check_zotero': 'on',
        }),
        test_user,
        str(tmp_path),
    )

    document = outcome['document']
    assert document.document_type == 'reference'
    assert document.reference_subtype == 'academic'
    assert document.title == 'Academic Paper'
    assert document.source_metadata['zotero_key'] == 'ABC123'


def test_legacy_upload_links_source_document_canonically(
    db_session, test_user, temporal_experiment, tmp_path
):
    from app.models.experiment_document import ExperimentDocument

    workflow, _, provenance, _ = _workflow(tmp_path)
    outcome = workflow.upload(
        _file(),
        MultiDict({
            'title': 'Experiment source',
            'experiment_id': str(temporal_experiment.id),
            'prov_type': 'prov:Entity/SourceDocument',
        }),
        test_user,
        str(tmp_path),
    )

    document = outcome['document']
    assert outcome['linked_experiment'] is temporal_experiment
    assert temporal_experiment.documents.filter_by(id=document.id).count() == 1
    assert ExperimentDocument.query.filter_by(
        experiment_id=temporal_experiment.id,
        document_id=document.id,
    ).count() == 1
    assert provenance.calls == [
        (document.id, test_user.id, temporal_experiment.id)
    ]


def test_legacy_upload_links_reference_with_include_flag(
    db_session, test_user, temporal_experiment, tmp_path
):
    from app.models.experiment import experiment_references

    workflow, _, _, _ = _workflow(tmp_path)
    outcome = workflow.upload(
        _file(),
        MultiDict({
            'title': 'Experiment reference',
            'experiment_id': str(temporal_experiment.id),
            'prov_type': 'prov:Entity/Reference',
            'include_in_analysis': 'true',
        }),
        test_user,
        str(tmp_path),
    )

    row = db_session.execute(
        db_session.query(experiment_references).filter(
            experiment_references.c.experiment_id == temporal_experiment.id,
            experiment_references.c.reference_id == outcome['document'].id,
        ).statement
    ).first()
    assert row is not None
    assert row.include_in_analysis is True


def test_processing_failure_is_reported_without_losing_document(
    db_session, test_user, tmp_path
):
    from app.models.document import Document

    workflow, _, _, path = _workflow(
        tmp_path,
        processing=RecordingProcessingService('Processor unavailable'),
    )
    outcome = workflow.upload(
        _file(),
        MultiDict({'title': 'Saved before processing'}),
        test_user,
        str(tmp_path),
    )

    assert outcome['processing_warning'] == 'Processor unavailable'
    assert db_session.get(Document, outcome['document'].id) is not None
    assert path.exists() is True


def test_precommit_failure_removes_saved_file(test_user, tmp_path):
    import pytest

    class FailingFileHandler(FakeFileHandler):
        def extract_text_from_file(self, path, filename):
            raise RuntimeError('Extraction exploded')

    path = tmp_path / 'failed.txt'
    workflow, _, _, _ = _workflow(
        tmp_path,
        file_handler=FailingFileHandler(path),
    )

    with pytest.raises(RuntimeError, match='Extraction exploded'):
        workflow.upload(
            _file(),
            MultiDict({'title': 'Failure'}),
            test_user,
            str(tmp_path),
        )

    assert path.exists() is False


def test_legacy_upload_route_redirects_to_document(
    auth_client, monkeypatch, sample_document
):
    from app.routes.upload import legacy

    monkeypatch.setattr(
        legacy.LegacyUploadWorkflow,
        'upload',
        lambda self, file, form, user, upload_folder: {
            'document': sample_document,
            'processing_warning': None,
            'linked_experiment': None,
        },
    )
    response = auth_client.post(
        '/upload/document',
        data={'file': (BytesIO(b'text'), 'route.txt'), 'title': 'Route'},
        content_type='multipart/form-data',
    )

    assert response.status_code == 302
    assert str(sample_document.uuid) in response.headers['Location']


def test_legacy_upload_route_redirects_linked_experiment(
    auth_client, monkeypatch, sample_document, temporal_experiment
):
    from app.routes.upload import legacy

    monkeypatch.setattr(
        legacy.LegacyUploadWorkflow,
        'upload',
        lambda self, file, form, user, upload_folder: {
            'document': sample_document,
            'processing_warning': 'Optional processing failed',
            'linked_experiment': temporal_experiment,
        },
    )
    response = auth_client.post(
        '/upload/document',
        data={'file': (BytesIO(b'text'), 'route.txt')},
        content_type='multipart/form-data',
    )

    assert response.status_code == 302
    assert response.headers['Location'].endswith(
        f'/experiments/{temporal_experiment.id}'
    )
