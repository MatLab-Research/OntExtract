"""Regression coverage for experiment-scoped temporal expression results."""

import json
from datetime import date

import pytest


def _experiment(db_session, user, suffix):
    from app.models.experiment import Experiment

    experiment = Experiment(
        name=f'Temporal Results {suffix}',
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
    *,
    method='spacy_ner_plus_regex',
    index=0,
    status='completed',
    artifact_type='temporal_marker',
):
    from app.models.experiment_processing import (
        ExperimentDocumentProcessing,
        ProcessingArtifact,
    )

    operation = ExperimentDocumentProcessing(
        experiment_document_id=association.id,
        processing_type='temporal',
        processing_method=method,
        status=status,
    )
    db_session.add(operation)
    db_session.flush()
    artifact = ProcessingArtifact(
        processing_id=operation.id,
        document_id=association.document_id,
        artifact_type=artifact_type,
        artifact_index=index,
    )
    artifact.set_content(content)
    artifact.set_metadata(metadata or {})
    db_session.add(artifact)
    db_session.commit()
    return artifact


def _derived_document(db_session, original, experiment, suffix, version_number):
    from app.models.document import Document

    document = Document(
        title=f'{original.title} {suffix}',
        content=original.content,
        content_type=original.content_type,
        document_type='document',
        status='completed',
        user_id=original.user_id,
        source_document_id=original.id,
        experiment_id=experiment.id,
        version_number=version_number,
        version_type='experimental',
    )
    db_session.add(document)
    db_session.commit()
    return document


def test_temporal_results_route_remains_canonical(app):
    assert app.view_functions[
        'experiments.experiment_temporal_results'
    ].__module__ == 'app.routes.experiments.results.temporal'


def test_temporal_artifacts_are_isolated_by_experiment(
    db_session, test_user, sample_document
):
    from app.services.experiment_temporal_results_service import (
        ExperimentTemporalResultsService,
    )

    first = _experiment(db_session, test_user, 'first')
    second = _experiment(db_session, test_user, 'second')
    first_link = _association(db_session, first, sample_document)
    second_link = _association(db_session, second, sample_document)
    _artifact(
        db_session,
        first_link,
        {'text': 'first-only', 'type': 'DATE'},
    )
    _artifact(
        db_session,
        second_link,
        {'text': 'second-only', 'type': 'YEAR'},
    )

    first_context = ExperimentTemporalResultsService.get_context(first.id)
    second_context = ExperimentTemporalResultsService.get_context(second.id)
    assert [item['text'] for item in first_context['temporal_expressions']] == [
        'first-only'
    ]
    assert [item['text'] for item in second_context['temporal_expressions']] == [
        'second-only'
    ]


def test_only_completed_temporal_operations_are_included(
    db_session, test_user, sample_document
):
    from app.services.experiment_temporal_results_service import (
        ExperimentTemporalResultsService,
    )

    experiment = _experiment(db_session, test_user, 'status')
    association = _association(db_session, experiment, sample_document)
    _artifact(
        db_session,
        association,
        {'text': 'completed', 'type': 'DATE'},
    )
    _artifact(
        db_session,
        association,
        {'text': 'failed', 'type': 'DATE'},
        status='failed',
    )
    _artifact(
        db_session,
        association,
        {'text': 'wrong artifact', 'type': 'DATE'},
        artifact_type='extracted_entity',
    )
    context = ExperimentTemporalResultsService.get_context(experiment.id)
    assert [item['text'] for item in context['temporal_expressions']] == [
        'completed'
    ]


def test_normalization_sorting_grouping_and_method_source(
    db_session, test_user, sample_documents
):
    from app.services.experiment_temporal_results_service import (
        ExperimentTemporalResultsService,
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
            'text': ' 2020 ',
            'type': 'year',
            'normalized': '2020-01-01',
            'start': '12',
            'end': '16',
            'confidence': 4,
            'context': ' modern context ',
        },
        {'method': 'langextract_orchestration'},
    )
    older_artifact = _artifact(
        db_session,
        older_link,
        {'placeholder': True},
        {'start_char': '2', 'end_char': '5', 'source': 'reviewed'},
        method='manual-review',
    )
    older_artifact.content_json = json.dumps('1990')
    db_session.commit()

    context = ExperimentTemporalResultsService.get_context(experiment.id)
    first, second = context['temporal_expressions']
    assert [first['text'], second['text']] == ['1990', '2020']
    assert first['type'] == 'UNKNOWN'
    assert first['start_position'] == 2
    assert first['end_position'] == 5
    assert first['source'] == 'reviewed'
    assert first['method'] == 'manual-review'
    assert second['type'] == 'YEAR'
    assert second['confidence'] == 1.0
    assert second['context'] == 'modern context'
    assert second['source'] == 'orchestration'
    assert list(context['expressions_by_type']) == ['UNKNOWN', 'YEAR']
    assert list(context['expressions_by_document']) == [older.id, newer.id]


def test_malformed_artifact_payloads_are_safe(
    db_session, test_user, sample_document
):
    from app.services.experiment_temporal_results_service import (
        ExperimentTemporalResultsService,
    )

    experiment = _experiment(db_session, test_user, 'malformed')
    association = _association(db_session, experiment, sample_document)
    artifact = _artifact(db_session, association, {'text': 'placeholder'})
    artifact.content_json = '{not json'
    artifact.metadata_json = '{not json'
    db_session.commit()
    expression = ExperimentTemporalResultsService.get_context(
        experiment.id
    )['temporal_expressions'][0]
    assert expression['text'] == ''
    assert expression['type'] == 'UNKNOWN'
    assert expression['confidence'] == 0.75
    assert expression['start_position'] is None


def test_latest_document_version_is_selected(
    db_session, test_user, sample_document
):
    from app.services.experiment_temporal_results_service import (
        ExperimentTemporalResultsService,
    )

    experiment = _experiment(db_session, test_user, 'versions')
    older = _derived_document(
        db_session,
        sample_document,
        experiment,
        'v2',
        2,
    )
    newer = _derived_document(
        db_session,
        sample_document,
        experiment,
        'v3',
        3,
    )
    _association(db_session, experiment, older)
    newer_link = _association(db_session, experiment, newer)
    _artifact(
        db_session,
        newer_link,
        {'text': 'latest', 'type': 'DATE'},
    )
    context = ExperimentTemporalResultsService.get_context(experiment.id)
    assert context['documents'] == [newer]
    assert context['temporal_expressions'][0]['document_id'] == newer.id


def test_empty_and_missing_experiments(db_session, test_user):
    from app.services.base_service import NotFoundError
    from app.services.experiment_temporal_results_service import (
        ExperimentTemporalResultsService,
    )

    experiment = _experiment(db_session, test_user, 'empty')
    context = ExperimentTemporalResultsService.get_context(experiment.id)
    assert context['documents'] == []
    assert context['temporal_expressions'] == []
    assert context['total_expressions'] == 0
    with pytest.raises(NotFoundError):
        ExperimentTemporalResultsService.get_context(999999)


def test_temporal_results_route_renders_and_maps_missing(
    client, db_session, test_user, sample_document
):
    experiment = _experiment(db_session, test_user, 'route')
    association = _association(db_session, experiment, sample_document)
    _artifact(
        db_session,
        association,
        {'text': 'the 1990s', 'type': 'DECADE'},
        {'method': 'langextract'},
        method='langextract',
    )
    response = client.get(
        f'/experiments/{experiment.id}/results/temporal'
    )
    missing = client.get('/experiments/999999/results/temporal')
    assert response.status_code == 200
    assert b'the 1990s' in response.data
    assert b'method: langextract' in response.data
    assert missing.status_code == 404
