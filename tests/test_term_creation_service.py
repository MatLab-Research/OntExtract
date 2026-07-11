"""Regression coverage for atomic initial term creation."""

from datetime import datetime
from types import SimpleNamespace

import pytest


class ProvenanceRecorder:
    def __init__(self, error=None):
        self.error = error
        self.calls = []

    def track_term_creation(self, term, user):
        self.calls.append((term.id, user.id))
        if self.error:
            raise self.error


class LoggerRecorder:
    def __init__(self):
        self.warnings = []

    def warning(self, message, *args):
        self.warnings.append(message % args if args else message)


def _user(db_session, suffix):
    from app.models.user import User

    user = User(
        username=f'term-create-{suffix}',
        email=f'term-create-{suffix}@example.com',
        password='password',
        account_status='active',
    )
    db_session.add(user)
    db_session.commit()
    return user


def _document(db_session, user, title):
    from app.models.document import Document

    document = Document(
        title=title,
        content='Reference source content.',
        content_type='text',
        document_type='reference',
        status='completed',
        user_id=user.id,
    )
    db_session.add(document)
    db_session.commit()
    return document


def _data(**overrides):
    values = {
        'term_text': '  computational agency  ',
        'description': '  A computational concept.  ',
        'etymology': '  Latin source.  ',
        'notes': '  Research note.  ',
        'research_domain': '  Artificial Intelligence  ',
        'selection_rationale': '  Important for autonomous systems.  ',
        'historical_significance': '  Used in modern AI.  ',
        'temporal_period': '  2000-present  ',
        'temporal_start_year': 2000,
        'temporal_end_year': 2026,
        'meaning_description': (
            '  The capacity of a computational system to act toward goals.  '
        ),
        'corpus_source': '  Technical literature  ',
        'source_citation': '  Example citation.  ',
        'confidence_level': 'high',
        'fuzziness_score': 0.25,
        'context_anchor': ' autonomy, agents, autonomy, , systems ',
    }
    values.update(overrides)
    return values


def _service(provenance=None, logger=None, clock=None):
    from app.services.term_creation_service import TermCreationService

    return TermCreationService(
        provenance_service=provenance,
        workflow_logger=logger,
        clock=clock,
    )


def test_term_creation_route_remains_canonical(app):
    assert app.view_functions['terms.add_term'].__module__ == (
        'app.routes.terms.crud.creation'
    )


def test_create_builds_term_version_and_deduplicated_anchor_links(
    db_session, test_user
):
    from app.models.context_anchor import ContextAnchor
    from app.models.term import TermVersion, term_version_anchors

    now = datetime(2026, 7, 10, 16, 0, 0)
    provenance = ProvenanceRecorder()
    term = _service(provenance, clock=lambda: now).create(
        _data(),
        test_user.id,
    )
    version = TermVersion.query.filter_by(term_id=term.id).one()
    rows = db_session.execute(
        term_version_anchors.select().where(
            term_version_anchors.c.term_version_id == version.id
        )
    ).mappings().all()

    assert term.term_text == 'computational agency'
    assert term.description == 'A computational concept.'
    assert term.research_domain == 'Artificial Intelligence'
    assert term.created_by == test_user.id
    assert term.status == 'active'
    assert version.temporal_period == '2000-present'
    assert version.temporal_start_year == 2000
    assert version.temporal_end_year == 2026
    assert version.meaning_description == (
        'The capacity of a computational system to act toward goals.'
    )
    assert version.context_anchor == ['autonomy', 'agents', 'systems']
    assert float(version.fuzziness_score) == 0.25
    assert version.confidence_level == 'high'
    assert version.generated_at_time.replace(tzinfo=None) == now
    assert version.version_number == 1
    assert version.is_current is True
    assert ContextAnchor.query.count() == 3
    assert len(rows) == 3
    assert provenance.calls == [(term.id, test_user.id)]


def test_page_context_scopes_documents_and_orders_domains(
    db_session, test_user
):
    from app.models.term import Term
    from app.services.term_creation_service import TermCreationService

    stranger = _user(db_session, 'context-stranger')
    owned_b = _document(db_session, test_user, 'B source')
    owned_a = _document(db_session, test_user, 'A source')
    foreign = _document(db_session, stranger, 'Foreign source')
    db_session.add_all([
        Term(term_text='domain-z', research_domain='Zoology', created_by=stranger.id),
        Term(term_text='domain-a', research_domain='AI', created_by=test_user.id),
        Term(term_text='domain-empty', research_domain='', created_by=test_user.id),
    ])
    db_session.commit()

    context = TermCreationService.page_context(test_user.id)
    assert context['existing_domains'] == ['AI', 'Zoology']
    assert context['documents'] == [owned_a, owned_b]
    assert foreign not in context['documents']


def test_duplicate_policy_is_per_creator(db_session, test_user):
    from app.models.term import Term
    from app.services.term_creation_service import DuplicateTermError

    first = _service().create(_data(term_text='shared term'), test_user.id)
    with pytest.raises(DuplicateTermError, match='already exists'):
        _service().create(_data(term_text='shared term'), test_user.id)
    stranger = _user(db_session, 'duplicate-stranger')
    second = _service().create(_data(term_text='shared term'), stranger.id)
    assert first.id != second.id
    assert Term.query.filter_by(term_text='shared term').count() == 2


@pytest.mark.parametrize(
    ('overrides', 'message'),
    [
        ({'term_text': ''}, 'Term text is required'),
        ({'temporal_period': ''}, 'Temporal period is required'),
        ({'meaning_description': ''}, 'Meaning description is required'),
        ({'confidence_level': 'certain'}, 'Invalid confidence level'),
        ({'fuzziness_score': 'bad'}, 'Fuzziness score must be a number'),
        ({'fuzziness_score': 1.1}, 'Fuzziness score must be between'),
        ({'temporal_start_year': 'bad'}, 'Temporal year must be an integer'),
        ({'temporal_start_year': 900}, 'Temporal year must be between'),
        (
            {'temporal_start_year': 2020, 'temporal_end_year': 2010},
            'end year cannot precede',
        ),
    ],
)
def test_create_validates_before_writes(
    db_session, test_user, overrides, message
):
    from app.models.term import Term, TermVersion
    from app.services.base_service import ValidationError

    with pytest.raises(ValidationError, match=message):
        _service().create(_data(**overrides), test_user.id)
    assert Term.query.count() == 0
    assert TermVersion.query.count() == 0


def test_invalid_payload_or_actor_is_typed(test_user):
    from app.services.base_service import PermissionError, ValidationError

    with pytest.raises(ValidationError, match='Invalid term data'):
        _service().create(None, test_user.id)
    with pytest.raises(PermissionError):
        _service().create(_data(), 999999)


def test_anchor_failure_rolls_back_term_version_and_new_anchors(
    db_session, test_user, monkeypatch
):
    from app.models.context_anchor import ContextAnchor
    from app.models.term import Term, TermVersion
    from app.services.base_service import ServiceError

    original = TermVersion.add_context_anchor
    calls = []

    def fail_second(version, anchor, **kwargs):
        calls.append(anchor)
        if len(calls) == 2:
            raise RuntimeError('forced anchor failure')
        return original(version, anchor, **kwargs)

    monkeypatch.setattr(TermVersion, 'add_context_anchor', fail_second)
    with pytest.raises(ServiceError, match='Failed to create term'):
        _service().create(_data(), test_user.id)
    assert Term.query.count() == 0
    assert TermVersion.query.count() == 0
    assert ContextAnchor.query.count() == 0


def test_integrity_failure_without_duplicate_is_generic(
    test_user, monkeypatch
):
    from sqlalchemy.exc import IntegrityError

    from app.models.term import TermVersion
    from app.services.base_service import ServiceError

    monkeypatch.setattr(
        TermVersion,
        'add_context_anchor',
        lambda *args, **kwargs: (_ for _ in ()).throw(
            IntegrityError('statement', {}, RuntimeError('constraint failure'))
        ),
    )
    with pytest.raises(ServiceError, match='Failed to create term'):
        _service().create(_data(), test_user.id)


def test_provenance_failure_does_not_undo_term(db_session, test_user):
    from app.models.term import Term

    logger = LoggerRecorder()
    term = _service(
        ProvenanceRecorder(RuntimeError('PROV unavailable')),
        logger,
    ).create(_data(), test_user.id)
    db_session.expire_all()
    assert db_session.get(Term, term.id) is not None
    assert logger.warnings == [
        'Failed to track term creation provenance: PROV unavailable'
    ]


def test_form_data_extracts_creation_fields():
    from app.services.term_creation_service import TermCreationService

    form = SimpleNamespace(**{
        name: SimpleNamespace(data=f'value-{name}')
        for name in TermCreationService.FIELDS
    })
    data = TermCreationService.form_data(form)
    assert set(data) == set(TermCreationService.FIELDS)
    assert data['term_text'] == 'value-term_text'


def test_add_term_route_success_duplicate_and_page_context(
    auth_client, db_session, test_user, monkeypatch
):
    from app.models.term import Term, TermVersion
    from app.routes.terms.crud import creation

    monkeypatch.setattr(
        creation,
        'provenance_service',
        ProvenanceRecorder(),
    )
    first = auth_client.post('/terms/add', data={
        'term_text': 'route-created-term',
        'meaning_description': 'A sufficiently detailed meaning description.',
        'temporal_period': '2000-present',
        'temporal_start_year': '2000',
        'confidence_level': 'medium',
        'research_domain': 'Computing',
        'context_anchor': 'agency, systems',
    })
    duplicate = auth_client.post('/terms/add', data={
        'term_text': 'route-created-term',
        'meaning_description': 'A sufficiently detailed meaning description.',
        'temporal_period': '2000-present',
        'confidence_level': 'medium',
    }, follow_redirects=True)
    page = auth_client.get('/terms/add')
    term = Term.query.filter_by(
        term_text='route-created-term',
        created_by=test_user.id,
    ).one()
    assert first.status_code == 302
    assert first.headers['Location'].endswith(f'/terms/{term.id}')
    assert TermVersion.query.filter_by(term_id=term.id).count() == 1
    assert duplicate.status_code == 200
    assert b'already exists' in duplicate.data
    assert Term.query.filter_by(term_text='route-created-term').count() == 1
    assert page.status_code == 200
    assert b'Computing' in page.data


def test_add_term_route_shows_form_validation_without_writes(auth_client):
    from app.models.term import Term

    response = auth_client.post('/terms/add', data={
        'term_text': 'invalid-route-term',
        'meaning_description': 'short',
        'temporal_period': '',
        'confidence_level': 'medium',
    })
    assert response.status_code == 200
    assert b'Field must be between 10 and 2000 characters long' in response.data
    assert Term.query.filter_by(term_text='invalid-route-term').count() == 0


def test_add_term_route_hides_service_error(
    auth_client, monkeypatch
):
    from app.routes.terms.crud import creation
    from app.services.base_service import ServiceError

    monkeypatch.setattr(
        creation,
        '_service',
        lambda: SimpleNamespace(
            create=lambda *args: (_ for _ in ()).throw(
                ServiceError('secret database details')
            )
        ),
    )
    response = auth_client.post('/terms/add', data={
        'term_text': 'route-failure',
        'meaning_description': 'A sufficiently detailed meaning description.',
        'temporal_period': '2000-present',
        'confidence_level': 'medium',
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'An error occurred while creating the term' in response.data
    assert b'secret database details' not in response.data


def test_add_term_route_requires_authentication(app):
    assert app.test_client().get('/terms/add').status_code == 302
