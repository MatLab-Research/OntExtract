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
