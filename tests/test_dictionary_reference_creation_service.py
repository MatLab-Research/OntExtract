"""Regression coverage for transactional dictionary-reference creation."""

from datetime import datetime
from types import SimpleNamespace

import pytest
from werkzeug.datastructures import MultiDict


class ProvenanceRecorder:
    def __init__(self, error=None):
        self.error = error
        self.calls = []

    def track_reference_creation(self, **kwargs):
        self.calls.append(kwargs)
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
        username=f'dictionary-create-{suffix}',
        email=f'dictionary-create-{suffix}@example.com',
        password='password',
        account_status='active',
    )
    db_session.add(user)
    db_session.commit()
    return user


def _service(provenance=None, logger=None):
    from app.services.dictionary_reference_creation_service import (
        DictionaryReferenceCreationService,
    )

    return DictionaryReferenceCreationService(
        provenance_service=provenance,
        workflow_logger=logger,
    )


def _client_for(app, user):
    client = app.test_client()
    with client.session_transaction() as session:
        session['_user_id'] = str(user.id)
        session['_fresh'] = True
    return client


def test_dictionary_reference_route_remains_canonical(app):
    assert app.view_functions['references.upload_dictionary'].__module__ == (
        'app.routes.references.upload.dictionary'
    )


def test_general_dictionary_normalizes_nuls_formats_content_and_tracks_provenance(
    db_session, test_user
):
    provenance = ProvenanceRecorder()
    result = _service(provenance).create(MultiDict({
        'title': '  agency\x00  ',
        'content': '  The capacity to act.\x00  ',
        'reference_subtype': 'dictionary_general',
        'journal': ' Example Dictionary\x00 ',
        'context': ' philosophy\x00 ',
        'synonyms': ' action, capacity\x00 ',
        'url': ' https://example.test/agency\x00 ',
        'citation': ' Example citation.\x00 ',
    }), test_user.id)

    document = result.document
    assert document.title == 'agency'
    assert document.reference_subtype == 'dictionary_general'
    assert document.content == (
        'Term: agency\n\n'
        'Source: Example Dictionary\n\n'
        'Context/Domain: philosophy\n\n'
        'Definition:\nThe capacity to act.\n'
        '\nSynonyms: action, capacity\n'
    )
    assert document.source_metadata == {
        'journal': 'Example Dictionary',
        'context': 'philosophy',
        'synonyms': 'action, capacity',
        'url': 'https://example.test/agency',
        'citation': 'Example citation.',
    }
    assert document.word_count == len(document.content.split())
    assert document.character_count == len(document.content)
    assert len(provenance.calls) == 1
    assert provenance.calls[0]['document'] is document
    assert provenance.calls[0]['user'] is test_user
    assert provenance.calls[0]['source'] == 'Example Dictionary'
    assert provenance.calls[0]['experiment'] is None


def test_oed_keeps_full_content_and_normalizes_metadata(db_session, test_user):
    raw_content = 'Full OED entry\nwith all supplied sections.\x00'
    result = _service().create(MultiDict({
        'title': ' agency ',
        'content': raw_content,
        'reference_subtype': 'dictionary_oed',
        'pronunciation': ' ˈeɪdʒənsi\x00 ',
        'etymology': ' Latin source\x00 ',
        'usage_notes': ' Historical usage ',
        'examples': ' An example. ',
        'first_use': ' 1600 ',
        'edition': ' Third ',
        'url': ' https://oed.example/agency ',
        'citation': ' OED citation ',
        'pdf_link': ' https://files.example/agency.pdf ',
    }), test_user.id)

    document = result.document
    assert document.content == 'Full OED entry\nwith all supplied sections.'
    assert document.reference_subtype == 'dictionary_oed'
    assert document.source_metadata == {
        'pronunciation': 'ˈeɪdʒənsi',
        'etymology': 'Latin source',
        'usage_notes': 'Historical usage',
        'examples': 'An example.',
        'first_use': '1600',
        'edition': 'Third',
        'url': 'https://oed.example/agency',
        'citation': 'OED citation',
        'pdf_link': 'https://files.example/agency.pdf',
        'journal': 'Oxford English Dictionary',
    }


@pytest.mark.parametrize(
    ('subtype', 'expected_source'),
    [
        ('dictionary_mw', 'MW'),
        ('thesaurus_mw', 'MW'),
        ('other', 'manual'),
    ],
)
def test_confirmed_non_oed_subtypes_remain_supported(
    db_session, test_user, subtype, expected_source
):
    provenance = ProvenanceRecorder()
    result = _service(provenance).create(MultiDict({
        'title': f'{subtype} title',
        'content': 'Stored reference content',
        'reference_subtype': subtype,
    }), test_user.id)
    assert result.document.reference_subtype == subtype
    assert provenance.calls[0]['source'] == expected_source


@pytest.mark.parametrize(
    ('form', 'message'),
    [
        ({'content': 'definition'}, 'Term is required'),
        ({'title': 'agency'}, 'Definition is required'),
        (
            {
                'title': 'agency',
                'content': 'definition',
                'reference_subtype': 'unsupported',
            },
            'Unsupported reference subtype',
        ),
    ],
)
def test_validation_occurs_before_writes(
    db_session, test_user, form, message
):
    from app.models.document import Document
    from app.services.base_service import ValidationError

    before = Document.query.count()
    with pytest.raises(ValidationError, match=message):
        _service().create(MultiDict(form), test_user.id)
    assert Document.query.count() == before


def test_input_lengths_are_bounded(db_session, test_user):
    result = _service().create(MultiDict({
        'title': 'x' * 250,
        'content': 'd' * 1_000_100,
        'reference_subtype': 'dictionary_general',
        'journal': 'j' * 700,
        'citation': 'c' * 11_000,
    }), test_user.id)
    document = result.document
    assert len(document.title) == 200
    assert document.content.count('d') == 1_000_000
    assert len(document.source_metadata['journal']) == 500
    assert len(document.source_metadata['citation']) == 10_000


def test_owner_link_is_atomic_and_records_include_flag(
    db_session, test_user, temporal_experiment
):
    from app.models.experiment import experiment_references

    provenance = ProvenanceRecorder()
    result = _service(provenance).create(MultiDict({
        'title': 'Linked dictionary entry',
        'content': 'A linked definition.',
        'reference_subtype': 'dictionary_general',
        'experiment_id': str(temporal_experiment.id),
        'include_in_analysis': 'true',
    }), test_user.id)
    row = db_session.execute(
        experiment_references.select().where(
            experiment_references.c.reference_id == result.document.id
        )
    ).mappings().one()
    assert row['experiment_id'] == temporal_experiment.id
    assert row['include_in_analysis'] is True
    assert result.experiment is temporal_experiment
    assert provenance.calls[0]['experiment'] is temporal_experiment


def test_admin_can_link_and_foreign_user_is_rejected_before_creation(
    db_session, test_user, admin_user, temporal_experiment
):
    from app.models.document import Document
    from app.services.base_service import PermissionError

    stranger = _user(db_session, 'stranger')
    form = MultiDict({
        'title': 'Experiment reference',
        'content': 'Definition.',
        'experiment_id': str(temporal_experiment.id),
    })
    before = Document.query.count()
    with pytest.raises(PermissionError):
        _service().create(form, stranger.id)
    assert Document.query.count() == before

    result = _service().create(form, admin_user.id)
    assert result.experiment is temporal_experiment
    assert result.document.user_id == admin_user.id


@pytest.mark.parametrize('experiment_id', ['not-an-id', '999999'])
def test_missing_experiment_creates_no_partial_reference(
    db_session, test_user, experiment_id
):
    from app.models.document import Document
    from app.services.base_service import NotFoundError

    before = Document.query.count()
    with pytest.raises(NotFoundError, match='Experiment not found'):
        _service().create(MultiDict({
            'title': 'Orphan prevented',
            'content': 'Definition.',
            'experiment_id': experiment_id,
        }), test_user.id)
    assert Document.query.count() == before


def test_link_failure_rolls_back_reference_and_keeps_outer_transaction(
    db_session, test_user, temporal_experiment, monkeypatch
):
    from app.models.document import Document
    from app.services.base_service import ServiceError
    from app.services.dictionary_reference_creation_service import (
        DictionaryReferenceCreationService,
    )

    before = Document.query.count()
    monkeypatch.setattr(
        DictionaryReferenceCreationService,
        '_link_experiment',
        staticmethod(lambda *args: (_ for _ in ()).throw(
            RuntimeError('forced link failure')
        )),
    )
    with pytest.raises(ServiceError, match='Failed to save dictionary reference'):
        _service().create(MultiDict({
            'title': 'Rolled back reference',
            'content': 'Definition.',
            'experiment_id': str(temporal_experiment.id),
        }), test_user.id)
    assert db_session.is_active
    assert Document.query.count() == before


def test_provenance_failure_does_not_undo_reference(db_session, test_user):
    from app.models.document import Document

    logger = LoggerRecorder()
    result = _service(
        ProvenanceRecorder(RuntimeError('PROV unavailable')),
        logger,
    ).create(MultiDict({
        'title': 'Durable reference',
        'content': 'Definition.',
    }), test_user.id)
    db_session.expire_all()
    assert db_session.get(Document, result.document.id) is not None
    assert logger.warnings == [
        'Failed to track dictionary reference provenance: PROV unavailable'
    ]


def test_dictionary_route_redirects_for_standalone_and_linked_entries(
    app, db_session, test_user, temporal_experiment, monkeypatch
):
    from app.routes.references.upload import dictionary

    monkeypatch.setattr(
        dictionary,
        'provenance_service',
        ProvenanceRecorder(),
    )
    client = _client_for(app, test_user)
    standalone = client.post('/references/upload_dictionary', data={
        'title': 'Standalone entry',
        'content': 'Definition.',
        'reference_subtype': 'dictionary_general',
    })
    linked = client.post('/references/upload_dictionary', data={
        'title': 'Linked entry',
        'content': 'Definition.',
        'reference_subtype': 'dictionary_oed',
        'experiment_id': str(temporal_experiment.id),
    })
    assert standalone.status_code == 302
    assert '/references/' in standalone.headers['Location']
    assert linked.status_code == 302
    assert linked.headers['Location'].endswith(
        f'/experiments/{temporal_experiment.id}'
    )


def test_dictionary_route_maps_validation_permission_and_service_errors(
    app, db_session, test_user, monkeypatch
):
    from app.routes.references.upload import dictionary
    from app.services.base_service import ServiceError

    client = _client_for(app, test_user)
    invalid = client.post('/references/upload_dictionary', data={})
    owner = _user(db_session, 'route-owner')
    from app.models.experiment import Experiment
    experiment = Experiment(
        name='Foreign dictionary experiment',
        experiment_type='temporal_evolution',
        user_id=owner.id,
        status='draft',
    )
    db_session.add(experiment)
    db_session.commit()
    forbidden = client.post('/references/upload_dictionary', data={
        'title': 'Foreign link',
        'content': 'Definition.',
        'experiment_id': str(experiment.id),
    })
    monkeypatch.setattr(
        dictionary,
        '_service',
        lambda: SimpleNamespace(
            create=lambda *args: (_ for _ in ()).throw(
                ServiceError('secret database details')
            )
        ),
    )
    failure = client.post('/references/upload_dictionary', data={
        'title': 'Failure',
        'content': 'Definition.',
    }, follow_redirects=True)
    assert invalid.status_code == 302
    assert forbidden.status_code == 302
    assert failure.status_code == 200
    assert b'Failed to save dictionary reference' in failure.data
    assert b'secret database details' not in failure.data


def test_dictionary_route_requires_authentication(app):
    response = app.test_client().post('/references/upload_dictionary', data={
        'title': 'Anonymous',
        'content': 'Definition.',
    })
    assert response.status_code == 401


@pytest.mark.parametrize(
    ('source', 'subtype', 'publisher', 'dictionary_name'),
    [
        (
            'MW',
            'dictionary_mw',
            'Merriam-Webster, Incorporated',
            'Merriam-Webster Dictionary',
        ),
        (
            'OED',
            'dictionary_oed',
            'Oxford University Press',
            'Oxford English Dictionary',
        ),
    ],
)
def test_quick_reference_preserves_raw_definition_and_source_metadata(
    db_session,
    test_user,
    source,
    subtype,
    publisher,
    dictionary_name,
):
    from app.services.dictionary_reference_creation_service import (
        DictionaryReferenceCreationService,
    )

    now = datetime(2026, 7, 10, 15, 30, 0)
    provenance = ProvenanceRecorder()
    service = DictionaryReferenceCreationService(
        provenance_service=provenance,
        clock=lambda: now,
    )
    result = service.create_quick({
        'title': '  agency\x00  ',
        'content': '  The capacity to act.\x00  ',
        'source': source.lower(),
        'source_type': 'dictionary',
        'term': ' agency ',
        'entry_url': ' https://example.test/agency ',
    }, test_user.id)

    document = result.document
    assert document.title == 'agency'
    assert document.content == 'The capacity to act.'
    assert document.reference_subtype == subtype
    assert document.publisher == publisher
    assert document.access_date.isoformat() == '2026-07-10'
    assert document.created_at == now
    assert document.source_metadata == {
        'source_type': 'dictionary',
        'term': 'agency',
        'entry_url': 'https://example.test/agency',
        'access_date': '2026-07-10',
        'publisher': publisher,
        'publisher_location': (
            'Springfield, MA' if source == 'MW' else 'Oxford, UK'
        ),
        'dictionary_name': dictionary_name,
        'citation': (
            f'"agency." {dictionary_name}, {publisher}. '
            'Accessed 10 Jul 2026.'
        ),
    }
    assert document.citation == document.source_metadata['citation']
    assert provenance.calls[0]['source'] == source
    assert provenance.calls[0]['document'] is document


def test_quick_reference_links_atomically_for_owner_and_admin(
    db_session, test_user, admin_user, temporal_experiment
):
    from app.models.experiment import experiment_references

    payload = {
        'title': 'Linked quick reference',
        'content': 'Definition.',
        'source': 'MW',
        'experiment_id': temporal_experiment.id,
        'include_in_analysis': True,
    }
    owner_result = _service().create_quick(payload, test_user.id)
    admin_result = _service().create_quick(payload, admin_user.id)
    rows = db_session.execute(
        experiment_references.select().where(
            experiment_references.c.reference_id.in_([
                owner_result.document.id,
                admin_result.document.id,
            ])
        )
    ).mappings().all()
    assert {row['experiment_id'] for row in rows} == {temporal_experiment.id}
    assert all(row['include_in_analysis'] is True for row in rows)
    assert owner_result.document.user_id == test_user.id
    assert admin_result.document.user_id == admin_user.id


def test_quick_reference_rejects_foreign_or_missing_experiment_before_write(
    db_session, test_user, temporal_experiment
):
    from app.models.document import Document
    from app.services.base_service import NotFoundError, PermissionError

    stranger = _user(db_session, 'quick-stranger')
    baseline = Document.query.count()
    payload = {
        'title': 'Rejected quick reference',
        'content': 'Definition.',
        'source': 'OED',
        'experiment_id': temporal_experiment.id,
    }
    with pytest.raises(PermissionError):
        _service().create_quick(payload, stranger.id)
    with pytest.raises(NotFoundError):
        _service().create_quick(
            {**payload, 'experiment_id': 999999},
            test_user.id,
        )
    assert Document.query.count() == baseline


@pytest.mark.parametrize(
    ('payload', 'message'),
    [
        (None, 'Invalid JSON payload'),
        ({}, 'Title and content are required'),
        (
            {'title': 'Title', 'content': 'Definition', 'source': 'other'},
            'Unsupported reference source',
        ),
    ],
)
def test_quick_reference_validates_payload_before_write(
    db_session, test_user, payload, message
):
    from app.models.document import Document
    from app.services.base_service import ValidationError

    baseline = Document.query.count()
    with pytest.raises(ValidationError, match=message):
        _service().create_quick(payload, test_user.id)
    assert Document.query.count() == baseline


def test_quick_reference_link_failure_rolls_back_document(
    db_session, test_user, temporal_experiment, monkeypatch
):
    from app.models.document import Document
    from app.services.base_service import ServiceError
    from app.services.dictionary_reference_creation_service import (
        DictionaryReferenceCreationService,
    )

    baseline = Document.query.count()
    monkeypatch.setattr(
        DictionaryReferenceCreationService,
        '_link_experiment',
        staticmethod(lambda *args: (_ for _ in ()).throw(
            RuntimeError('forced quick link failure')
        )),
    )
    with pytest.raises(ServiceError, match='Failed to save dictionary reference'):
        _service().create_quick({
            'title': 'Rolled back quick reference',
            'content': 'Definition.',
            'source': 'MW',
            'experiment_id': temporal_experiment.id,
        }, test_user.id)
    assert Document.query.count() == baseline
