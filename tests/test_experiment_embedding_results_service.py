"""Regression coverage for experiment-scoped embedding result summaries."""

from datetime import datetime


def _operation_with_artifacts(
    db_session,
    association,
    *,
    method,
    dimensions,
    artifact_count,
):
    from app.models.experiment_processing import (
        ExperimentDocumentProcessing,
        ProcessingArtifact,
    )

    operation = ExperimentDocumentProcessing(
        experiment_document_id=association.id,
        processing_type='embeddings',
        processing_method=method,
        status='completed',
        created_at=datetime.utcnow(),
    )
    db_session.add(operation)
    db_session.flush()
    artifacts = []
    for index in range(artifact_count):
        artifact = ProcessingArtifact(
            processing_id=operation.id,
            document_id=association.document_id,
            artifact_type='embedding_vector',
            artifact_index=index,
        )
        artifact.set_content({
            'vector': [0.1] * dimensions,
            'model': f'{method}-model',
        })
        artifact.set_metadata({
            'method': method,
            'dimensions': dimensions,
        })
        db_session.add(artifact)
        artifacts.append(artifact)
    db_session.commit()
    return operation, artifacts


def test_experiment_embedding_route_remains_canonical(app):
    assert app.view_functions[
        'experiments.experiment_embeddings_results'
    ].__module__ == 'app.routes.experiments.results.embeddings'


def test_embedding_results_use_latest_canonical_operation(
    db_session, experiment_with_documents
):
    from app.models.experiment_document import ExperimentDocument
    from app.services.experiment_embedding_results_service import (
        ExperimentEmbeddingResultsService,
    )

    association = ExperimentDocument.query.filter_by(
        experiment_id=experiment_with_documents.id
    ).first()
    _operation_with_artifacts(
        db_session,
        association,
        method='old-method',
        dimensions=3,
        artifact_count=1,
    )
    _operation_with_artifacts(
        db_session,
        association,
        method='latest-method',
        dimensions=5,
        artifact_count=2,
    )

    context = ExperimentEmbeddingResultsService.get_context(
        experiment_with_documents.id
    )
    info = next(
        item for item in context['embeddings_info']
        if item['document_id'] == association.document_id
    )
    assert info['method'] == 'latest-method'
    assert info['dimensions'] == 5
    assert info['chunk_count'] == 2
    assert context['total_embeddings'] == 2


def test_embedding_artifacts_are_isolated_by_experiment_owner(
    db_session, test_user, sample_document
):
    from app.models.experiment import Experiment
    from app.models.experiment_document import ExperimentDocument
    from app.services.experiment_embedding_results_service import (
        ExperimentEmbeddingResultsService,
    )

    owner = Experiment(
        name='Embedding owner',
        experiment_type='entity_extraction',
        user_id=test_user.id,
        status='completed',
    )
    viewer = Experiment(
        name='Shared document viewer',
        experiment_type='entity_extraction',
        user_id=test_user.id,
        status='completed',
    )
    db_session.add_all([owner, viewer])
    db_session.flush()
    owner_link = ExperimentDocument(
        experiment_id=owner.id,
        document_id=sample_document.id,
    )
    viewer_link = ExperimentDocument(
        experiment_id=viewer.id,
        document_id=sample_document.id,
    )
    db_session.add_all([owner_link, viewer_link])
    db_session.flush()
    _operation_with_artifacts(
        db_session,
        owner_link,
        method='owner-only',
        dimensions=4,
        artifact_count=1,
    )

    owner_context = ExperimentEmbeddingResultsService.get_context(owner.id)
    viewer_context = ExperimentEmbeddingResultsService.get_context(viewer.id)

    assert owner_context['embeddings_info'][0]['method'] == 'owner-only'
    assert viewer_context['embeddings_info'] == []


def test_orchestration_labels_persisted_embedding_as_pipeline(
    db_session, experiment_with_documents, test_user
):
    from app.models.experiment_document import ExperimentDocument
    from app.models.experiment_orchestration_run import ExperimentOrchestrationRun
    from app.services.experiment_embedding_results_service import (
        ExperimentEmbeddingResultsService,
    )

    association = ExperimentDocument.query.filter_by(
        experiment_id=experiment_with_documents.id
    ).first()
    _operation_with_artifacts(
        db_session,
        association,
        method='period_aware',
        dimensions=4,
        artifact_count=1,
    )
    run = ExperimentOrchestrationRun(
        experiment_id=experiment_with_documents.id,
        user_id=test_user.id,
        status='completed',
        processing_results={
            str(association.document_id): {
                'period_aware_embedding': {'status': 'executed'},
            },
        },
    )
    db_session.add(run)
    db_session.commit()

    context = ExperimentEmbeddingResultsService.get_context(
        experiment_with_documents.id
    )
    info = next(
        item for item in context['embeddings_info']
        if item['document_id'] == association.document_id
    )
    assert info['source'] == 'llm'


def test_legacy_completed_job_is_fallback_for_owned_version(
    db_session, experiment_with_documents, test_user
):
    from app.models.document import Document
    from app.models.experiment_document import ExperimentDocument
    from app.models.processing_job import ProcessingJob
    from app.services.experiment_embedding_results_service import (
        ExperimentEmbeddingResultsService,
    )

    root_link = ExperimentDocument.query.filter_by(
        experiment_id=experiment_with_documents.id
    ).first()
    root = root_link.document
    version = Document(
        title='Experiment embedding version',
        content='Version content',
        content_type='text/plain',
        document_type='document',
        status='completed',
        user_id=test_user.id,
        source_document_id=root.id,
        version_number=2,
        version_type='experimental',
        experiment_id=experiment_with_documents.id,
    )
    db_session.add(version)
    db_session.flush()
    version_link = ExperimentDocument(
        experiment_id=experiment_with_documents.id,
        document_id=version.id,
    )
    db_session.add(version_link)
    db_session.flush()
    job = ProcessingJob(
        document_id=version.id,
        user_id=test_user.id,
        job_type='generate_embeddings',
        status='completed',
        completed_at=datetime.utcnow(),
    )
    job.set_result_data({
        'embedding_method': 'local',
        'embedding_dimensions': 384,
        'chunk_count': 3,
        'model_used': 'legacy-model',
    })
    db_session.add(job)
    db_session.commit()

    context = ExperimentEmbeddingResultsService.get_context(
        experiment_with_documents.id
    )
    info = next(
        item for item in context['embeddings_info']
        if item['document_id'] == version.id
    )
    assert info['method'] == 'local'
    assert info['chunk_count'] == 3
    assert info['source'] == 'manual'


def test_bare_orchestration_json_does_not_invent_embedding_result(
    db_session, experiment_with_documents, test_user
):
    from app.models.experiment_document import ExperimentDocument
    from app.models.experiment_orchestration_run import ExperimentOrchestrationRun
    from app.services.experiment_embedding_results_service import (
        ExperimentEmbeddingResultsService,
    )

    association = ExperimentDocument.query.filter_by(
        experiment_id=experiment_with_documents.id
    ).first()
    run = ExperimentOrchestrationRun(
        experiment_id=experiment_with_documents.id,
        user_id=test_user.id,
        status='completed',
        processing_results={
            str(association.document_id): {
                'period_aware_embedding': {
                    'status': 'executed',
                    'metadata': {'dimensions': 999},
                },
            },
        },
    )
    db_session.add(run)
    db_session.commit()

    context = ExperimentEmbeddingResultsService.get_context(
        experiment_with_documents.id
    )
    assert all(
        item['document_id'] != association.document_id
        for item in context['embeddings_info']
    )


def test_embedding_results_route_renders_and_missing_returns_404(
    client, experiment_with_processing
):
    rendered = client.get(
        f'/experiments/{experiment_with_processing.id}/results/embeddings'
    )
    missing = client.get('/experiments/999999/results/embeddings')

    assert rendered.status_code == 200
    assert missing.status_code == 404
