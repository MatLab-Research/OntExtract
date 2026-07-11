"""Regression coverage for authorized term-analysis persistence workflows."""

from types import SimpleNamespace

import pytest


def _user(db_session, suffix):
    from app.models.user import User

    user = User(
        username=f'term-analysis-{suffix}',
        email=f'term-analysis-{suffix}@example.com',
        password='password',
        account_status='active',
    )
    db_session.add(user)
    db_session.commit()
    return user


def _term(db_session, user, suffix, shared=False, with_version=True):
    from app.models.term import Term, TermVersion

    term = Term(
        term_text=f'analysis-term-{suffix}',
        status='active',
        created_by=None if shared else user.id,
    )
    db_session.add(term)
    db_session.flush()
    version = None
    if with_version:
        version = TermVersion(
            term_id=term.id,
            temporal_period='2000-2009',
            temporal_start_year=2000,
            temporal_end_year=2009,
            meaning_description='A meaning for analysis.',
            confidence_level='low',
            context_anchor=['existing'],
            version_number=1,
            is_current=True,
            created_by=user.id,
        )
        db_session.add(version)
    db_session.commit()
    return term, version


def _version(db_session, term, user, suffix, year, current=False):
    from app.models.term import TermVersion

    version = TermVersion(
        term_id=term.id,
        temporal_period=f'{year}-{year + 9}',
        temporal_start_year=year,
        temporal_end_year=year + 9,
        meaning_description=f'Meaning {suffix}.',
        confidence_level='medium',
        context_anchor=[suffix],
        version_number=year,
        is_current=current,
        created_by=user.id,
    )
    db_session.add(version)
    db_session.commit()
    return version


class AnalysisRecorder:
    def __init__(self, result=None, error=None, drift=None):
        self.result = result or SimpleNamespace(
            fuzziness_score=0.625,
            confidence_level='high',
            context_anchors=[
                ' existing ',
                'agency',
                'actor',
                'responsibility',
                'action',
                'capacity',
                'ignored-sixth-new-anchor',
            ],
            embeddings=[0.1, 0.2],
            temporal_contexts=[{'year': 2000}],
        )
        self.error = error
        self.drift = drift or DriftResult()
        self.analysis_calls = []
        self.drift_calls = []

    def analyze_term(self, term, corpus_texts):
        self.analysis_calls.append((term.id, corpus_texts))
        if self.error:
            raise self.error
        return self.result

    def detect_semantic_drift(self, term, baseline, comparison):
        self.drift_calls.append((term.id, baseline.id, comparison.id))
        if self.error:
            raise self.error
        return self.drift

    @staticmethod
    def create_semantic_drift_activity(term, baseline, comparison, drift):
        from app.models.semantic_drift import SemanticDriftActivity

        return SemanticDriftActivity(
            activity_type='semantic_drift_detection',
            start_period=baseline.temporal_period,
            end_period=comparison.temporal_period,
            used_entity=baseline.id,
            generated_entity=comparison.id,
            drift_metrics=drift.to_dict(),
            detection_algorithm='test-algorithm',
            drift_detected=True,
            drift_magnitude=drift.drift_score,
            drift_type='gradual',
            evidence_summary='Test drift evidence.',
            activity_status='completed',
        )


class DriftResult:
    drift_score = 0.4
    meaning_changes = ['changed']
    emergent_contexts = ['new']
    lost_contexts = ['old']

    def to_dict(self):
        return {
            'drift_score': self.drift_score,
            'meaning_changes': self.meaning_changes,
            'emergent_contexts': self.emergent_contexts,
            'lost_contexts': self.lost_contexts,
        }


def _workflow(analysis=None):
    from app.services.term_analysis_workflow_service import (
        TermAnalysisWorkflowService,
    )

    return TermAnalysisWorkflowService(analysis or AnalysisRecorder())


def _client_for(app, user):
    client = app.test_client()
    with client.session_transaction() as session:
        session['_user_id'] = str(user.id)
        session['_fresh'] = True
    return client


def test_term_analysis_routes_remain_canonical(app):
    expected = 'app.routes.terms.analysis'
    assert app.view_functions['terms.analyze_term'].__module__ == expected
    assert app.view_functions['terms.detect_semantic_drift'].__module__ == expected


def test_owner_analysis_normalizes_input_and_persists_results(
    db_session, test_user
):
    from app.models.context_anchor import ContextAnchor

    term, version = _term(db_session, test_user, 'owner')
    recorder = AnalysisRecorder()
    result = _workflow(recorder).analyze(
        term.id,
        ['  First corpus  ', '', 'Second corpus'],
        test_user.id,
    )

    db_session.refresh(version)
    assert recorder.analysis_calls == [(
        term.id,
        ['First corpus', 'Second corpus'],
    )]
    assert float(version.fuzziness_score) == 0.625
    assert version.confidence_level == 'high'
    assert version.context_anchor == [
        'existing',
        'agency',
        'actor',
        'responsibility',
        'action',
        'capacity',
    ]
    assert ContextAnchor.query.filter(
        ContextAnchor.anchor_term.in_([
            'agency',
            'actor',
            'responsibility',
            'action',
            'capacity',
        ])
    ).count() == 5
    assert result['analysis']['has_embeddings'] is True
    assert result['analysis']['temporal_contexts_count'] == 1


def test_analysis_preserves_existing_manual_fuzziness(db_session, test_user):
    from decimal import Decimal

    term, version = _term(db_session, test_user, 'manual-score')
    version.fuzziness_score = Decimal('0.800')
    db_session.commit()
    _workflow().analyze(term.id, [], test_user.id)
    db_session.refresh(version)
    assert version.fuzziness_score == Decimal('0.800')


@pytest.mark.parametrize('corpus', ['not-a-list', [1], {'text': 'bad'}])
def test_analysis_validates_corpus_before_algorithm(
    db_session, test_user, corpus
):
    from app.services.base_service import ValidationError

    term, _ = _term(db_session, test_user, f'corpus-{type(corpus).__name__}')
    recorder = AnalysisRecorder()
    with pytest.raises(ValidationError):
        _workflow(recorder).analyze(term.id, corpus, test_user.id)
    assert recorder.analysis_calls == []


def test_analysis_requires_current_version(db_session, test_user):
    from app.services.base_service import ValidationError

    term, _ = _term(
        db_session,
        test_user,
        'no-version',
        with_version=False,
    )
    with pytest.raises(ValidationError, match='no current version'):
        _workflow().analyze(term.id, [], test_user.id)


def test_foreign_and_shared_terms_are_read_only(
    db_session, test_user
):
    from app.services.base_service import PermissionError

    owner = _user(db_session, 'foreign-owner')
    foreign, _ = _term(db_session, owner, 'foreign')
    shared, _ = _term(db_session, owner, 'shared', shared=True)
    for term in (foreign, shared):
        with pytest.raises(PermissionError):
            _workflow().analyze(term.id, [], test_user.id)


def test_admin_can_analyze_owned_term(db_session, admin_user, test_user):
    term, version = _term(db_session, test_user, 'admin')
    _workflow().analyze(term.id, [], admin_user.id)
    db_session.refresh(version)
    assert float(version.fuzziness_score) == 0.625


def test_algorithm_failures_are_sanitized(db_session, test_user):
    from app.services.base_service import ServiceError

    term, _ = _term(db_session, test_user, 'algorithm-failure')
    with pytest.raises(ServiceError) as exc:
        _workflow(AnalysisRecorder(error=RuntimeError('secret model detail'))).analyze(
            term.id,
            [],
            test_user.id,
        )
    assert str(exc.value) == 'Term analysis failed'
    assert 'secret' not in str(exc.value)


def test_analysis_persistence_failure_rolls_back_savepoint(
    db_session, test_user, monkeypatch
):
    from app.models.context_anchor import ContextAnchor
    from app.models.term import TermVersion
    from app.services.base_service import ServiceError

    term, version = _term(db_session, test_user, 'rollback')
    baseline_anchors = ContextAnchor.query.count()
    monkeypatch.setattr(
        TermVersion,
        'add_context_anchor',
        lambda self, *args, **kwargs: (_ for _ in ()).throw(
            RuntimeError('forced persistence failure')
        ),
    )
    with pytest.raises(ServiceError, match='persist term analysis'):
        _workflow().analyze(term.id, [], test_user.id)
    db_session.refresh(version)
    assert version.fuzziness_score is None
    assert version.context_anchor == ['existing']
    assert ContextAnchor.query.count() == baseline_anchors


def test_drift_success_validates_pair_and_attributes_activity(
    db_session, test_user
):
    from app.models.semantic_drift import SemanticDriftActivity

    term, first = _term(db_session, test_user, 'drift')
    second = _version(db_session, term, test_user, 'second', 2010, current=True)
    recorder = AnalysisRecorder()
    result = _workflow(recorder).detect_drift(
        term.id,
        str(first.id),
        str(second.id),
        test_user.id,
    )
    activity = db_session.get(
        SemanticDriftActivity,
        result['activity_id'],
    )
    assert recorder.drift_calls == [(term.id, first.id, second.id)]
    assert activity.created_by == test_user.id
    assert activity.used_entity == first.id
    assert activity.generated_entity == second.id
    assert result['drift']['drift_score'] == 0.4


def test_drift_rejects_wrong_same_and_reversed_versions(
    db_session, test_user
):
    from app.services.base_service import ValidationError

    term, first = _term(db_session, test_user, 'drift-validation')
    second = _version(db_session, term, test_user, 'second', 2010)
    other, other_version = _term(db_session, test_user, 'other-drift')
    service = _workflow()
    with pytest.raises(ValidationError, match='Invalid version'):
        service.detect_drift(
            term.id,
            first.id,
            other_version.id,
            test_user.id,
        )
    with pytest.raises(ValidationError, match='different'):
        service.detect_drift(
            term.id,
            first.id,
            first.id,
            test_user.id,
        )
    with pytest.raises(ValidationError, match='precede'):
        service.detect_drift(
            term.id,
            second.id,
            first.id,
            test_user.id,
        )
    assert other.id != term.id


def test_drift_rejects_malformed_and_missing_versions(db_session, test_user):
    from app.services.base_service import NotFoundError

    term, version = _term(db_session, test_user, 'missing-version')
    for value in ('not-a-uuid', str(__import__('uuid').uuid4())):
        with pytest.raises(NotFoundError):
            _workflow().detect_drift(
                term.id,
                value,
                version.id,
                test_user.id,
            )


def test_unavailable_analysis_is_typed(db_session, test_user):
    from app.services.term_analysis_workflow_service import (
        AnalysisUnavailableError,
        TermAnalysisWorkflowService,
    )

    term, version = _term(db_session, test_user, 'unavailable')
    service = TermAnalysisWorkflowService(None)
    with pytest.raises(AnalysisUnavailableError):
        service.analyze(term.id, [], test_user.id)
    with pytest.raises(AnalysisUnavailableError):
        service.detect_drift(
            term.id,
            version.id,
            version.id,
            test_user.id,
        )


def test_analysis_route_success_validation_permission_and_failures(
    app, db_session, test_user, monkeypatch
):
    from app.routes.terms import analysis
    from app.services.base_service import ServiceError

    term, _ = _term(db_session, test_user, 'route-analysis')
    client = _client_for(app, test_user)
    fake = AnalysisRecorder()
    monkeypatch.setattr(analysis, 'get_term_analysis_service', lambda: fake)
    success = client.post(
        f'/terms/{term.id}/analyze',
        json={'corpus_texts': ['Example corpus']},
    )
    invalid = client.post(
        f'/terms/{term.id}/analyze',
        json={'corpus_texts': 'invalid'},
    )
    shared, _ = _term(db_session, test_user, 'route-shared', shared=True)
    forbidden = client.post(f'/terms/{shared.id}/analyze', json={})
    monkeypatch.setattr(
        analysis,
        '_workflow',
        lambda: SimpleNamespace(
            analyze=lambda *args: (_ for _ in ()).throw(
                ServiceError('secret algorithm error')
            )
        ),
    )
    failure = client.post(f'/terms/{term.id}/analyze', json={})

    assert success.status_code == 200
    assert success.get_json()['analysis']['fuzziness_score'] == 0.625
    assert invalid.status_code == 400
    assert forbidden.status_code == 403
    assert forbidden.get_json()['error'] == 'Permission denied'
    assert failure.status_code == 500
    assert failure.get_json()['error'] == 'Term analysis failed'
    assert 'secret' not in str(failure.get_json())


def test_drift_route_contracts(app, db_session, test_user, monkeypatch):
    from app.routes.terms import analysis

    term, first = _term(db_session, test_user, 'route-drift')
    second = _version(db_session, term, test_user, 'second', 2010)
    client = _client_for(app, test_user)
    monkeypatch.setattr(
        analysis,
        'get_term_analysis_service',
        lambda: AnalysisRecorder(),
    )
    missing = client.post(f'/terms/{term.id}/detect-drift', json={})
    success = client.post(f'/terms/{term.id}/detect-drift', json={
        'baseline_version_id': str(first.id),
        'comparison_version_id': str(second.id),
    })
    mismatch = client.post(f'/terms/{term.id}/detect-drift', json={
        'baseline_version_id': str(second.id),
        'comparison_version_id': str(first.id),
    })
    assert missing.status_code == 400
    assert success.status_code == 200
    assert success.get_json()['drift']['drift_score'] == 0.4
    assert mismatch.status_code == 400


def test_term_analysis_routes_require_authentication(app, db_session, test_user):
    term, version = _term(db_session, test_user, 'authentication')
    client = app.test_client()
    assert client.post(f'/terms/{term.id}/analyze', json={}).status_code == 401
    assert client.post(
        f'/terms/{term.id}/detect-drift',
        json={
            'baseline_version_id': str(version.id),
            'comparison_version_id': str(version.id),
        },
    ).status_code == 401


def test_form_analysis_preserves_redirect_contract(
    app, db_session, test_user, monkeypatch
):
    from app.routes.terms import analysis

    term, _ = _term(db_session, test_user, 'form')
    monkeypatch.setattr(
        analysis,
        'get_term_analysis_service',
        lambda: AnalysisRecorder(),
    )
    response = _client_for(app, test_user).post(f'/terms/{term.id}/analyze')
    assert response.status_code == 302
    assert response.headers['Location'].endswith(f'/terms/{term.id}')
