"""Regression coverage for OED term enrichment and persisted-data APIs."""

from decimal import Decimal

import pytest


class EnrichmentRecorder:
    def __init__(self, result=None, error=None):
        self.result = result or {
            'success': True,
            'etymology_created': True,
            'definitions_created': 2,
            'historical_stats_created': 1,
            'quotation_summaries_created': 3,
        }
        self.error = error
        self.calls = []

    def enrich_term_with_oed_data(self, term_id, entry_id=None):
        self.calls.append((term_id, entry_id))
        if self.error:
            raise self.error
        return self.result


class SearchRecorder:
    def __init__(self, result=None, error=None):
        self.result = result or {
            'success': True,
            'suggestions': [{'entry_id': 'agency_nn01'}],
        }
        self.error = error
        self.calls = []

    def suggest_ids(self, term, limit=10):
        self.calls.append((term, limit))
        if self.error:
            raise self.error
        return self.result


def _user(db_session, suffix):
    from app.models.user import User

    user = User(
        username=f'oed-term-api-{suffix}',
        email=f'oed-term-api-{suffix}@example.com',
        password='password',
        account_status='active',
    )
    db_session.add(user)
    db_session.commit()
    return user


def _term(db_session, user, text='agency'):
    from app.models.term import Term

    term = Term(term_text=text, status='active', created_by=user.id)
    db_session.add(term)
    db_session.commit()
    return term


def _experiment(db_session, user, term=None, suffix='context'):
    from app.models.experiment import Experiment

    experiment = Experiment(
        name=f'OED Term API {suffix}',
        experiment_type='temporal_evolution',
        user_id=user.id,
        term_id=term.id if term else None,
        status='draft',
    )
    db_session.add(experiment)
    db_session.commit()
    return experiment


def _service(enrichment=None, search=None):
    from app.services.oed_term_api_service import OEDTermApiService

    return OEDTermApiService(
        enrichment or EnrichmentRecorder(),
        search or SearchRecorder(),
    )


def test_oed_term_api_routes_remain_canonical(app):
    expected = 'app.routes.api'
    for endpoint in (
        'api.enrich_term_with_oed',
        'api.get_term_oed_data',
        'api.search_oed_entries',
        'api.health_check',
    ):
        assert app.view_functions[endpoint].__module__ == expected


def test_enrichment_resolves_experiment_term_and_forwards_entry_id(
    db_session, test_user
):
    owner_term = _term(db_session, test_user, 'agency')
    other = _user(db_session, 'duplicate-owner')
    _term(db_session, other, 'agency')
    experiment = _experiment(db_session, test_user, owner_term)
    enrichment = EnrichmentRecorder()

    result = _service(enrichment=enrichment).enrich(
        '  Agency  ',
        test_user.id,
        experiment_id=experiment.id,
        entry_id='  agency_nn01  ',
    )

    assert result['success'] is True
    assert enrichment.calls == [(str(owner_term.id), 'agency_nn01')]


def test_enrichment_without_experiment_uses_actor_owned_duplicate(
    db_session, test_user
):
    other = _user(db_session, 'first-owner')
    _term(db_session, other, 'agent')
    actor_term = _term(db_session, test_user, 'agent')
    enrichment = EnrichmentRecorder()
    _service(enrichment=enrichment).enrich('agent', test_user.id)
    assert enrichment.calls == [(str(actor_term.id), None)]


def test_admin_can_enrich_any_matching_term(db_session, admin_user):
    owner = _user(db_session, 'admin-target-owner')
    term = _term(db_session, owner, 'action')
    enrichment = EnrichmentRecorder()
    _service(enrichment=enrichment).enrich('action', admin_user.id)
    assert enrichment.calls == [(str(term.id), None)]


def test_enrichment_rejects_unauthorized_term_and_experiment(
    db_session, test_user
):
    from app.services.base_service import PermissionError

    owner = _user(db_session, 'protected-owner')
    term = _term(db_session, owner, 'protected')
    experiment = _experiment(db_session, owner, term, 'protected')
    enrichment = EnrichmentRecorder()
    service = _service(enrichment=enrichment)

    with pytest.raises(PermissionError):
        service.enrich('protected', test_user.id)
    with pytest.raises(PermissionError):
        service.enrich(
            'protected',
            test_user.id,
            experiment_id=experiment.id,
        )
    assert enrichment.calls == []


def test_enrichment_validates_missing_resources_before_upstream_call(
    test_user
):
    from app.services.base_service import NotFoundError, ValidationError

    enrichment = EnrichmentRecorder()
    service = _service(enrichment=enrichment)
    with pytest.raises(ValidationError, match='term_text is required'):
        service.enrich(' ', test_user.id)
    with pytest.raises(NotFoundError, match='Term'):
        service.enrich('not-in-database', test_user.id)
    with pytest.raises(NotFoundError, match='Experiment not found'):
        service.enrich('agency', test_user.id, experiment_id='invalid')
    assert enrichment.calls == []


@pytest.mark.parametrize(
    'enrichment',
    [
        EnrichmentRecorder(result={'success': False, 'error': 'secret detail'}),
        EnrichmentRecorder(error=RuntimeError('secret exception detail')),
    ],
)
def test_enrichment_failures_raise_sanitized_error(
    db_session, test_user, enrichment
):
    from app.services.oed_term_api_service import OEDTermUpstreamError

    _term(db_session, test_user, 'failure-term')
    with pytest.raises(OEDTermUpstreamError) as exc:
        _service(enrichment=enrichment).enrich('failure-term', test_user.id)
    assert str(exc.value) == 'OED term enrichment failed'
    assert 'secret' not in str(exc.value)


def test_persisted_oed_data_is_sorted_and_serialized(
    db_session, test_user
):
    from app.models.oed_models import (
        OEDDefinition,
        OEDEtymology,
        OEDHistoricalStats,
        OEDQuotationSummary,
    )
    from app.services.oed_term_api_service import OEDTermApiService

    term = _term(db_session, test_user, 'history')
    etymology = OEDEtymology(
        term_id=term.id,
        etymology_text='Historical origin.',
        first_recorded_year=1500,
    )
    later = OEDDefinition(
        term_id=term.id,
        definition_number='2',
        definition_excerpt='Later sense.',
        first_cited_year=1900,
        last_cited_year=2020,
    )
    earlier = OEDDefinition(
        term_id=term.id,
        definition_number='1',
        definition_excerpt='Earlier sense.',
        first_cited_year=1600,
        last_cited_year=1850,
    )
    stats = OEDHistoricalStats(
        term_id=term.id,
        time_period='1600-1700',
        start_year=1600,
        end_year=1700,
        semantic_stability_score=Decimal('0.750'),
    )
    quotation = OEDQuotationSummary(
        term_id=term.id,
        quotation_year=1650,
        author_name='Example Author',
        chronological_rank=1,
    )
    db_session.add_all([etymology, later, earlier, stats, quotation])
    db_session.commit()

    data = OEDTermApiService.get_persisted_data(term.id)
    assert data['term_text'] == 'history'
    assert data['etymology']['etymology_text'] == 'Historical origin.'
    assert [item['definition_number'] for item in data['definitions']] == [
        '1',
        '2',
    ]
    assert data['historical_stats'][0]['semantic_stability_score'] == 0.75
    assert data['quotation_summaries'][0]['quotation_year'] == 1650
    assert data['date_range'] == {'earliest': 1600, 'latest': 2020}


def test_persisted_data_rejects_malformed_and_missing_ids():
    from app.services.base_service import NotFoundError
    from app.services.oed_term_api_service import OEDTermApiService

    with pytest.raises(NotFoundError, match='Term not found'):
        OEDTermApiService.get_persisted_data('not-a-uuid')
    with pytest.raises(NotFoundError, match='Term not found'):
        OEDTermApiService.get_persisted_data(
            '00000000-0000-0000-0000-000000000000'
        )


def test_search_normalizes_term_and_bounds_limit():
    from app.services.base_service import ValidationError

    search = SearchRecorder()
    service = _service(search=search)
    result = service.search('  agency  ', 500)
    assert result['success'] is True
    assert search.calls == [('agency', 50)]
    with pytest.raises(ValidationError, match='limit must be an integer'):
        service.search('agency', 'invalid')
    with pytest.raises(ValidationError, match='term parameter is required'):
        service.search('', 10)


@pytest.mark.parametrize(
    'search',
    [
        SearchRecorder(result={'success': False, 'error': 'secret'}),
        SearchRecorder(error=RuntimeError('secret transport detail')),
    ],
)
def test_search_failures_are_sanitized(search):
    from app.services.oed_term_api_service import OEDTermUpstreamError

    with pytest.raises(OEDTermUpstreamError) as exc:
        _service(search=search).search('agency')
    assert str(exc.value) == 'OED search failed'


def test_oed_term_routes_delegate_and_preserve_contracts(
    app, auth_client, db_session, test_user, monkeypatch
):
    from app.routes import api

    term = _term(db_session, test_user, 'route-term')

    class FakeService:
        def enrich(self, term_text, actor_id, experiment_id=None, entry_id=None):
            return {
                'success': True,
                'term_text': term_text,
                'definitions_created': 1,
            }

        def search(self, term_text, limit=10):
            return {'success': True, 'term': term_text, 'limit': int(limit)}

    monkeypatch.setattr(api, '_service', lambda: FakeService())
    client = app.test_client()
    search = client.get('/api/terms/search-oed?term=agency&limit=3')
    health = client.get('/api/health')
    missing_data = client.get('/api/terms/not-a-uuid/oed-data')
    enrich = auth_client.post(
        '/api/terms/enrich-oed',
        json={'term_text': term.term_text},
    )

    assert search.get_json() == {'success': True, 'term': 'agency', 'limit': 3}
    assert health.get_json() == {'status': 'healthy', 'service': 'OntExtract API'}
    assert missing_data.status_code == 404
    assert enrich.status_code == 200
    assert enrich.get_json()['definitions_created'] == 1


def test_oed_term_enrichment_requires_authentication(app):
    response = app.test_client().post(
        '/api/terms/enrich-oed',
        json={'term_text': 'agency'},
    )
    assert response.status_code == 401


def test_oed_term_routes_map_sanitized_errors(app, monkeypatch):
    from app.routes import api
    from app.services.oed_term_api_service import OEDTermUpstreamError

    class FailureService:
        def search(self, term_text, limit=10):
            raise OEDTermUpstreamError('secret search transport detail')

    monkeypatch.setattr(api, '_service', lambda: FailureService())
    failure = app.test_client().get('/api/terms/search-oed?term=agency')
    assert failure.status_code == 502
    assert failure.get_json() == {
        'success': False,
        'error': 'OED search failed',
    }
    assert 'secret' not in str(failure.get_json())
