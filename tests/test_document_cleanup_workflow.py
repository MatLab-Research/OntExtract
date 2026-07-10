"""Regression coverage for cleanup job orchestration and reviewed versions."""


class DeferredThread:
    """Capture a background target without executing it."""

    instances = []

    def __init__(self, target, args, daemon):
        self.target = target
        self.args = args
        self.daemon = daemon
        self.started = False
        self.__class__.instances.append(self)

    def start(self):
        self.started = True


def test_cleanup_routes_remain_in_canonical_module(app):
    expected = 'app.routes.processing.text_cleanup'
    assert app.view_functions['processing.clean_text'].__module__ == expected
    assert app.view_functions['processing.save_cleaned_text'].__module__ == expected


def test_start_cleanup_creates_running_job_without_blocking(
    app, db_session, sample_document, test_user
):
    from app.models.processing_job import ProcessingJob
    from app.services.document_cleanup_workflow import DocumentCleanupWorkflow

    DeferredThread.instances.clear()
    workflow = DocumentCleanupWorkflow(thread_factory=DeferredThread)
    result = workflow.start_cleanup(sample_document, test_user.id, app)

    job = db_session.get(ProcessingJob, result['job_id'])
    assert result['status'] == 'running'
    assert job.status == 'running'
    assert job.get_parameters()['original_length'] == len(sample_document.content)
    assert len(DeferredThread.instances) == 1
    assert DeferredThread.instances[0].started is True
    assert DeferredThread.instances[0].daemon is True


def test_cleanup_route_rejects_document_without_content(
    auth_client, db_session, sample_document, monkeypatch
):
    from app.routes.processing import text_cleanup

    sample_document.content = ''
    db_session.commit()
    monkeypatch.setattr(
        text_cleanup.cleanup_workflow,
        'thread_factory',
        DeferredThread,
    )

    response = auth_client.post(
        f'/process/document/{sample_document.uuid}/clean-text'
    )

    assert response.status_code == 400
    assert response.get_json()['error'] == 'Document has no content to clean'


def test_save_reviewed_cleanup_creates_version_job_and_experiment_link(
    auth_client,
    db_session,
    experiment_with_documents,
    test_user,
):
    from app.models.document import Document
    from app.models.experiment_document import ExperimentDocument
    from app.models.processing_job import ProcessingJob

    original_link = ExperimentDocument.query.filter_by(
        experiment_id=experiment_with_documents.id
    ).first()
    document = original_link.document
    original_job = ProcessingJob(
        document_id=document.id,
        job_type='clean_text',
        status='completed',
        user_id=test_user.id,
    )
    original_job.set_parameters({
        'model': 'test-cleanup-model',
        'input_tokens': 10,
        'output_tokens': 12,
        'chunks_processed': 2,
    })
    db_session.add(original_job)
    db_session.commit()

    response = auth_client.post(
        f'/process/document/{document.uuid}/save-cleaned-text',
        json={
            'cleaned_content': 'Reviewed and cleaned content.',
            'changes_accepted': 4,
            'changes_rejected': 1,
            'original_length': len(document.content),
            'cleaned_length': 29,
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    cleaned = db_session.get(Document, payload['document_id'])
    cleanup_job = db_session.get(ProcessingJob, payload['job_id'])
    assert cleaned.version_type == 'cleaned'
    assert cleaned.content == 'Reviewed and cleaned content.'
    assert cleaned.get_root_document().id == document.id
    assert cleanup_job.document_id == cleaned.id
    assert cleanup_job.get_parameters()['model'] == 'test-cleanup-model'
    assert cleanup_job.get_parameters()['cleanup_method'] == 'llm_claude_reviewed'
    assert ExperimentDocument.query.filter_by(
        experiment_id=experiment_with_documents.id,
        document_id=cleaned.id,
    ).count() == 1


def test_save_reviewed_cleanup_validates_payload(auth_client, sample_document):
    empty_payload = auth_client.post(
        f'/process/document/{sample_document.uuid}/save-cleaned-text',
        json={},
    )
    missing_content = auth_client.post(
        f'/process/document/{sample_document.uuid}/save-cleaned-text',
        json={'changes_accepted': 1},
    )

    assert empty_payload.status_code == 400
    assert empty_payload.get_json()['error'] == 'No data provided'
    assert missing_content.status_code == 400
    assert missing_content.get_json()['error'] == 'No cleaned content provided'


def test_cleanup_routes_return_not_found(auth_client):
    response = auth_client.post('/process/document/not-a-uuid/clean-text')

    assert response.status_code == 404
