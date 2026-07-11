"""Regression coverage for transactional OED reference creation."""

from types import SimpleNamespace

import pytest


class FakeOEDService:
    def __init__(self, entries=None):
        self.entries = entries or {}
        self.calls = []

    def get_word(self, entry_id):
        self.calls.append(entry_id)
        value = self.entries.get(entry_id)
        if isinstance(value, Exception):
            raise value
        if value is None:
            return {'success': False, 'error': 'Entry not found'}
        return {'success': True, 'data': value}


class ProvenanceRecorder:
    def __init__(self, error=None):
        self.error = error
        self.calls = []

    def track_reference_creation(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error


def _payload(headword='agency'):
    return {
        'headword': headword,
        'part_of_speech': 'noun',
        'senses': [{
            'id': 'sense-1',
            'label': 'capacity',
            'definition': (
                'The capacity of an actor to initiate action independently '
                'within a social or computational environment and pursue '
                'goals under changing constraints with additional words that '
                'must not be retained in the stored minimal excerpt.'
            ),
            'subsenses': [{
                'oid': 'sense-2',
                'label': 'organization',
                'definition': ['An organization acting on behalf of another.'],
            }],
        }],
        'extracted_senses': [{
            'sense_id': 'sense-2',
            'label': 'duplicate ignored',
            'definition': 'Duplicate definition.',
        }, {
            'sense_id': 'sense-3',
            'label': 'linguistic',
            'definition': 'A grammatical source of action.',
        }],
    }


def _service(oed, provenance=None, logger=None):
    from app.services.oed_reference_creation_service import (
        OEDReferenceCreationService,
    )

    return OEDReferenceCreationService(
        oed,
        provenance_service=provenance,
        workflow_logger=logger or SimpleNamespace(warning=lambda message: None),
        api_base='https://api.example.test/oed',
    )


def _user(db_session, suffix):
    from app.models.user import User

    user = User(
        username=f'oed-create-{suffix}',
        email=f'oed-create-{suffix}@example.com',
        password='password',
        account_status='active',
    )
    db_session.add(user)
    db_session.commit()
    return user


def test_oed_creation_routes_remain_canonical(app):
    expected = 'app.routes.references.oed.creation'
    assert app.view_functions['references.add_oed_reference'].__module__ == expected
    assert (
        app.view_functions['references.add_oed_references_batch'].__module__
        == expected
    )


def test_build_unsaved_flattens_senses_and_stores_minimal_metadata(test_user):
    oed = FakeOEDService({'agency_nn01': _payload()})
    document = _service(oed).build_unsaved(
        '  agency_nn01  ',
        test_user.id,
        selected_sense_ids=['sense-1', 'sense-2'],
        title_override='  OED Agency  ',
    )

    assert document.id is None
    assert document.title == 'OED Agency'
    assert document.document_type == 'reference'
    assert document.reference_subtype == 'dictionary_oed'
    assert document.content == (
        'OED entry: agency_nn01\n'
        'Headword: agency\n'
        'Part of speech: noun\n'
        'Selected senses: sense-1, sense-2'
    )
    selected = document.source_metadata['selected_senses']
    assert [sense['sense_id'] for sense in selected] == ['sense-1', 'sense-2']
    assert len(selected[0]['definition'].split()) == 20
    assert selected[1] == {
        'sense_id': 'sense-2',
        'label': 'organization',
        'definition': 'An organization acting on behalf of another.',
    }
    assert document.source_metadata['oed_api_word_url'] == (
        'https://api.example.test/oed/word/agency_nn01/'
    )
    assert document.source_metadata['oed_web_search_url'].endswith('?q=agency')


def test_create_one_persists_links_and_tracks_provenance(
    db_session, test_user, temporal_experiment
):
    from app.models.experiment import experiment_references

    provenance = ProvenanceRecorder()
    result = _service(
        FakeOEDService({'agency_nn01': _payload()}),
        provenance,
    ).create_one(
        'agency_nn01',
        test_user,
        experiment_id=temporal_experiment.id,
        include_in_analysis=True,
    )

    assert result.document.id is not None
    assert result.experiment is temporal_experiment
    row = db_session.execute(
        experiment_references.select().where(
            experiment_references.c.reference_id == result.document.id
        )
    ).mappings().one()
    assert row['experiment_id'] == temporal_experiment.id
    assert row['include_in_analysis'] is True
    assert len(provenance.calls) == 1
    assert provenance.calls[0]['source'] == 'OED'
    assert provenance.calls[0]['experiment'] is temporal_experiment


def test_admin_can_link_and_non_owner_is_rejected_before_lookup(
    db_session, test_user, admin_user, temporal_experiment
):
    from app.services.base_service import PermissionError

    stranger = _user(db_session, 'stranger')
    rejected_oed = FakeOEDService({'agency_nn01': _payload()})
    with pytest.raises(PermissionError):
        _service(rejected_oed).create_one(
            'agency_nn01',
            stranger,
            experiment_id=temporal_experiment.id,
        )
    assert rejected_oed.calls == []

    result = _service(
        FakeOEDService({'agency_nn01': _payload()})
    ).create_one(
        'agency_nn01',
        admin_user,
        experiment_id=temporal_experiment.id,
    )
    assert result.experiment is temporal_experiment


def test_missing_experiment_creates_no_partial_reference(
    db_session, test_user
):
    from app.models.document import Document
    from app.services.base_service import NotFoundError

    oed = FakeOEDService({'agency_nn01': _payload()})
    before = Document.query.count()
    with pytest.raises(NotFoundError, match='Experiment not found'):
        _service(oed).create_one(
            'agency_nn01',
            test_user,
            experiment_id=999999,
        )
    assert oed.calls == []
    assert Document.query.count() == before


def test_batch_deduplicates_and_reports_partial_lookup_failures(
    db_session, test_user
):
    from app.models.document import Document

    oed = FakeOEDService({
        'agency_nn01': _payload('agency'),
        'agent_nn01': _payload('agent'),
    })
    result = _service(oed).create_batch(
        [' agency_nn01 ', 'missing_nn01', 'agency_nn01', '', 'agent_nn01'],
        test_user,
    )

    assert oed.calls == ['agency_nn01', 'missing_nn01', 'agent_nn01']
    assert [document.title for document in result.documents] == [
        'OED: agency',
        'OED: agent',
    ]
    assert result.errors == ['missing_nn01: Entry not found']
    assert Document.query.filter_by(reference_subtype='dictionary_oed').count() == 2


def test_provenance_failure_does_not_undo_reference(
    db_session, test_user
):
    from app.models.document import Document

    result = _service(
        FakeOEDService({'agency_nn01': _payload()}),
        ProvenanceRecorder(RuntimeError('PROV unavailable')),
    ).create_one('agency_nn01', test_user)
    db_session.expire_all()
    assert db_session.get(Document, result.document.id) is not None


def test_builder_compatibility_shim_returns_error_tuple(
    test_user, monkeypatch
):
    from app.routes.references.oed import builder

    monkeypatch.setattr(
        builder,
        'OEDService',
        lambda: FakeOEDService({'agency_nn01': _payload()}),
    )
    document, error = builder._build_oed_reference(
        'agency_nn01',
        test_user.id,
        selected_sense_ids=['sense-3'],
    )
    missing, missing_error = builder._build_oed_reference(
        'missing_nn01',
        test_user.id,
    )
    assert error is None
    assert document.source_metadata['selected_senses'][0]['sense_id'] == 'sense-3'
    assert missing is None
    assert missing_error == 'Entry not found'


def test_single_route_creates_reference_and_preserves_redirect(
    auth_client, test_user, monkeypatch
):
    from app.models.document import Document
    from app.routes.references.oed import creation

    monkeypatch.setattr(
        creation,
        'OEDService',
        lambda: FakeOEDService({'agency_nn01': _payload()}),
    )
    monkeypatch.setattr(
        creation,
        'ProvenanceService',
        ProvenanceRecorder(),
    )
    response = auth_client.post('/references/oed/add', data={
        'entry_id': 'agency_nn01',
        'sense_id': 'sense-1',
        'title': 'OED Route Agency',
    })
    document = Document.query.filter_by(title='OED Route Agency').one()
    assert response.status_code == 302
    assert response.headers['Location'].endswith(f'/references/{document.id}')


def test_batch_route_deduplicates_and_links_to_experiment(
    auth_client, db_session, test_user, temporal_experiment, monkeypatch
):
    from app.models.experiment import experiment_references
    from app.routes.references.oed import creation

    monkeypatch.setattr(
        creation,
        'OEDService',
        lambda: FakeOEDService({
            'agency_nn01': _payload('agency'),
            'agent_nn01': _payload('agent'),
        }),
    )
    monkeypatch.setattr(
        creation,
        'ProvenanceService',
        ProvenanceRecorder(),
    )
    response = auth_client.post('/references/oed/add_batch', data={
        'entry_id': ['agency_nn01', 'agency_nn01', 'agent_nn01'],
        'experiment_id': str(temporal_experiment.id),
        'include_in_analysis': 'true',
    })
    rows = db_session.execute(
        experiment_references.select().where(
            experiment_references.c.experiment_id == temporal_experiment.id
        )
    ).mappings().all()
    assert response.status_code == 302
    assert response.headers['Location'].endswith(
        f'/experiments/{temporal_experiment.id}'
    )
    assert len(rows) == 2
    assert all(row['include_in_analysis'] for row in rows)


def test_oed_creation_routes_require_authentication(app):
    client = app.test_client()
    assert client.post('/references/oed/add', data={}).status_code == 401
    assert client.post('/references/oed/add_batch', data={}).status_code == 401
