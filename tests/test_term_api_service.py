"""Regression coverage for term utility and fuzziness APIs."""

from decimal import Decimal
from types import SimpleNamespace

import pytest


def _term_with_version(db_session, user, suffix, **version_kwargs):
    from app.models.term import Term, TermVersion

    term = Term(
        term_text=f'agency-{suffix}',
        status='active',
        created_by=user.id,
    )
    db_session.add(term)
    db_session.flush()
    version = TermVersion(
        term_id=term.id,
        temporal_period='2000-present',
        temporal_start_year=2000,
        meaning_description='The capacity to act toward goals.',
        confidence_level='medium',
        created_by=user.id,
        **version_kwargs,
    )
    db_session.add(version)
    db_session.commit()
    return term, version


def _user(db_session, suffix):
    from app.models.user import User

    user = User(
        username=f'term-api-{suffix}',
        email=f'term-api-{suffix}@example.com',
        password='password',
        account_status='active',
    )
    db_session.add(user)
    db_session.commit()
    return user


def _anchor(db_session, term, frequency):
    from app.models.context_anchor import ContextAnchor

    anchor = ContextAnchor(anchor_term=term, frequency=frequency)
    db_session.add(anchor)
    db_session.commit()
    return anchor


def test_term_api_routes_remain_canonical(app):
    expected = 'app.routes.terms.api'
    for endpoint in (
        'terms.api_context_anchors',
        'terms.api_term_search',
        'terms.adjust_fuzziness',
        'terms.api_discover_context_anchors',
        'terms.api_calculate_fuzziness',
    ):
        assert app.view_functions[endpoint].__module__ == expected


def test_autocomplete_searches_and_bounds_limits(
    db_session, test_user
):
    from app.services.term_api_service import TermApiService

    frequent = _anchor(db_session, 'machine learning', 10)
    _anchor(db_session, 'deep learning', 5)
    _anchor(db_session, 'agency', 20)
    _term_with_version(db_session, test_user, 'searchable')

    anchors = TermApiService.search_context_anchors('learning', 1)
    terms = TermApiService.search_terms('searchable', -5)

    assert anchors == [{
        'id': str(frequent.id),
        'term': 'machine learning',
        'frequency': 10,
    }]
    assert len(terms) == 1
    assert terms[0]['term_text'] == 'agency-searchable'


def test_context_discovery_falls_back_to_existing_anchors(
    db_session
):
    from app.services.term_api_service import TermApiService

    first = _anchor(db_session, 'highest frequency', 30)
    _anchor(db_session, 'second frequency', 20)
    results = TermApiService.discover_context_anchors(
        'agency',
        limit=1,
        analysis_service=None,
    )
    assert results == [{
        'term': first.anchor_term,
        'frequency': 30,
        'similarity': 0.0,
        'source': 'existing',
    }]


def test_context_discovery_uses_embeddings_and_skips_failed_anchor(
    db_session
):
    from app.services.term_api_service import TermApiService

    _anchor(db_session, 'high similarity', 10)
    _anchor(db_session, 'low similarity', 9)
    _anchor(db_session, 'broken anchor', 8)

    class Embeddings:
        @staticmethod
        def is_available():
            return True

        @staticmethod
        def get_embedding(text):
            if text == 'broken anchor':
                raise RuntimeError('embedding unavailable')
            return text

        @staticmethod
        def similarity(term_embedding, anchor_embedding):
            return {
                'high similarity': 0.9126,
                'low similarity': 0.3214,
            }[anchor_embedding]

    results = TermApiService.discover_context_anchors(
        'agency',
        'A capacity to act.',
        limit=2,
        analysis_service=SimpleNamespace(embedding_service=Embeddings()),
    )
    assert results == [
        {
            'term': 'high similarity',
            'frequency': 10,
            'similarity': 0.913,
            'source': 'embedding_similarity',
        },
        {
            'term': 'low similarity',
            'frequency': 9,
            'similarity': 0.321,
            'source': 'embedding_similarity',
        },
    ]


def test_adjust_fuzziness_creates_audit_record_for_owner(
    db_session, test_user
):
    from app.models.term import FuzzinessAdjustment
    from app.services.term_api_service import TermApiService

    term, version = _term_with_version(
        db_session,
        test_user,
        'adjust',
        fuzziness_score=Decimal('0.400'),
    )
    adjustment = TermApiService.adjust_fuzziness(
        term.id,
        version.id,
        '0.725',
        '  Reviewed against historical evidence. ',
        test_user.id,
    )

    assert version.fuzziness_score == Decimal('0.725')
    assert adjustment.original_score == Decimal('0.400')
    assert adjustment.adjusted_score == Decimal('0.725')
    assert adjustment.adjustment_reason == 'Reviewed against historical evidence.'
    assert adjustment.adjusted_by == test_user.id
    assert db_session.get(FuzzinessAdjustment, adjustment.id) is adjustment


def test_adjust_fuzziness_allows_admin_and_rejects_stranger(
    db_session, test_user, admin_user
):
    from app.services.base_service import PermissionError
    from app.services.term_api_service import TermApiService

    term, version = _term_with_version(db_session, test_user, 'permission')
    stranger = _user(db_session, 'stranger')
    with pytest.raises(PermissionError):
        TermApiService.adjust_fuzziness(
            term.id,
            version.id,
            0.5,
            'Unauthorized adjustment.',
            stranger.id,
        )
    adjustment = TermApiService.adjust_fuzziness(
        term.id,
        version.id,
        0.6,
        'Administrator review.',
        admin_user.id,
    )
    assert adjustment.adjusted_by == admin_user.id


@pytest.mark.parametrize('score', [None, -0.1, 1.1, 'NaN', 'Infinity'])
def test_adjust_fuzziness_validates_score(db_session, test_user, score):
    from app.services.base_service import ValidationError
    from app.services.term_api_service import TermApiService

    term, version = _term_with_version(
        db_session,
        test_user,
        f'invalid-score-{score}',
    )
    with pytest.raises(ValidationError, match='between 0 and 1'):
        TermApiService.adjust_fuzziness(
            term.id,
            version.id,
            score,
            'Reason',
            test_user.id,
        )


def test_term_version_pair_is_enforced_for_adjustment_and_calculation(
    db_session, test_user
):
    from app.services.base_service import ValidationError
    from app.services.term_api_service import TermApiService

    first_term, _ = _term_with_version(db_session, test_user, 'pair-first')
    _, second_version = _term_with_version(db_session, test_user, 'pair-second')
    with pytest.raises(ValidationError, match='Invalid version for this term'):
        TermApiService.adjust_fuzziness(
            first_term.id,
            second_version.id,
            0.5,
            'Wrong pair',
            test_user.id,
        )
    with pytest.raises(ValidationError, match='Invalid version for this term'):
        TermApiService.calculate_fuzziness(
            first_term.id,
            second_version.id,
            SimpleNamespace(calculate_fuzziness_score=lambda term, version: (0.5, 'low')),
        )


def test_calculate_fuzziness_uses_public_analysis_contract(
    db_session, test_user
):
    from app.services.term_api_service import TermApiService

    term, version = _term_with_version(db_session, test_user, 'calculate')
    calls = []

    class Analysis:
        semantic_tracker = object()

        @staticmethod
        def calculate_fuzziness_score(received_term, received_version):
            calls.append((received_term.id, received_version.id))
            return 0.6789, 'high'

    result = TermApiService.calculate_fuzziness(
        term.id,
        version.id,
        Analysis(),
    )
    assert result == {
        'success': True,
        'fuzziness_score': 0.679,
        'confidence_level': 'high',
        'method': 'shared_services',
    }
    assert calls == [(term.id, version.id)]


def test_calculate_fuzziness_reports_unavailable_analysis(db_session, test_user):
    from app.services.term_api_service import AnalysisUnavailableError, TermApiService

    term, version = _term_with_version(db_session, test_user, 'unavailable')
    with pytest.raises(AnalysisUnavailableError):
        TermApiService.calculate_fuzziness(term.id, version.id, None)


def test_term_get_routes_are_public_and_support_q_parameter(
    client, db_session, test_user, monkeypatch
):
    from app.routes.terms import api

    _anchor(db_session, 'public anchor', 2)
    term, _ = _term_with_version(db_session, test_user, 'public-search')
    monkeypatch.setattr(api, 'get_term_analysis_service', lambda: None)

    anchors = client.get('/terms/api/context-anchors?query=public')
    terms = client.get('/terms/api/terms/search?q=public-search')
    fallback = client.get(
        '/terms/api/discover-context-anchors?term_text=agency&limit=1'
    )

    assert anchors.status_code == 200
    assert anchors.get_json()[0]['term'] == 'public anchor'
    assert terms.status_code == 200
    assert terms.get_json()[0]['id'] == str(term.id)
    assert fallback.status_code == 200
    assert fallback.get_json()[0]['source'] == 'existing'


def test_adjust_fuzziness_route_persists_and_redirects(
    auth_client, db_session, test_user
):
    term, version = _term_with_version(db_session, test_user, 'route-adjust')
    response = auth_client.post(
        f'/terms/{term.id}/versions/{version.id}/adjust-fuzziness',
        data={
            'fuzziness_score': '0.625',
            'adjustment_reason': 'Route review',
        },
    )
    assert response.status_code == 302
    assert response.headers['Location'].endswith(f'/terms/{term.id}')
    assert version.fuzziness_score == Decimal('0.625')


def test_calculate_fuzziness_route_maps_pair_and_availability(
    auth_client, db_session, test_user, monkeypatch
):
    from app.routes.terms import api

    first_term, first_version = _term_with_version(
        db_session,
        test_user,
        'route-calculate-first',
        fuzziness_score=Decimal('0.550'),
    )
    _, second_version = _term_with_version(
        db_session,
        test_user,
        'route-calculate-second',
    )
    analysis = SimpleNamespace(
        semantic_tracker=None,
        calculate_fuzziness_score=lambda term, version: (0.55, 'medium'),
    )
    monkeypatch.setattr(api, 'get_term_analysis_service', lambda: analysis)
    success = auth_client.post('/terms/api/calculate-fuzziness', json={
        'term_id': str(first_term.id),
        'version_id': str(first_version.id),
    })
    mismatch = auth_client.post('/terms/api/calculate-fuzziness', json={
        'term_id': str(first_term.id),
        'version_id': str(second_version.id),
    })
    monkeypatch.setattr(api, 'get_term_analysis_service', lambda: None)
    unavailable = auth_client.post('/terms/api/calculate-fuzziness', json={
        'term_id': str(first_term.id),
        'version_id': str(first_version.id),
    })

    assert success.status_code == 200
    assert success.get_json()['method'] == 'heuristic'
    assert mismatch.status_code == 400
    assert unavailable.status_code == 503


def test_term_post_apis_require_authentication(
    app, db_session, test_user
):
    term, version = _term_with_version(db_session, test_user, 'authentication')
    client = app.test_client()
    adjustment = client.post(
        f'/terms/{term.id}/versions/{version.id}/adjust-fuzziness',
        data={},
    )
    calculation = client.post('/terms/api/calculate-fuzziness', json={})
    assert adjustment.status_code == 401
    assert calculation.status_code == 401
