"""Regression coverage for standalone document embedding orchestration."""

from datetime import date


class FakeEmbeddingService:
    def __init__(self, provider_priority, calls, fail=False):
        self.provider_priority = provider_priority
        self.calls = calls
        self.fail = fail

    def get_embedding(self, text):
        self.calls.append(text)
        if self.fail:
            raise RuntimeError('Embedding provider failed')
        return [0.1, 0.2, 0.3]

    def get_model_name(self):
        return 'fake:model'

    def get_dimension(self):
        return 3


class RecordingProvenance:
    def __init__(self):
        self.calls = []

    def track_embedding_generation(self, *args, **kwargs):
        self.calls.append((args, kwargs))


def _workflow(calls, provenance=None, fail=False, period_service=None):
    from app.services.document_embedding_workflow import DocumentEmbeddingWorkflow

    return DocumentEmbeddingWorkflow(
        embedding_service_factory=lambda priority: FakeEmbeddingService(
            priority,
            calls,
            fail=fail,
        ),
        period_service_factory=(lambda: period_service),
        provenance_service=provenance or RecordingProvenance(),
        timer=lambda: 10.0,
    )


def test_embedding_route_remains_in_canonical_module(app):
    assert app.view_functions['processing.generate_embeddings'].__module__ == (
        'app.routes.processing.embeddings'
    )


def test_manual_embedding_creates_version_and_completed_job(
    db_session, sample_document, test_user
):
    from app.models.document import Document
    from app.models.processing_job import ProcessingJob

    calls = []
    provenance = RecordingProvenance()
    workflow = _workflow(calls, provenance)
    result = workflow.generate(sample_document, {'method': 'local'}, test_user)

    version = db_session.get(Document, result['processing_version_id'])
    job = db_session.get(ProcessingJob, result['job_id'])
    assert version.id != sample_document.id
    assert version.version_type == 'processed'
    assert job.document_id == version.id
    assert job.status == 'completed'
    assert job.get_parameters()['original_document_id'] == sample_document.id
    assert job.get_result_data()['embedding_dimensions'] == 3
    assert job.get_result_data()['chunk_count'] == 1
    assert calls == [version.content]
    assert len(provenance.calls) == 1
    assert result['latest_version_id'] == version.id
    assert result['redirect_url'] == f'/input/document/{version.id}'


def test_embedding_chunks_long_documents(
    db_session, sample_document, test_user
):
    sample_document.content = 'x' * 17000
    db_session.commit()
    calls = []

    result = _workflow(calls).generate(
        sample_document,
        {'method': 'local'},
        test_user,
    )

    from app.models.processing_job import ProcessingJob

    job = db_session.get(ProcessingJob, result['job_id'])
    assert [len(chunk) for chunk in calls] == [8000, 8000, 1000]
    assert job.get_result_data()['chunk_count'] == 3
    assert job.get_result_data()['total_embeddings'] == 3


def test_experiment_embedding_reuses_experiment_version(
    db_session, sample_document, temporal_experiment, test_user
):
    calls = []
    workflow = _workflow(calls)
    first = workflow.generate(
        sample_document,
        {'method': 'local', 'experiment_id': temporal_experiment.id},
        test_user,
    )
    second = workflow.generate(
        sample_document,
        {'method': 'local', 'experiment_id': temporal_experiment.id},
        test_user,
    )

    assert first['processing_version_id'] == second['processing_version_id']
    assert first['processing_version_id'] != sample_document.id


def test_period_aware_embedding_records_selection_metadata(
    db_session, sample_document, test_user
):
    class PeriodService:
        def __init__(self):
            self.kwargs = None

        def select_model_for_period(self, **kwargs):
            self.kwargs = kwargs
            return {
                'model': 'historical-model',
                'selection_reason': 'Publication year',
                'selection_confidence': 0.9,
                'era': 'historical',
                'domain': kwargs['domain'],
                'handles_archaic': True,
            }

    sample_document.publication_date = date(1890, 1, 1)
    db_session.commit()
    period_service = PeriodService()
    workflow = _workflow([], period_service=period_service)
    result = workflow.generate(
        sample_document,
        {
            'method': 'period_aware',
            'model_preference': 'scientific',
            'auto_detect_period': True,
        },
        test_user,
    )

    from app.models.processing_job import ProcessingJob

    job = db_session.get(ProcessingJob, result['job_id'])
    period_data = job.get_result_data()['period_aware']
    assert period_service.kwargs['year'] == 1890
    assert period_service.kwargs['domain'] == 'scientific'
    assert period_service.kwargs['text_sample']
    assert period_data['selected_model'] == 'historical-model'
    assert period_data['detected_year'] == 1890


def test_embedding_failure_persists_failed_job(
    db_session, sample_document, test_user
):
    import pytest

    from app.models.processing_job import ProcessingJob

    workflow = _workflow([], fail=True)
    with pytest.raises(RuntimeError, match='Embedding provider failed'):
        workflow.generate(sample_document, {'method': 'local'}, test_user)

    job = ProcessingJob.query.order_by(ProcessingJob.id.desc()).first()
    assert job.status == 'failed'
    assert job.get_result_data()['error'] == 'Embedding provider failed'
    assert job.get_result_data()['embedding_method'] == 'local'


def test_embedding_workflow_validates_method_and_content(
    db_session, sample_document, test_user
):
    import pytest

    from app.services.base_service import ValidationError

    workflow = _workflow([])
    with pytest.raises(ValidationError, match='Invalid embedding method'):
        workflow.generate(sample_document, {'method': 'huggingface'}, test_user)

    sample_document.content = ''
    db_session.commit()
    with pytest.raises(ValidationError, match='Document has no content'):
        workflow.generate(sample_document, {'method': 'local'}, test_user)


def test_embedding_lookup_supports_uuid_and_existing_numeric_caller(
    sample_document,
):
    from app.services.document_embedding_workflow import DocumentEmbeddingWorkflow

    assert DocumentEmbeddingWorkflow.get_document(str(sample_document.uuid)).id == (
        sample_document.id
    )
    assert DocumentEmbeddingWorkflow.get_document(str(sample_document.id)).id == (
        sample_document.id
    )


def test_embedding_route_maps_validation_and_not_found(auth_client):
    invalid_method = auth_client.post(
        '/process/document/999999/embeddings',
        json={'method': 'huggingface'},
    )
    missing = auth_client.post(
        '/process/document/not-a-document/embeddings',
        json={'method': 'local'},
    )

    assert invalid_method.status_code == 404
    assert missing.status_code == 404


def test_embedding_workflow_requires_document_and_experiment_permissions(
    db_session, sample_document, test_user, admin_user, temporal_experiment
):
    import pytest

    from app.services.base_service import PermissionError

    stranger = type(test_user)(
        username='embedding-stranger',
        email='embedding-stranger@example.com',
        password='password',
        account_status='active',
    )
    db_session.add(stranger)
    db_session.commit()
    calls = []
    workflow = _workflow(calls)
    with pytest.raises(PermissionError):
        workflow.generate(sample_document, {'method': 'local'}, stranger)
    with pytest.raises(PermissionError):
        workflow.generate(
            sample_document,
            {'method': 'local', 'experiment_id': temporal_experiment.id},
            stranger,
        )
    result = workflow.generate(sample_document, {'method': 'local'}, admin_user)
    assert result['success'] is True


def test_embedding_workflow_rejects_missing_or_invalid_experiment_before_writes(
    db_session, sample_document, test_user
):
    import pytest

    from app.models.document import Document
    from app.models.processing_job import ProcessingJob
    from app.services.base_service import NotFoundError

    baseline_documents = Document.query.count()
    baseline_jobs = ProcessingJob.query.count()
    for experiment_id in ('not-an-id', 999999):
        with pytest.raises(NotFoundError, match='Experiment not found'):
            _workflow([]).generate(
                sample_document,
                {'method': 'local', 'experiment_id': experiment_id},
                test_user,
            )
    assert Document.query.count() == baseline_documents
    assert ProcessingJob.query.count() == baseline_jobs


def test_embedding_result_includes_compatibility_summary(
    sample_document, test_user
):
    result = _workflow([]).generate(
        sample_document,
        {'method': 'local'},
        test_user,
    )
    assert result['embedding_info'] == {
        'type': 'single',
        'chunks': 1,
        'chunk_size': 8000,
        'model': 'fake:model',
        'dimension': 3,
    }


def test_embedding_routes_require_owner_or_admin(
    app, db_session, sample_document
):
    from app.models.user import User

    stranger = User(
        username='embedding-route-stranger',
        email='embedding-route-stranger@example.com',
        password='password',
        account_status='active',
    )
    db_session.add(stranger)
    db_session.commit()
    client = app.test_client()
    with client.session_transaction() as session:
        session['_user_id'] = str(stranger.id)
        session['_fresh'] = True
    canonical = client.post(
        f'/process/document/{sample_document.uuid}/embeddings',
        json={'method': 'local'},
    )
    legacy = client.post(
        f'/input/documents/{sample_document.id}/apply_embeddings'
    )
    assert canonical.status_code == 403
    assert legacy.status_code == 403


def test_legacy_embedding_route_delegates_and_preserves_response(
    auth_client, test_user, sample_document, monkeypatch
):
    from app.routes.text_input import processing

    calls = []

    class Workflow:
        def __init__(self, workflow_logger):
            self.logger = workflow_logger

        @staticmethod
        def get_document(document_id):
            calls.append(('lookup', document_id))
            return sample_document

        @staticmethod
        def generate(document, data, user):
            calls.append(('generate', document.id, data, user.id))
            return {
                'embedding_info': {
                    'type': 'single',
                    'chunks': 1,
                    'chunk_size': 8000,
                    'model': 'fake:model',
                    'dimension': 3,
                }
            }

    monkeypatch.setattr(processing, 'DocumentEmbeddingWorkflow', Workflow)
    response = auth_client.post(
        f'/input/documents/{sample_document.id}/apply_embeddings'
    )
    assert response.status_code == 200
    assert response.get_json() == {
        'success': True,
        'message': 'Embeddings applied successfully',
        'embedding_info': {
            'type': 'single',
            'chunks': 1,
            'chunk_size': 8000,
            'model': 'fake:model',
            'dimension': 3,
        },
    }
    assert calls == [
        ('lookup', sample_document.id),
        ('generate', sample_document.id, {'method': 'local'}, test_user.id),
    ]


def test_canonical_embedding_route_defaults_missing_json_to_local(
    auth_client, test_user, sample_document, monkeypatch
):
    from app.routes.processing import embeddings

    calls = []

    class Workflow:
        def __init__(self, workflow_logger):
            pass

        @staticmethod
        def get_document(identifier):
            return sample_document

        @staticmethod
        def generate(document, data, user):
            calls.append((document.id, data, user.id))
            return {'success': True, 'method': data.get('method', 'local')}

    monkeypatch.setattr(embeddings, 'DocumentEmbeddingWorkflow', Workflow)
    response = auth_client.post(
        f'/process/document/{sample_document.uuid}/embeddings'
    )
    assert response.status_code == 200
    assert response.get_json()['method'] == 'local'
    assert calls == [(sample_document.id, {}, test_user.id)]


def test_embedding_routes_hide_provider_errors(
    auth_client, sample_document, monkeypatch
):
    from app.routes.processing import embeddings
    from app.routes.text_input import processing

    class Failure:
        def __init__(self, workflow_logger):
            pass

        @staticmethod
        def get_document(identifier):
            return sample_document

        @staticmethod
        def generate(*args):
            raise RuntimeError('secret provider details')

    monkeypatch.setattr(embeddings, 'DocumentEmbeddingWorkflow', Failure)
    monkeypatch.setattr(processing, 'DocumentEmbeddingWorkflow', Failure)
    canonical = auth_client.post(
        f'/process/document/{sample_document.uuid}/embeddings',
        json={'method': 'local'},
    )
    legacy = auth_client.post(
        f'/input/documents/{sample_document.id}/apply_embeddings'
    )
    assert canonical.status_code == 500
    assert canonical.get_json()['error'] == 'Embedding generation failed'
    assert legacy.status_code == 500
    assert legacy.get_json()['error'] == 'Failed to generate embeddings'
    assert 'secret' not in str(canonical.get_json())
    assert 'secret' not in str(legacy.get_json())


def test_embedding_routes_require_authentication(app, sample_document):
    client = app.test_client()
    assert client.post(
        f'/process/document/{sample_document.uuid}/embeddings',
        json={'method': 'local'},
    ).status_code == 401
    assert client.post(
        f'/input/documents/{sample_document.id}/apply_embeddings'
    ).status_code == 302
