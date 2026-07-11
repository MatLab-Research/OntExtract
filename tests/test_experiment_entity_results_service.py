"""Regression coverage for experiment-scoped entity result read models."""

import json
from datetime import date

import pytest


def _experiment(db_session, user, suffix):
    from app.models.experiment import Experiment

    experiment = Experiment(
        name=f'Entity Results {suffix}',
        experiment_type='entity_extraction',
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
        processing_type='entities',
        processing_method=(metadata or {}).get('method', 'spacy'),
        status=status,
    )
    db_session.add(operation)
    db_session.flush()
    artifact = ProcessingArtifact(
        processing_id=operation.id,
        document_id=association.document_id,
        artifact_type='extracted_entity',
        artifact_index=0,
    )
    artifact.set_content(content)
    artifact.set_metadata(metadata or {})
    db_session.add(artifact)
    db_session.commit()
    return artifact


def _legacy_entity(db_session, user, document, text, status='completed'):
    from app.models.extracted_entity import ExtractedEntity
    from app.models.processing_job import ProcessingJob

    job = ProcessingJob(
        document_id=document.id,
        user_id=user.id,
        job_type='entity_extraction',
        status=status,
    )
    db_session.add(job)
    db_session.flush()
    entity = ExtractedEntity(
        processing_job_id=job.id,
        entity_text=text,
        entity_type='CONCEPT',
        context_before='before',
        context_after='after',
        start_position=2,
        end_position=8,
        confidence_score=0.72,
        extraction_method='manual-review',
    )
    db_session.add(entity)
    db_session.commit()
    return entity


def test_entity_results_route_remains_canonical(app):
    assert app.view_functions['experiments.experiment_entities_results'].__module__ == (
        'app.routes.experiments.results.entities'
    )


def test_canonical_entities_are_experiment_isolated(
    db_session, test_user, sample_document
):
    from app.services.experiment_entity_results_service import (
        ExperimentEntityResultsService,
    )

    first = _experiment(db_session, test_user, 'first')
    second = _experiment(db_session, test_user, 'second')
    first_link = _association(db_session, first, sample_document)
    second_link = _association(db_session, second, sample_document)
    _artifact(
        db_session,
        first_link,
        {'entity': 'first-only', 'type': 'FIELD', 'confidence': 0.9},
        {'method': 'spacy_ner'},
    )
    _artifact(
        db_session,
        second_link,
        {'text': 'second-only', 'label': 'ORG', 'confidence': 0.8},
        {'method': 'zero_shot'},
    )

    first_context = ExperimentEntityResultsService.get_context(first.id)
    second_context = ExperimentEntityResultsService.get_context(second.id)
    assert [item['text'] for item in first_context['entities']] == ['first-only']
    assert first_context['entities'][0]['source'] == 'spacy_ner'
    assert [item['text'] for item in second_context['entities']] == ['second-only']
    assert second_context['entities'][0]['entity_type'] == 'ORG'


def test_artifact_normalization_grouping_and_sorting(
    db_session, test_user, sample_documents
):
    from app.services.experiment_entity_results_service import (
        ExperimentEntityResultsService,
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
            'entity': 'Zeta',
            'entity_type': 'CONCEPT',
            'start': 4,
            'end': 8,
            'confidence': 0.81,
            'context': 'structured context',
        },
    )
    string_artifact = _artifact(db_session, older_link, {'placeholder': True})
    string_artifact.content_json = json.dumps('Alpha')
    db_session.commit()

    context = ExperimentEntityResultsService.get_context(experiment.id)
    assert [item['text'] for item in context['entities']] == ['Alpha', 'Zeta']
    assert context['entities'][0]['entity_type'] == 'UNKNOWN'
    assert context['entities'][1]['start_position'] == 4
    assert context['entities'][1]['context'] == 'structured context'
    assert set(context['entities_by_type']) == {'UNKNOWN', 'CONCEPT'}
    assert set(context['entities_by_document']) == {newer.id, older.id}
    assert context['total_entities'] == 2


def test_legacy_entities_are_per_document_fallback(
    db_session, test_user, sample_documents
):
    from app.services.experiment_entity_results_service import (
        ExperimentEntityResultsService,
    )

    experiment = _experiment(db_session, test_user, 'legacy')
    canonical, legacy = sample_documents[:2]
    canonical_link = _association(db_session, experiment, canonical)
    _association(db_session, experiment, legacy)
    _artifact(
        db_session,
        canonical_link,
        {'entity': 'canonical', 'type': 'FIELD'},
    )
    _legacy_entity(db_session, test_user, canonical, 'duplicate')
    _legacy_entity(db_session, test_user, legacy, 'legacy')
    _legacy_entity(
        db_session,
        test_user,
        legacy,
        'failed',
        status='failed',
    )

    context = ExperimentEntityResultsService.get_context(experiment.id)
    texts = {item['text'] for item in context['entities']}
    assert texts == {'canonical', 'legacy'}
    legacy_result = next(
        item for item in context['entities'] if item['text'] == 'legacy'
    )
    assert legacy_result['source'] == 'manual-review'
    assert '[legacy]' in legacy_result['context']


def test_failed_canonical_operation_allows_legacy_fallback(
    db_session, test_user, sample_document
):
    from app.services.experiment_entity_results_service import (
        ExperimentEntityResultsService,
    )

    experiment = _experiment(db_session, test_user, 'failed')
    association = _association(db_session, experiment, sample_document)
    _artifact(
        db_session,
        association,
        {'entity': 'failed-canonical', 'type': 'ORG'},
        status='failed',
    )
    _legacy_entity(db_session, test_user, sample_document, 'fallback')
    context = ExperimentEntityResultsService.get_context(experiment.id)
    assert [item['text'] for item in context['entities']] == ['fallback']


def test_latest_document_version_is_used(db_session, test_user, sample_document):
    from app.models.document import Document
    from app.services.experiment_entity_results_service import (
        ExperimentEntityResultsService,
    )

    experiment = _experiment(db_session, test_user, 'versions')
    root_link = _association(db_session, experiment, sample_document)
    latest = Document(
        title='Latest entity document',
        content='Latest content',
        content_type='text',
        document_type='document',
        status='completed',
        user_id=test_user.id,
        source_document_id=sample_document.id,
        version_number=2,
        version_type='processed',
    )
    db_session.add(latest)
    db_session.commit()
    latest_link = _association(db_session, experiment, latest)
    _artifact(db_session, root_link, {'entity': 'old', 'type': 'ORG'})
    _artifact(db_session, latest_link, {'entity': 'latest', 'type': 'ORG'})
    context = ExperimentEntityResultsService.get_context(experiment.id)
    assert context['documents'] == [latest]
    assert [item['text'] for item in context['entities']] == ['latest']


def test_empty_missing_and_route_contracts(
    client, db_session, test_user, sample_document
):
    from app.services.base_service import NotFoundError
    from app.services.experiment_entity_results_service import (
        ExperimentEntityResultsService,
    )

    empty = _experiment(db_session, test_user, 'empty')
    assert ExperimentEntityResultsService.get_context(empty.id)['entities'] == []
    with pytest.raises(NotFoundError):
        ExperimentEntityResultsService.get_context(999999)

    experiment = _experiment(db_session, test_user, 'route')
    link = _association(db_session, experiment, sample_document)
    _artifact(
        db_session,
        link,
        {'entity': 'rendered-entity', 'type': 'CONCEPT'},
    )
    response = client.get(f'/experiments/{experiment.id}/results/entities')
    missing = client.get('/experiments/999999/results/entities')
    assert response.status_code == 200
    assert b'rendered-entity' in response.data
    assert missing.status_code == 404
