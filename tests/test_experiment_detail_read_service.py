"""Regression coverage for experiment detail and manual result read models."""

import json


def test_experiment_detail_routes_remain_in_canonical_module(app):
    expected = 'app.routes.experiments.crud.detail'
    assert app.view_functions['experiments.view'].__module__ == expected
    assert app.view_functions['experiments.results'].__module__ == expected


def test_detail_context_uses_unified_artifacts_and_operations(
    experiment_with_processing,
):
    from app.services.experiment_detail_read_service import (
        ExperimentDetailReadService,
    )

    context = ExperimentDetailReadService.get_detail_context(
        experiment_with_processing.id
    )

    assert context['experiment'] is experiment_with_processing
    assert context['processing_summary']['embeddings'] == 5
    assert context['processing_summary']['definitions'] == 5
    assert context['processing_summary']['entities'] == 5
    assert context['processing_summary']['temporal'] == 5
    assert context['processing_summary']['segmentation'] == 5
    assert context['total_processing_ops'] == 25
    assert len(context['documents_enhanced']) == 5
    assert all(
        document['processing_count'] == 1
        for document in context['documents_enhanced']
    )
    assert all(
        list(document['processing_by_type']) == ['embeddings']
        for document in context['documents_enhanced']
    )


def test_artifacts_are_scoped_by_owning_experiment(
    db_session, test_user, sample_document
):
    from app.models.experiment import Experiment
    from app.models.experiment_document import ExperimentDocument
    from app.models.experiment_processing import (
        ExperimentDocumentProcessing,
        ProcessingArtifact,
    )
    from app.services.experiment_detail_read_service import (
        ExperimentDetailReadService,
    )

    first = Experiment(
        name='Artifact owner',
        experiment_type='entity_extraction',
        user_id=test_user.id,
        status='completed',
    )
    second = Experiment(
        name='Shared document only',
        experiment_type='entity_extraction',
        user_id=test_user.id,
        status='completed',
    )
    db_session.add_all([first, second])
    db_session.flush()
    first_link = ExperimentDocument(
        experiment_id=first.id,
        document_id=sample_document.id,
    )
    second_link = ExperimentDocument(
        experiment_id=second.id,
        document_id=sample_document.id,
    )
    db_session.add_all([first_link, second_link])
    db_session.flush()
    processing = ExperimentDocumentProcessing(
        experiment_document_id=first_link.id,
        processing_type='entities',
        processing_method='spacy',
        status='completed',
    )
    db_session.add(processing)
    db_session.flush()
    artifact = ProcessingArtifact(
        processing_id=processing.id,
        document_id=sample_document.id,
        artifact_type='extracted_entity',
        artifact_index=0,
    )
    artifact.set_content({'text': 'OntExtract'})
    db_session.add(artifact)
    db_session.commit()

    first_context = ExperimentDetailReadService.get_detail_context(first.id)
    second_context = ExperimentDetailReadService.get_detail_context(second.id)

    assert first_context['processing_summary'] == {'entities': 1}
    assert second_context['processing_summary'] == {}
    assert first_context['documents_enhanced'][0][
        'other_experiments_count'
    ] == 1
    assert second_context['documents_enhanced'][0][
        'other_experiments_count'
    ] == 1


def test_detail_selects_latest_version_and_deduplicates_operations(
    db_session, test_user, sample_document
):
    from app.models.document import Document
    from app.models.experiment import Experiment
    from app.models.experiment_document import ExperimentDocument
    from app.models.experiment_processing import ExperimentDocumentProcessing
    from app.services.experiment_detail_read_service import (
        ExperimentDetailReadService,
    )

    experiment = Experiment(
        name='Version selection',
        experiment_type='entity_extraction',
        user_id=test_user.id,
        status='completed',
    )
    latest = Document(
        title='Latest version',
        content='Latest content',
        content_type='text/plain',
        document_type='document',
        status='completed',
        user_id=test_user.id,
        source_document_id=sample_document.id,
        version_number=3,
        version_type='processed',
    )
    db_session.add_all([experiment, latest])
    db_session.flush()
    root_link = ExperimentDocument(
        experiment_id=experiment.id,
        document_id=sample_document.id,
    )
    latest_link = ExperimentDocument(
        experiment_id=experiment.id,
        document_id=latest.id,
    )
    db_session.add_all([root_link, latest_link])
    db_session.flush()
    db_session.add_all([
        ExperimentDocumentProcessing(
            experiment_document_id=latest_link.id,
            processing_type='segmentation',
            processing_method='sentence',
            status='completed',
        ),
        ExperimentDocumentProcessing(
            experiment_document_id=latest_link.id,
            processing_type='segmentation',
            processing_method='sentence',
            status='completed',
        ),
        ExperimentDocumentProcessing(
            experiment_document_id=latest_link.id,
            processing_type='segmentation',
            processing_method='paragraph',
            status='completed',
        ),
        ExperimentDocumentProcessing(
            experiment_document_id=latest_link.id,
            processing_type='entities',
            processing_method='spacy',
            status='failed',
        ),
    ])
    db_session.commit()

    context = ExperimentDetailReadService.get_detail_context(experiment.id)
    document_context = context['documents_enhanced'][0]

    assert len(context['documents_enhanced']) == 1
    assert document_context['document'].id == latest.id
    assert document_context['processing_count'] == 2
    assert {
        method['method_key']
        for method in document_context['processing_by_type']['segmentation']
    } == {'sentence', 'paragraph'}


def test_manual_results_context_uses_unified_schema(
    experiment_with_processing,
):
    from app.services.experiment_detail_read_service import (
        ExperimentDetailReadService,
    )

    context = ExperimentDetailReadService.get_manual_results_context(
        experiment_with_processing.id
    )

    assert context['total_operations'] == 25
    assert context['config_data']['terms'] == ['algorithm']
    assert len(context['documents_with_processing']) == 5
    assert all(
        item['processing'] == {'embeddings': 1}
        for item in context['documents_with_processing']
    )


def test_manual_results_route_renders_for_completed_experiment(
    client, experiment_with_processing
):
    response = client.get(
        f'/experiments/{experiment_with_processing.id}/results'
    )

    assert response.status_code == 200
    assert b'Manual Processing Complete' in response.data


def test_results_route_redirects_incomplete_experiment(
    client, temporal_experiment
):
    response = client.get(
        f'/experiments/{temporal_experiment.id}/results',
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers['Location'].endswith(
        f'/experiments/{temporal_experiment.id}'
    )


def test_results_route_redirects_completed_orchestration(
    client, db_session, experiment_with_documents, test_user
):
    from app.models.experiment_orchestration_run import ExperimentOrchestrationRun

    run = ExperimentOrchestrationRun(
        experiment_id=experiment_with_documents.id,
        user_id=test_user.id,
        status='completed',
        current_stage='completed',
    )
    db_session.add(run)
    db_session.commit()

    response = client.get(
        f'/experiments/{experiment_with_documents.id}/results',
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert str(run.id) in response.headers['Location']


def test_manual_results_configuration_tolerates_non_object_json(
    db_session, experiment_with_documents
):
    from app.services.experiment_detail_read_service import (
        ExperimentDetailReadService,
    )

    experiment_with_documents.configuration = json.dumps(['not', 'an', 'object'])
    db_session.commit()

    context = ExperimentDetailReadService.get_manual_results_context(
        experiment_with_documents.id
    )

    assert context['config_data'] == {}
