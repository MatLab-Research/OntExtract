"""Regression coverage for processing status read models and APIs."""

from datetime import datetime


def _create_job(db_session, user, document, job_type, parameters, status='completed'):
    from app.models.processing_job import ProcessingJob

    job = ProcessingJob(
        job_type=job_type,
        status=status,
        user_id=user.id,
        document_id=document.id,
        created_at=datetime.utcnow(),
    )
    job.set_parameters(parameters)
    db_session.add(job)
    db_session.commit()
    return job


def test_processing_status_routes_use_page_and_api_modules(app):
    expected = {
        'processing.processing_home': 'app.routes.processing.status.pages',
        'processing.job_list': 'app.routes.processing.status.pages',
        'processing.get_langextract_details': 'app.routes.processing.status.api',
        'processing.get_job_status': 'app.routes.processing.status.api',
        'processing.get_document_processing_jobs': 'app.routes.processing.status.api',
    }
    assert {
        endpoint: app.view_functions[endpoint].__module__
        for endpoint in expected
    } == expected


def test_dashboard_context_counts_live_processing(
    experiment_with_processing,
):
    from app.services.processing_status_service import ProcessingStatusService

    context = ProcessingStatusService.get_dashboard_context()

    assert context['stats']['documents']['total'] > 0
    assert context['stats']['processing_operations']['total'] > 0
    assert context['stats']['processing_operations']['completed'] > 0
    assert context['recent_documents']
    assert context['recent_processing']


def test_job_status_includes_chunk_progress(
    auth_client, db_session, test_user, sample_document
):
    job = _create_job(
        db_session,
        test_user,
        sample_document,
        'enhanced_processing',
        {
            'current_chunk': 2,
            'total_chunks': 4,
            'progress_message': 'Halfway',
        },
        status='running',
    )

    response = auth_client.get(f'/process/job/{job.id}/status')

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['progress'] == {
        'current': 2,
        'total': 4,
        'message': 'Halfway',
        'percentage': 50,
    }


def test_document_jobs_group_direct_and_indirect_history(
    auth_client, db_session, test_user, sample_document
):
    from app.models.document import Document

    first = _create_job(
        db_session,
        test_user,
        sample_document,
        'generate_embeddings',
        {'method': 'period_aware'},
    )
    version = Document(
        title='Embedding version',
        content='Processed content',
        content_type='text/plain',
        document_type='document',
        status='completed',
        user_id=test_user.id,
        source_document_id=sample_document.id,
        version_number=2,
        version_type='processed',
    )
    db_session.add(version)
    db_session.commit()
    second = _create_job(
        db_session,
        test_user,
        version,
        'generate_embeddings',
        {
            'method': 'period_aware',
            'original_document_id': sample_document.id,
        },
    )

    response = auth_client.get(
        f'/process/document/{sample_document.uuid}/processing-jobs'
    )

    assert response.status_code == 200
    operations = response.get_json()['processing_operations']
    assert len(operations) == 1
    assert operations[0]['processing_method'] == 'period_aware'
    assert operations[0]['run_count'] == 2
    assert operations[0]['has_history'] is True
    assert set(operations[0]['all_job_ids']) == {first.id, second.id}


def test_langextract_details_rejects_other_job_types(
    auth_client, db_session, test_user, sample_document
):
    job = _create_job(
        db_session,
        test_user,
        sample_document,
        'generate_embeddings',
        {'method': 'local'},
    )

    response = auth_client.get(
        f'/process/api/processing/job/{job.id}/langextract-details'
    )

    assert response.status_code == 400
    assert 'only for LangExtract' in response.get_json()['error']


def test_processing_status_apis_return_not_found(auth_client):
    missing_job = auth_client.get('/process/job/999999/status')
    missing_document = auth_client.get(
        '/process/document/not-a-real-uuid/processing-jobs'
    )

    assert missing_job.status_code == 404
    assert missing_document.status_code == 404
