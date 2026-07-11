"""Regression coverage for temporal ontology catalog read models."""

from pathlib import Path
from types import SimpleNamespace

import pytest


class LocalOntologyStub:
    def __init__(self, ontology_path='/repo/ontologies/events.ttl', error=None):
        self.ontology_path = Path(ontology_path)
        self.error = error

    def get_all_for_dropdown(self):
        if self.error:
            raise self.error
        return [{
            'value': 'broadening',
            'label': 'Broadening',
            'definition': 'Meaning becomes more general.',
            'citation': 'Test citation',
            'example': 'Example usage',
            'uri': 'http://example.org/Broadening',
        }]

    def get_semantic_change_event_types(self):
        if self.error:
            raise self.error
        return [SimpleNamespace(
            label='Broadening',
            definition='Meaning becomes more general.',
            citation='Test citation',
        )]


class PeriodClientStub:
    def __init__(self, error=None):
        self.error = error

    def get_period_types(self):
        if self.error:
            raise self.error
        return [{
            'name': 'HistoricalPeriod',
            'label': 'Historical Period',
            'description': 'A historical span.',
            'uri': 'http://example.org/HistoricalPeriod',
            'color': '#123456',
            'icon': 'fas fa-landmark',
        }]


def _service(local=None, periods=None, repository_root='/repo'):
    from app.services.temporal_ontology_service import TemporalOntologyService

    return TemporalOntologyService(
        local_ontology=local or LocalOntologyStub(),
        period_client=periods or PeriodClientStub(),
        repository_root=repository_root,
    )


def test_temporal_ontology_routes_remain_canonical(app):
    expected = 'app.routes.experiments.temporal.ontology'
    for endpoint in (
        'experiments.ontology_info',
        'experiments.get_semantic_event_types',
        'experiments.get_period_types',
    ):
        assert app.view_functions[endpoint].__module__ == expected


def test_event_catalog_and_lookup_use_local_ontology():
    service = _service()
    catalog = service.get_event_catalog()

    assert catalog == {
        'success': True,
        'event_types': [{
            'value': 'broadening',
            'label': 'Broadening',
            'definition': 'Meaning becomes more general.',
            'citation': 'Test citation',
            'example': 'Example usage',
            'uri': 'http://example.org/Broadening',
        }],
        'count': 1,
        'source': 'semantic-change-ontology-v2.ttl',
    }
    assert service.get_event_type('broadening')['label'] == 'Broadening'
    assert service.get_event_type('missing') is None


def test_event_catalog_returns_stable_fallback_on_load_error():
    catalog = _service(
        local=LocalOntologyStub(error=RuntimeError('TTL unavailable'))
    ).get_event_catalog()

    assert catalog['success'] is True
    assert catalog['source'] == 'fallback (ontology load failed)'
    assert catalog['error'] == 'TTL unavailable'
    assert catalog['count'] == 3
    assert {item['value'] for item in catalog['event_types']} == {
        'pejoration',
        'amelioration',
        'semantic_drift',
    }


def test_period_catalog_transforms_client_contract():
    catalog = _service().get_period_catalog()

    assert catalog == {
        'success': True,
        'period_types': [{
            'value': 'HistoricalPeriod',
            'label': 'Historical Period',
            'description': 'A historical span.',
            'uri': 'http://example.org/HistoricalPeriod',
            'color': '#123456',
            'icon': 'fas fa-landmark',
        }],
        'count': 1,
        'source': 'ontology',
    }


def test_period_catalog_returns_stable_fallback_on_client_error():
    catalog = _service(
        periods=PeriodClientStub(error=RuntimeError('OntServe unavailable'))
    ).get_period_catalog()

    assert catalog['success'] is True
    assert catalog['source'] == 'fallback (ontology load failed)'
    assert catalog['error'] == 'OntServe unavailable'
    assert catalog['count'] == 4
    assert catalog['period_types'][0]['value'] == 'HistoricalPeriod'


def test_event_catalog_validates_temporal_experiment(
    db_session, temporal_experiment, entity_extraction_experiment
):
    from app.services.base_service import NotFoundError, ValidationError

    assert _service().get_event_catalog(temporal_experiment.id)['count'] == 1
    with pytest.raises(ValidationError, match='only available for temporal'):
        _service().get_event_catalog(entity_extraction_experiment.id)
    with pytest.raises(NotFoundError, match='Experiment not found'):
        _service().get_event_catalog(999999)


def test_ontology_info_context_uses_repository_relative_path(tmp_path):
    ontology_dir = tmp_path / 'ontologies'
    ontology_dir.mkdir()
    ontology_path = ontology_dir / 'events.ttl'
    ontology_path.write_text('ontology')
    (tmp_path / 'VALIDATION_GUIDE.md').write_text('validation')

    context = _service(
        local=LocalOntologyStub(ontology_path=ontology_path),
        repository_root=tmp_path,
    ).get_info_context()

    assert context['event_count'] == 1
    assert context['ontology_path'] == 'ontologies/events.ttl'
    assert context['validation_exists'] is True


def test_semantic_event_service_uses_catalog_lookup(
    db_session, test_user, temporal_experiment
):
    from app.services.semantic_event_service import SemanticEventService

    catalog = _service()
    service = SemanticEventService(
        ontology_service=catalog,
        provenance_service=SimpleNamespace(
            track_semantic_event=lambda **kwargs: None
        ),
        id_factory=lambda: 'catalog-event-id',
    )
    event = service.save(
        temporal_experiment.id,
        {
            'event_type': 'broadening',
            'from_period': 1990,
            'description': 'Catalog-enriched event.',
        },
        test_user,
    )['semantic_events'][0]

    assert event['type_label'] == 'Broadening'
    assert event['type_uri'] == 'http://example.org/Broadening'


def test_temporal_ontology_route_contracts(
    client, temporal_experiment, entity_extraction_experiment
):
    info = client.get('/experiments/ontology/info')
    events = client.get(
        f'/experiments/{temporal_experiment.id}/semantic_event_types'
    )
    wrong_type = client.get(
        f'/experiments/{entity_extraction_experiment.id}/semantic_event_types'
    )
    missing = client.get('/experiments/999999/semantic_event_types')
    periods = client.get('/experiments/period_types')

    assert info.status_code == 200
    assert b'Semantic Change Ontology' in info.data
    assert events.status_code == 200
    assert events.get_json()['success'] is True
    assert events.get_json()['event_types']
    assert wrong_type.status_code == 400
    assert missing.status_code == 404
    assert periods.status_code == 200
    assert periods.get_json()['success'] is True
    assert periods.get_json()['period_types']
