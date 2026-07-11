"""Regression coverage for experiment-scoped segment result read models."""

import json
from datetime import date

import pytest


def _experiment(db_session, user, suffix):
    from app.models.experiment import Experiment

    experiment = Experiment(
        name=f'Segment Results {suffix}',
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


def _artifact(db_session, association, content, metadata=None, status='completed'):
    from app.models.experiment_processing import (
        ExperimentDocumentProcessing,
        ProcessingArtifact,
    )

    operation = ExperimentDocumentProcessing(
        experiment_document_id=association.id,
        processing_type='segmentation',
        processing_method=(metadata or {}).get('method', 'paragraph'),
        status=status,
    )
    db_session.add(operation)
    db_session.flush()
    artifact = ProcessingArtifact(
        processing_id=operation.id,
        document_id=association.document_id,
        artifact_type='text_segment',
        artifact_index=0,
    )
    artifact.set_content(content)
    artifact.set_metadata(metadata or {})
    db_session.add(artifact)
    db_session.commit()
    return artifact


def _segment(db_session, document, content, **kwargs):
    from app.models.text_segment import TextSegment

    segment = TextSegment(
        document_id=document.id,
        content=content,
        segment_number=kwargs.pop('segment_number', 1),
        **kwargs,
    )
    db_session.add(segment)
    db_session.commit()
    return segment


def test_segment_results_route_remains_canonical(app):
    assert app.view_functions['experiments.experiment_segments_results'].__module__ == (
        'app.routes.experiments.results.segments'
    )


def test_canonical_segment_artifacts_are_experiment_isolated(
    db_session, test_user, sample_document
):
    from app.services.experiment_segment_results_service import (
        ExperimentSegmentResultsService,
    )

    first = _experiment(db_session, test_user, 'first')
    second = _experiment(db_session, test_user, 'second')
    first_link = _association(db_session, first, sample_document)
    second_link = _association(db_session, second, sample_document)
    _artifact(
        db_session,
        first_link,
        {'text': 'first-only segment', 'segment_type': 'paragraph'},
        {'method': 'paragraph', 'word_count': 2},
    )
    _artifact(
        db_session,
        second_link,
        {'text': 'second-only segment', 'segment_type': 'sentence'},
        {'method': 'sentence'},
    )

    first_context = ExperimentSegmentResultsService.get_context(first.id)
    second_context = ExperimentSegmentResultsService.get_context(second.id)
    assert [item['content'] for item in first_context['segments']] == [
        'first-only segment'
    ]
    assert [item['content'] for item in second_context['segments']] == [
        'second-only segment'
    ]


def test_ambiguous_source_segments_do_not_leak_between_experiments(
    db_session, test_user, sample_document
):
    from app.services.experiment_segment_results_service import (
        ExperimentSegmentResultsService,
    )

    first = _experiment(db_session, test_user, 'shared-first')
    second = _experiment(db_session, test_user, 'shared-second')
    _association(db_session, first, sample_document)
    _association(db_session, second, sample_document)
    _segment(db_session, sample_document, 'Ambiguous shared source segment.')

    assert ExperimentSegmentResultsService.get_context(first.id)['segments'] == []
    assert ExperimentSegmentResultsService.get_context(second.id)['segments'] == []


def test_exclusive_source_segment_remains_legacy_fallback(
    db_session, test_user, sample_document
):
    from app.services.experiment_segment_results_service import (
        ExperimentSegmentResultsService,
    )

    experiment = _experiment(db_session, test_user, 'exclusive')
    _association(db_session, experiment, sample_document)
    _segment(
        db_session,
        sample_document,
        'Exclusive legacy segment.',
        segment_type='sentence',
    )
    result = ExperimentSegmentResultsService.get_context(experiment.id)['segments'][0]
    assert result['content'] == 'Exclusive legacy segment.'
    assert result['method'] == 'sentence'
    assert result['source'] == 'text_segment'


def test_experiment_owned_version_segments_are_visible_without_v2_association(
    db_session, test_user, sample_document
):
    from app.models.document import Document
    from app.services.experiment_segment_results_service import (
        ExperimentSegmentResultsService,
    )

    experiment = _experiment(db_session, test_user, 'owned-version')
    _association(db_session, experiment, sample_document)
    version = Document(
        title='Experiment segmentation version',
        content='Version content',
        content_type='text',
        document_type='document',
        status='completed',
        user_id=test_user.id,
        source_document_id=sample_document.id,
        version_number=2,
        version_type='experimental',
        experiment_id=experiment.id,
    )
    db_session.add(version)
    db_session.commit()
    _segment(
        db_session,
        version,
        'Owned version segment.',
        segment_type='paragraph',
    )
    context = ExperimentSegmentResultsService.get_context(experiment.id)
    assert context['documents'] == [version]
    assert [item['content'] for item in context['segments']] == [
        'Owned version segment.'
    ]


def test_canonical_artifacts_take_precedence_over_text_segments(
    db_session, test_user, sample_document
):
    from app.services.experiment_segment_results_service import (
        ExperimentSegmentResultsService,
    )

    experiment = _experiment(db_session, test_user, 'precedence')
    association = _association(db_session, experiment, sample_document)
    _segment(db_session, sample_document, 'Legacy duplicate segment.')
    _artifact(
        db_session,
        association,
        {'text': 'Canonical segment.', 'segment_type': 'semantic'},
    )
    context = ExperimentSegmentResultsService.get_context(experiment.id)
    assert [item['content'] for item in context['segments']] == [
        'Canonical segment.'
    ]


def test_failed_canonical_operation_allows_owned_fallback(
    db_session, test_user, sample_document
):
    from app.services.experiment_segment_results_service import (
        ExperimentSegmentResultsService,
    )

    experiment = _experiment(db_session, test_user, 'failed')
    association = _association(db_session, experiment, sample_document)
    _artifact(
        db_session,
        association,
        {'text': 'Failed canonical segment.'},
        status='failed',
    )
    _segment(db_session, sample_document, 'Completed fallback segment.')
    context = ExperimentSegmentResultsService.get_context(experiment.id)
    assert [item['content'] for item in context['segments']] == [
        'Completed fallback segment.'
    ]


def test_normalization_grouping_sorting_and_statistics(
    db_session, test_user, sample_documents
):
    from app.services.experiment_segment_results_service import (
        ExperimentSegmentResultsService,
    )

    experiment = _experiment(db_session, test_user, 'stats')
    newer, older = sample_documents[:2]
    newer.publication_date = date(2020, 1, 1)
    older.publication_date = date(1990, 1, 1)
    newer_link = _association(db_session, experiment, newer)
    older_link = _association(db_session, experiment, older)
    _artifact(
        db_session,
        newer_link,
        {'text': 'three word segment', 'segment_type': 'paragraph'},
        {'word_count': 3},
    )
    string_artifact = _artifact(
        db_session,
        older_link,
        {'placeholder': True},
        {'method': 'sentence', 'word_count': 2},
    )
    string_artifact.content_json = json.dumps('two words')
    db_session.commit()

    context = ExperimentSegmentResultsService.get_context(experiment.id)
    assert [item['content'] for item in context['segments']] == [
        'two words',
        'three word segment',
    ]
    assert context['segments'][0]['method'] == 'sentence'
    assert context['total_segments'] == 2
    assert context['avg_words'] == 2.5
    assert context['avg_length'] == (
        len('two words') + len('three word segment')
    ) / 2
    assert set(context['segments_by_document']) == {newer.id, older.id}


def test_empty_missing_and_route_contracts(
    client, db_session, test_user, sample_document
):
    from app.services.base_service import NotFoundError
    from app.services.experiment_segment_results_service import (
        ExperimentSegmentResultsService,
    )

    empty = _experiment(db_session, test_user, 'empty')
    context = ExperimentSegmentResultsService.get_context(empty.id)
    assert context['segments'] == []
    assert context['avg_words'] == 0
    with pytest.raises(NotFoundError):
        ExperimentSegmentResultsService.get_context(999999)

    experiment = _experiment(db_session, test_user, 'route')
    association = _association(db_session, experiment, sample_document)
    _artifact(
        db_session,
        association,
        {'text': 'Rendered segment.', 'segment_type': 'paragraph'},
    )
    response = client.get(f'/experiments/{experiment.id}/results/segments')
    missing = client.get('/experiments/999999/results/segments')
    assert response.status_code == 200
    assert b'Rendered segment.' in response.data
    assert missing.status_code == 404
