"""Regression coverage for experiment-scoped definition result read models."""

import json
from datetime import date

import pytest


def _experiment(db_session, user, suffix):
    from app.models.experiment import Experiment

    experiment = Experiment(
        name=f'Definition Results {suffix}',
        experiment_type='temporal_evolution',
        user_id=user.id,
        status='draft',
    )
    db_session.add(experiment)
    db_session.commit()
    return experiment


def _association(db_session, experiment, document):
    from app.models.experiment_document import ExperimentDocument

    association = ExperimentDocument(
        experiment_id=experiment.id,
        document_id=document.id,
    )
    db_session.add(association)
    db_session.commit()
    return association


def _artifact(
    db_session,
    association,
    content,
    metadata=None,
    index=0,
    status='completed',
):
    from app.models.experiment_processing import (
        ExperimentDocumentProcessing,
        ProcessingArtifact,
    )

    operation = ExperimentDocumentProcessing(
        experiment_document_id=association.id,
        processing_type='definitions',
        processing_method=(metadata or {}).get('method', 'pattern_matching'),
        status=status,
    )
    db_session.add(operation)
    db_session.flush()
    artifact = ProcessingArtifact(
        processing_id=operation.id,
        document_id=association.document_id,
        artifact_type='term_definition',
        artifact_index=index,
    )
    artifact.set_content(content)
    artifact.set_metadata(metadata or {})
    db_session.add(artifact)
    db_session.commit()
    return artifact


def _legacy_job(db_session, user, document, definitions, status='completed'):
    from app.models.processing_job import ProcessingJob

    job = ProcessingJob(
        document_id=document.id,
        user_id=user.id,
        job_type='definition_extraction',
        status=status,
    )
    job.set_result_data({'definitions': definitions})
    db_session.add(job)
    db_session.commit()
    return job


def test_definition_results_route_remains_canonical(app):
    assert (
        app.view_functions['experiments.experiment_definitions_results'].__module__
        == 'app.routes.experiments.results.definitions'
    )


def test_canonical_definition_artifacts_are_experiment_isolated(
    db_session, test_user, sample_document
):
    from app.services.experiment_definition_results_service import (
        ExperimentDefinitionResultsService,
    )

    first = _experiment(db_session, test_user, 'first')
    second = _experiment(db_session, test_user, 'second')
    first_link = _association(db_session, first, sample_document)
    second_link = _association(db_session, second, sample_document)
    _artifact(
        db_session,
        first_link,
        {
            'term': 'first-only',
            'definition': 'Definition owned by the first experiment.',
            'confidence': 0.91,
        },
        {'method': 'pattern_matching'},
    )
    _artifact(
        db_session,
        second_link,
        {
            'term': 'second-only',
            'definition': 'Definition owned by the second experiment.',
            'confidence': 0.88,
        },
        {'method': 'zero_shot_classifier'},
    )

    first_context = ExperimentDefinitionResultsService.get_context(first.id)
    second_context = ExperimentDefinitionResultsService.get_context(second.id)
    assert [item['term'] for item in first_context['definitions']] == [
        'first-only'
    ]
    assert first_context['definitions'][0]['source'] == 'pattern'
    assert [item['term'] for item in second_context['definitions']] == [
        'second-only'
    ]
    assert second_context['definitions'][0]['source'] == 'zeroshot'


def test_artifact_normalization_grouping_sorting_and_counts(
    db_session, test_user, sample_documents
):
    from app.services.experiment_definition_results_service import (
        ExperimentDefinitionResultsService,
    )

    experiment = _experiment(db_session, test_user, 'normalization')
    newer, older = sample_documents[:2]
    newer.publication_date = date(2020, 1, 1)
    older.publication_date = date(1990, 1, 1)
    newer_link = _association(db_session, experiment, newer)
    older_link = _association(db_session, experiment, older)
    _artifact(
        db_session,
        newer_link,
        {
            'term': 'Zeta',
            'definition': 'Structured definition.',
            'pattern': 'means',
            'confidence': 0.8,
            'sentence': 'Zeta means structured.',
        },
        {
            'method': 'pattern_matching',
            'start_char': 2,
            'end_char': 20,
        },
    )
    string_artifact = _artifact(
        db_session,
        older_link,
        {'placeholder': True},
    )
    string_artifact.content_json = json.dumps('A plain string definition.')
    db_session.commit()

    context = ExperimentDefinitionResultsService.get_context(experiment.id)
    assert context['total_definitions'] == 2
    assert context['auto_count'] == 2
    assert context['manual_count'] == 0
    assert [item['document_year'] for item in context['definitions']] == [
        1990,
        2020,
    ]
    plain = context['definitions'][0]
    assert plain['definition'] == 'A plain string definition.'
    assert plain['term'] == ''
    structured = context['definitions'][1]
    assert structured['start_char'] == 2
    assert structured['end_char'] == 20
    assert set(context['definitions_by_document']) == {newer.id, older.id}


def test_completed_legacy_jobs_are_fallback_for_documents_without_artifacts(
    db_session, test_user, sample_documents
):
    from app.services.experiment_definition_results_service import (
        ExperimentDefinitionResultsService,
    )

    experiment = _experiment(db_session, test_user, 'legacy')
    canonical, legacy = sample_documents[:2]
    canonical_link = _association(db_session, experiment, canonical)
    _association(db_session, experiment, legacy)
    _artifact(
        db_session,
        canonical_link,
        {'term': 'canonical', 'definition': 'Canonical result.'},
    )
    _legacy_job(
        db_session,
        test_user,
        canonical,
        [{'term': 'duplicate', 'definition': 'Must not be displayed.'}],
    )
    _legacy_job(
        db_session,
        test_user,
        legacy,
        [{
            'term': 'legacy',
            'definition': 'Legacy result.',
            'pattern': 'refers_to',
            'confidence': 0.7,
            'method': 'manual-review',
        }, 'Plain legacy result'],
    )
    _legacy_job(
        db_session,
        test_user,
        legacy,
        [{'term': 'failed', 'definition': 'Failed job result.'}],
        status='failed',
    )

    context = ExperimentDefinitionResultsService.get_context(experiment.id)
    terms = [item['term'] for item in context['definitions']]
    assert set(terms) == {'canonical', '', 'legacy'}
    assert 'duplicate' not in terms
    assert context['auto_count'] == 1
    assert context['manual_count'] == 2
    assert all(
        item['source'] == 'manual'
        for item in context['definitions']
        if item['document_id'] == legacy.id
    )


def test_noncompleted_canonical_operation_is_excluded_and_allows_legacy_fallback(
    db_session, test_user, sample_document
):
    from app.services.experiment_definition_results_service import (
        ExperimentDefinitionResultsService,
    )

    experiment = _experiment(db_session, test_user, 'pending')
    association = _association(db_session, experiment, sample_document)
    _artifact(
        db_session,
        association,
        {'term': 'pending', 'definition': 'Not completed.'},
        status='failed',
    )
    _legacy_job(
        db_session,
        test_user,
        sample_document,
        [{'term': 'fallback', 'definition': 'Completed legacy fallback.'}],
    )

    context = ExperimentDefinitionResultsService.get_context(experiment.id)
    assert [item['term'] for item in context['definitions']] == ['fallback']
    assert context['auto_count'] == 0
    assert context['manual_count'] == 1


def test_latest_document_version_is_used_for_results(
    db_session, test_user, sample_document
):
    from app.models.document import Document
    from app.services.experiment_definition_results_service import (
        ExperimentDefinitionResultsService,
    )

    experiment = _experiment(db_session, test_user, 'versions')
    root_link = _association(db_session, experiment, sample_document)
    version = Document(
        title='Latest version',
        content='Latest content',
        content_type='text',
        document_type='document',
        status='completed',
        user_id=test_user.id,
        source_document_id=sample_document.id,
        version_number=2,
        version_type='processed',
    )
    db_session.add(version)
    db_session.commit()
    latest_link = _association(db_session, experiment, version)
    _artifact(
        db_session,
        root_link,
        {'term': 'old', 'definition': 'Old version result.'},
    )
    _artifact(
        db_session,
        latest_link,
        {'term': 'latest', 'definition': 'Latest version result.'},
    )

    context = ExperimentDefinitionResultsService.get_context(experiment.id)
    assert context['documents'] == [version]
    assert [item['term'] for item in context['definitions']] == ['latest']


def test_empty_and_missing_experiment_contexts(db_session, test_user):
    from app.services.base_service import NotFoundError
    from app.services.experiment_definition_results_service import (
        ExperimentDefinitionResultsService,
    )

    experiment = _experiment(db_session, test_user, 'empty')
    context = ExperimentDefinitionResultsService.get_context(experiment.id)
    assert context['documents'] == []
    assert context['definitions'] == []
    assert context['total_definitions'] == 0
    with pytest.raises(NotFoundError, match='Experiment 999999 not found'):
        ExperimentDefinitionResultsService.get_context(999999)


def test_definition_results_route_contracts(
    client, db_session, test_user, sample_document
):
    experiment = _experiment(db_session, test_user, 'route')
    association = _association(db_session, experiment, sample_document)
    _artifact(
        db_session,
        association,
        {'term': 'route-term', 'definition': 'Rendered route definition.'},
    )
    response = client.get(
        f'/experiments/{experiment.id}/results/definitions'
    )
    missing = client.get('/experiments/999999/results/definitions')
    assert response.status_code == 200
    assert b'route-term' in response.data
    assert b'Rendered route definition.' in response.data
    assert missing.status_code == 404
