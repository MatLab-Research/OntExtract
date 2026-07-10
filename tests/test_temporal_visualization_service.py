"""Regression coverage for evidence-based temporal visualization APIs."""

from datetime import date
from decimal import Decimal

import pytest


def _link_documents(db_session, experiment, documents):
    from app.models.experiment_document import ExperimentDocument

    for document in documents:
        db_session.add(ExperimentDocument(
            experiment_id=experiment.id,
            document_id=document.id,
        ))
    db_session.commit()


def test_temporal_visualization_routes_remain_canonical(app):
    expected = 'app.routes.temporal_visual.api'
    for endpoint in (
        'temporal_visual.get_experiment_data',
        'temporal_visual.analyze_temporal_evolution',
        'temporal_visual.get_document_details',
        'temporal_visual.list_temporal_experiments',
    ):
        assert app.view_functions[endpoint].__module__ == expected


def test_experiment_data_uses_canonical_documents_and_real_years(
    db_session, temporal_experiment, sample_documents
):
    from app.models.temporal_experiment import DocumentTemporalMetadata
    from app.services.temporal_visualization_service import (
        TemporalVisualizationService,
    )

    first, second = sample_documents[:2]
    first.publication_date = date(1990, 5, 1)
    second.publication_date = None
    _link_documents(db_session, temporal_experiment, [first, second])
    db_session.add(DocumentTemporalMetadata(
        document_id=second.id,
        experiment_id=temporal_experiment.id,
        publication_year=2005,
    ))
    db_session.commit()

    payload = TemporalVisualizationService.get_experiment_data(
        temporal_experiment.id
    )
    documents = {item['id']: item for item in payload['documents']}
    assert set(documents) == {first.id, second.id}
    assert documents[first.id]['year'] == 1990
    assert documents[second.id]['year'] == 2005
    assert payload['temporal_data']['terms_tracked'] == ['algorithm']
    assert payload['temporal_data']['analysis_results'] == []


def test_analysis_groups_real_documents_and_is_repeatable(
    db_session, temporal_experiment, sample_documents
):
    from app.services.temporal_visualization_service import (
        TemporalVisualizationService,
    )

    first, second, outside = sample_documents[:3]
    first.publication_date = date(1990, 1, 1)
    second.publication_date = date(1997, 1, 1)
    outside.publication_date = date(2015, 1, 1)
    _link_documents(
        db_session,
        temporal_experiment,
        [first, second, outside],
    )
    db_session.commit()
    request = {
        'term': 'algorithm',
        'time_range': '1990-2004',
        'period_length': 5,
        'experiment_id': temporal_experiment.id,
    }

    first_result = TemporalVisualizationService.analyze(request)
    second_result = TemporalVisualizationService.analyze(request)

    assert first_result == second_result
    assert [period['label'] for period in first_result['periods']] == [
        '1990-1994',
        '1995-1999',
        '2000-2004',
    ]
    assert [
        item['id']
        for item in first_result['documents_by_period']['period-1990']
    ] == [first.id]
    assert [
        item['id']
        for item in first_result['documents_by_period']['period-1995']
    ] == [second.id]
    assert first_result['analysis_results']['documents_analyzed'] == 2
    assert first_result['analysis_results']['semantic_drift'] is None
    assert first_result['analysis_results']['context_stability'] is None
    assert first_result['analysis_results']['confidence_score'] is None
    assert 'No stored semantic shift analyses' in (
        first_result['analysis_results']['key_findings'][0]
    )


def test_analysis_reports_stored_shift_evidence_and_confidence(
    db_session, temporal_experiment, sample_term
):
    from app.models.temporal_experiment import SemanticShiftAnalysis
    from app.services.temporal_visualization_service import (
        TemporalVisualizationService,
    )

    shifts = [
        SemanticShiftAnalysis(
            experiment_id=temporal_experiment.id,
            term_id=sample_term.id,
            shift_type='broadening',
            from_period='1990-1999',
            to_period='2000-2009',
            description='Algorithm broadened into everyday policy discourse.',
            confidence=Decimal('0.80'),
        ),
        SemanticShiftAnalysis(
            experiment_id=temporal_experiment.id,
            term_id=sample_term.id,
            shift_type='domain_shift',
            from_period='2000-2009',
            to_period='2010-2020',
            description='Usage shifted toward automated decision systems.',
            confidence=Decimal('0.90'),
        ),
    ]
    db_session.add_all(shifts)
    db_session.commit()

    payload = TemporalVisualizationService.analyze({
        'term': 'algorithm',
        'time_range': '1990-2020',
        'period_length': 10,
        'experiment_id': temporal_experiment.id,
    })
    analysis = payload['analysis_results']
    assert analysis['stored_shift_count'] == 2
    assert analysis['confidence_score'] == '85%'
    assert analysis['semantic_drift'] is None
    assert analysis['key_findings'] == [
        shifts[0].description,
        shifts[1].description,
    ]


def test_analysis_does_not_leak_other_experiment_shifts(
    db_session, temporal_experiment, entity_extraction_experiment, sample_term
):
    from app.models.temporal_experiment import SemanticShiftAnalysis
    from app.services.temporal_visualization_service import (
        TemporalVisualizationService,
    )

    db_session.add(SemanticShiftAnalysis(
        experiment_id=entity_extraction_experiment.id,
        term_id=sample_term.id,
        shift_type='domain_shift',
        description='Other experiment evidence.',
        confidence=Decimal('0.99'),
    ))
    db_session.commit()

    payload = TemporalVisualizationService.analyze({
        'term': 'algorithm',
        'time_range': '2000-2024',
        'period_length': 5,
        'experiment_id': temporal_experiment.id,
    })
    assert payload['analysis_results']['stored_shift_count'] == 0
    assert payload['analysis_results']['confidence_score'] is None


def test_document_details_uses_publication_and_temporal_fallback(
    db_session, sample_document, temporal_experiment
):
    from app.models.temporal_experiment import DocumentTemporalMetadata
    from app.services.temporal_visualization_service import (
        TemporalVisualizationService,
    )

    sample_document.publication_date = None
    db_session.add(DocumentTemporalMetadata(
        document_id=sample_document.id,
        experiment_id=temporal_experiment.id,
        publication_year=1984,
    ))
    db_session.commit()

    details = TemporalVisualizationService.get_document_details(
        sample_document.id
    )
    assert details['year'] == 1984
    assert details['content_preview'] == sample_document.content[:500]


def test_temporal_experiment_list_counts_canonical_documents_and_references(
    db_session,
    temporal_experiment,
    sample_documents,
    sample_document,
):
    from app.services.temporal_visualization_service import (
        TemporalVisualizationService,
    )

    _link_documents(
        db_session,
        temporal_experiment,
        sample_documents[:2],
    )
    sample_document.document_type = 'reference'
    temporal_experiment.references.append(sample_document)
    db_session.commit()

    payload = TemporalVisualizationService.list_temporal_experiments()
    item = next(
        experiment for experiment in payload['experiments']
        if experiment['id'] == temporal_experiment.id
    )
    assert item['document_count'] == 2
    assert item['reference_count'] == 1


@pytest.mark.parametrize(
    ('payload', 'message'),
    [
        (None, 'JSON payload required'),
        ({'term': ''}, 'Term is required'),
        (
            {'term': 'algorithm', 'time_range': 'not-a-range'},
            'Invalid time range format',
        ),
        (
            {'term': 'algorithm', 'time_range': '2024-2000'},
            'Start year must not exceed end year',
        ),
        (
            {'term': 'algorithm', 'period_length': 0},
            'period_length must be a positive integer',
        ),
    ],
)
def test_temporal_analysis_validation(payload, message):
    from app.services.base_service import ValidationError
    from app.services.temporal_visualization_service import (
        TemporalVisualizationService,
    )

    with pytest.raises(ValidationError, match=message):
        TemporalVisualizationService.analyze(payload)


def test_temporal_visual_api_contracts(
    client, db_session, temporal_experiment, sample_documents
):
    first = sample_documents[0]
    first.publication_date = date(2001, 1, 1)
    _link_documents(db_session, temporal_experiment, [first])
    db_session.commit()

    data = client.get(
        f'/temporal-visual/api/experiment/{temporal_experiment.id}/data'
    )
    analysis = client.post('/temporal-visual/api/analyze', json={
        'term': 'algorithm',
        'time_range': '2000-2004',
        'period_length': 5,
        'experiment_id': temporal_experiment.id,
    })
    detail = client.get(
        f'/temporal-visual/api/documents/{first.id}/details'
    )
    experiments = client.get('/temporal-visual/api/experiments/temporal')
    invalid = client.post('/temporal-visual/api/analyze', json={'term': ''})
    missing = client.get('/temporal-visual/api/experiment/999999/data')

    assert data.status_code == 200
    assert data.get_json()['documents'][0]['year'] == 2001
    assert analysis.status_code == 200
    assert analysis.get_json()['analysis_results']['documents_analyzed'] == 1
    assert detail.status_code == 200
    assert detail.get_json()['year'] == 2001
    assert experiments.status_code == 200
    assert invalid.status_code == 400
    assert missing.status_code == 404


def test_temporal_visualization_contains_no_random_demo_analysis():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    files = [
        root / 'app/routes/temporal_visual/api.py',
        root / 'app/services/temporal_visualization_service.py',
        root / 'app/templates/experiments/temporal_evolution_visual.html',
    ]
    content = '\n'.join(path.read_text() for path in files)
    assert 'random.uniform' not in content
    assert 'random.randint' not in content
    assert 'Math.random' not in content
    assert 'generateSampleData' not in content
    assert "fetch('/temporal-visual/api/analyze'" in content
