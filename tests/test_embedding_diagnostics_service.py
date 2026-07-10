"""Regression coverage for embedding diagnostics and real vector samples."""

from datetime import datetime


def _artifact(db_session, experiment_with_processing, document, vector=None):
    from app.models.experiment_document import ExperimentDocument
    from app.models.experiment_processing import (
        ExperimentDocumentProcessing,
        ProcessingArtifact,
    )

    association = ExperimentDocument.query.filter_by(
        experiment_id=experiment_with_processing.id,
        document_id=document.id,
    ).first()
    operation = ExperimentDocumentProcessing(
        experiment_document_id=association.id,
        processing_type='embeddings',
        processing_method='period_aware',
        status='completed',
    )
    db_session.add(operation)
    db_session.flush()
    artifact = ProcessingArtifact(
        processing_id=operation.id,
        document_id=document.id,
        artifact_type='embedding_vector',
        artifact_index=-1,
    )
    artifact.set_content({
        'text': 'Stored embedding context.',
        'vector': vector or [0.1, 0.2, 0.3, 0.4],
        'model': 'stored-model',
    })
    artifact.set_metadata({'method': 'period_aware', 'dimensions': 4})
    db_session.add(artifact)
    db_session.commit()
    return artifact


def _legacy_job(db_session, user, document, status='completed'):
    from app.models.processing_job import ProcessingJob

    job = ProcessingJob(
        job_type='generate_embeddings',
        status=status,
        user_id=user.id,
        document_id=document.id,
        completed_at=datetime.utcnow() if status == 'completed' else None,
    )
    job.set_parameters({'original_document_id': document.get_root_document().id})
    job.set_result_data({
        'embedding_method': 'local',
        'model_used': 'legacy-model',
        'embedding_dimensions': 384,
        'chunk_count': 2,
        'processing_time': 1.25,
    })
    if status == 'failed':
        job.set_error_details({'provider': 'unavailable'})
    db_session.add(job)
    db_session.commit()
    return job


def test_embedding_diagnostic_routes_remain_canonical(app):
    expected = 'app.routes.embeddings.embeddings'
    for endpoint in (
        'embeddings.get_document_embeddings',
        'embeddings.get_embedding_sample',
        'embeddings.verify_embeddings',
        'embeddings.get_job_details',
    ):
        assert app.view_functions[endpoint].__module__ == expected


def test_document_info_prefers_unified_artifacts(
    auth_client, db_session, experiment_with_processing
):
    from app.models.experiment_document import ExperimentDocument

    document = ExperimentDocument.query.filter_by(
        experiment_id=experiment_with_processing.id
    ).first().document
    _artifact(db_session, experiment_with_processing, document)

    response = auth_client.get(f'/api/embeddings/document/{document.id}')

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['has_embeddings'] is True
    assert payload['source'] == 'processing_artifact'
    assert payload['method'] == 'period_aware'
    assert payload['dimensions'] == 4


def test_embedding_sample_returns_real_stored_vector_values(
    auth_client, db_session, experiment_with_processing
):
    from app.models.experiment_document import ExperimentDocument

    document = ExperimentDocument.query.filter_by(
        experiment_id=experiment_with_processing.id
    ).first().document
    _artifact(
        db_session,
        experiment_with_processing,
        document,
        vector=[0.11, 0.22, 0.33, 0.44],
    )

    response = auth_client.get(
        f'/api/embeddings/document/{document.id}/sample'
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['method'] == 'period_aware'
    assert payload['total_dimensions'] == 4
    assert payload['sample_chunks'][0]['vector_sample'] == [
        0.11,
        0.22,
        0.33,
        0.44,
    ]
    assert payload['processed_versions'][0]['source'] == 'processing_artifact'
    assert 'stored embedding vector samples' in payload['note'].lower()


def test_legacy_sample_does_not_fabricate_vectors(
    auth_client, db_session, sample_document, test_user
):
    _legacy_job(db_session, test_user, sample_document)

    response = auth_client.get(
        f'/api/embeddings/document/{sample_document.id}/sample'
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['method'] == 'local'
    assert payload['total_dimensions'] == 384
    assert payload['sample_chunks'][0]['vector_sample'] == []
    assert 'without fabricated values' in payload['note']


def test_verify_includes_family_jobs_and_artifacts(
    auth_client,
    db_session,
    sample_document,
    test_user,
    experiment_with_processing,
):
    from app.models.document import Document
    from app.models.experiment_document import ExperimentDocument

    version = Document(
        title='Embedding version',
        content='Version content',
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
    _legacy_job(db_session, test_user, version, status='completed')
    _legacy_job(db_session, test_user, version, status='failed')

    # Create an artifact on a fixture document and query through that family.
    artifact_document = ExperimentDocument.query.filter_by(
        experiment_id=experiment_with_processing.id
    ).first().document
    _artifact(db_session, experiment_with_processing, artifact_document)
    artifact_response = auth_client.get(
        f'/api/embeddings/document/{artifact_document.id}/verify'
    )
    legacy_response = auth_client.get(
        f'/api/embeddings/document/{sample_document.id}/verify'
    )

    artifact_payload = artifact_response.get_json()
    assert artifact_payload['has_embeddings'] is True
    assert artifact_payload['artifact_count'] >= 1
    assert artifact_payload['latest_embedding']['source'] == 'processing_artifact'
    legacy_payload = legacy_response.get_json()
    assert legacy_payload['total_attempts'] == 2
    assert legacy_payload['successful_attempts'] == 1
    assert legacy_payload['failed_attempts'] == 1


def test_job_details_enforces_owner(
    auth_client, db_session, sample_document, test_user
):
    from app.models.user import User

    owner_job = _legacy_job(db_session, test_user, sample_document)
    other = User(
        username='embedding-owner-other',
        email='embedding-owner-other@example.com',
        password='password',
    )
    db_session.add(other)
    db_session.commit()
    other_job = _legacy_job(db_session, other, sample_document)

    allowed = auth_client.get(f'/api/embeddings/jobs/{owner_job.id}')
    denied = auth_client.get(f'/api/embeddings/jobs/{other_job.id}')

    assert allowed.status_code == 200
    assert allowed.get_json()['job_details']['job_info']['id'] == owner_job.id
    assert denied.status_code == 403
    assert denied.get_json()['error'] == 'Access denied'


def test_embedding_diagnostics_return_not_found(auth_client):
    document = auth_client.get('/api/embeddings/document/999999')
    job = auth_client.get('/api/embeddings/jobs/999999')

    assert document.status_code == 404
    assert job.status_code == 404
