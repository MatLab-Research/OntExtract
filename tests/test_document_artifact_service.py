"""Regression coverage for unified document artifact APIs."""

from datetime import datetime


def _create_embedding_artifact(
    db_session,
    experiment_with_processing,
    document,
    vector=None,
):
    from app.models.experiment_document import ExperimentDocument
    from app.models.experiment_processing import (
        ExperimentDocumentProcessing,
        ProcessingArtifact,
    )

    experiment_document = ExperimentDocument.query.filter_by(
        experiment_id=experiment_with_processing.id,
        document_id=document.id,
    ).first()
    processing = ExperimentDocumentProcessing.query.filter_by(
        experiment_document_id=experiment_document.id,
    ).first()
    artifact = ProcessingArtifact(
        processing_id=processing.id,
        document_id=document.id,
        artifact_type='embedding_vector',
        artifact_index=-1,
    )
    artifact.set_content({
        'text': 'Embedding context',
        'vector': vector or [0.1, 0.2, 0.3],
        'model': 'test-model',
        'embedding_level': 'document',
    })
    artifact.set_metadata({
        'method': 'period_aware',
        'dimensions': 3,
        'embedding_level': 'document',
    })
    db_session.add(artifact)
    db_session.commit()
    return artifact


def test_document_artifact_routes_keep_canonical_modules(app):
    expected = {
        'document_api.get_document_embeddings_new': (
            'app.routes.embeddings.documents'
        ),
        'document_api.get_embedding_preview': 'app.routes.embeddings.documents',
        'document_api.get_document_segments': 'app.routes.embeddings.documents',
    }
    assert {
        endpoint: app.view_functions[endpoint].__module__
        for endpoint in expected
    } == expected


def test_unified_embedding_list_uses_processing_artifacts(
    auth_client,
    db_session,
    experiment_with_processing,
):
    from app.models.experiment_document import ExperimentDocument

    document = ExperimentDocument.query.filter_by(
        experiment_id=experiment_with_processing.id
    ).first().document
    artifact = _create_embedding_artifact(
        db_session,
        experiment_with_processing,
        document,
    )

    response = auth_client.get(f'/api/document/{document.id}/embeddings')

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['count'] >= 1
    embedding = next(
        item for item in payload['embeddings'] if item['id'] == str(artifact.id)
    )
    assert embedding['model_name'] == 'test-model'
    assert embedding['dimensions'] == 3
    assert embedding['metadata']['source'] == 'processing_artifact'


def test_unified_embedding_preview_returns_real_vector(
    auth_client,
    db_session,
    experiment_with_processing,
):
    from app.models.experiment_document import ExperimentDocument

    document = ExperimentDocument.query.filter_by(
        experiment_id=experiment_with_processing.id
    ).first().document
    artifact = _create_embedding_artifact(
        db_session,
        experiment_with_processing,
        document,
        vector=[0.4, 0.5, 0.6],
    )

    response = auth_client.get(
        f'/api/document/embedding/{artifact.id}/preview'
    )

    assert response.status_code == 200
    embedding = response.get_json()['embedding']
    assert embedding['embedding'] == [0.4, 0.5, 0.6]
    assert embedding['context_window'] == 'Embedding context'


def test_legacy_embedding_job_remains_a_fallback(
    auth_client, db_session, sample_document, test_user
):
    from app.models.processing_job import ProcessingJob

    job = ProcessingJob(
        job_type='generate_embeddings',
        status='completed',
        user_id=test_user.id,
        document_id=sample_document.id,
        completed_at=datetime.utcnow(),
    )
    job.set_result_data({
        'embedding_method': 'local',
        'model_used': 'legacy-model',
        'embedding_dimensions': 384,
        'chunk_count': 2,
    })
    db_session.add(job)
    db_session.commit()

    list_response = auth_client.get(
        f'/api/document/{sample_document.id}/embeddings'
    )
    preview_response = auth_client.get(
        f'/api/document/embedding/job_{job.id}/preview'
    )

    assert list_response.status_code == 200
    assert list_response.get_json()['embeddings'][0]['id'] == f'job_{job.id}'
    assert preview_response.status_code == 200
    preview = preview_response.get_json()['embedding']
    assert preview['model_name'] == 'legacy-model'
    assert preview['embedding'] == []


def test_segments_group_by_explicit_segmentation_method(
    auth_client, db_session, sample_document
):
    from app.models.text_segment import TextSegment

    segments = [
        TextSegment(
            document_id=sample_document.id,
            content='Sentence segment.',
            segment_number=2,
            segmentation_method='sentence',
        ),
        TextSegment(
            document_id=sample_document.id,
            content='First sentence.',
            segment_number=1,
            segmentation_method='sentence',
        ),
        TextSegment(
            document_id=sample_document.id,
            content='Paragraph segment.',
            segment_number=1,
            segmentation_method='paragraph',
        ),
    ]
    db_session.add_all(segments)
    db_session.commit()

    response = auth_client.get(f'/api/document/{sample_document.id}/segments')

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['total_segments'] == 3
    methods = {item['method']: item for item in payload['segmentation_methods']}
    assert methods['sentence']['count'] == 2
    assert [
        segment['segment_number'] for segment in methods['sentence']['segments']
    ] == [1, 2]
    assert methods['paragraph']['count'] == 1


def test_document_artifact_apis_return_not_found(auth_client):
    missing_document = auth_client.get('/api/document/999999/embeddings')
    missing_embedding = auth_client.get(
        '/api/document/embedding/not-an-artifact/preview'
    )

    assert missing_document.status_code == 404
    assert missing_embedding.status_code == 404
