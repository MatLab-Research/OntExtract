"""Regression coverage for semantic event configuration workflows."""

import json
from datetime import datetime
from types import SimpleNamespace
from uuid import UUID

import pytest


class StubOntology:
    @staticmethod
    def get_all_for_dropdown():
        return [{
            'value': 'broadening',
            'label': 'Broadening',
            'uri': 'http://example.org/Broadening',
            'definition': 'A meaning becomes more general.',
            'citation': 'Test citation',
            'example': 'A test example',
        }]


class ProvenanceRecorder:
    def __init__(self, error=None):
        self.error = error
        self.calls = []

    def track_semantic_event(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error


def _service(provenance=None, clock=None):
    from app.services.semantic_event_service import SemanticEventService

    return SemanticEventService(
        ontology_service=StubOntology(),
        provenance_service=provenance or ProvenanceRecorder(),
        clock=clock or (lambda: datetime(2026, 1, 1, 12, 0, 0)),
        id_factory=lambda: UUID('11111111-1111-1111-1111-111111111111'),
        workflow_logger=SimpleNamespace(warning=lambda message: None),
    )


def _temporal_experiment(db_session, user, suffix='events'):
    from app.models.experiment import Experiment

    experiment = Experiment(
        name=f'Temporal Events {suffix}',
        experiment_type='temporal_evolution',
        user_id=user.id,
        status='draft',
        configuration=json.dumps({'preserved': {'value': True}}),
    )
    db_session.add(experiment)
    db_session.commit()
    return experiment


def _user(db_session, suffix):
    from app.models.user import User

    user = User(
        username=f'event-user-{suffix}',
        email=f'event-user-{suffix}@example.com',
        password='password',
        account_status='active',
    )
    db_session.add(user)
    db_session.commit()
    return user


def _link(db_session, experiment, document):
    from app.models.experiment_document import ExperimentDocument

    db_session.add(ExperimentDocument(
        experiment_id=experiment.id,
        document_id=document.id,
    ))
    db_session.commit()


def test_semantic_event_routes_remain_canonical(app):
    expected = 'app.routes.experiments.temporal.events'
    assert app.view_functions['experiments.save_semantic_event'].__module__ == expected
    assert app.view_functions['experiments.remove_semantic_event'].__module__ == expected


def test_create_event_generates_id_enriches_and_scopes_evidence(
    db_session, test_user, sample_document
):
    experiment = _temporal_experiment(db_session, test_user, 'create')
    _link(db_session, experiment, sample_document)
    provenance = ProvenanceRecorder()

    result = _service(provenance).save(
        experiment.id,
        {
            'event_type': 'broadening',
            'from_period': '1990',
            'to_period': 2000,
            'description': '  The meaning broadened across domains.  ',
            'related_document_ids': [sample_document.id, sample_document.id],
        },
        test_user,
    )

    event = result['semantic_events'][0]
    assert event['id'] == '11111111-1111-1111-1111-111111111111'
    assert event['from_period'] == 1990
    assert event['to_period'] == 2000
    assert event['description'] == 'The meaning broadened across domains.'
    assert event['related_documents'] == [{
        'id': sample_document.id,
        'uuid': str(sample_document.uuid),
        'title': sample_document.title,
    }]
    assert event['type_label'] == 'Broadening'
    assert event['type_uri'] == 'http://example.org/Broadening'
    assert event['created_by'] == test_user.id
    assert event['created_at'] == '2026-01-01T12:00:00'
    assert event['modified_by'] is None
    stored = json.loads(experiment.configuration)
    assert stored['semantic_events'] == [event]
    assert stored['preserved'] == {'value': True}
    assert len(provenance.calls) == 1
    assert provenance.calls[0]['is_update'] is False


def test_create_accepts_legacy_and_reference_associations(
    db_session, test_user, sample_documents
):
    experiment = _temporal_experiment(db_session, test_user, 'compatibility')
    legacy, reference = sample_documents[:2]
    legacy.experiment_id = experiment.id
    reference.document_type = 'reference'
    experiment.references.append(reference)
    db_session.commit()

    event = _service().save(
        experiment.id,
        {
            'event_type': 'unknown_event',
            'from_period': 1900,
            'description': 'Compatibility evidence.',
            'related_document_ids': [legacy.id, reference.id],
        },
        test_user,
    )['semantic_events'][0]

    assert [item['id'] for item in event['related_documents']] == [
        legacy.id,
        reference.id,
    ]
    assert event['type_label'] == 'Unknown Event'
    assert event['type_uri'] is None


def test_update_preserves_creation_metadata_and_sets_modification(
    db_session, test_user
):
    experiment = _temporal_experiment(db_session, test_user, 'update')
    first_service = _service()
    created = first_service.save(
        experiment.id,
        {
            'event_type': 'broadening',
            'from_period': 1990,
            'description': 'Original description.',
        },
        test_user,
    )['semantic_events'][0]
    provenance = ProvenanceRecorder()
    updated = _service(
        provenance,
        clock=lambda: datetime(2026, 2, 1, 8, 30, 0),
    ).save(
        experiment.id,
        {
            'id': created['id'],
            'event_type': 'broadening',
            'from_period': 1995,
            'description': 'Updated description.',
        },
        test_user,
    )['semantic_events'][0]

    assert updated['id'] == created['id']
    assert updated['created_at'] == created['created_at']
    assert updated['created_by'] == created['created_by']
    assert updated['modified_by'] == test_user.id
    assert updated['modified_at'] == '2026-02-01T08:30:00'
    assert updated['description'] == 'Updated description.'
    assert provenance.calls[0]['is_update'] is True


def test_unknown_update_and_remove_return_not_found(db_session, test_user):
    from app.services.base_service import NotFoundError

    experiment = _temporal_experiment(db_session, test_user, 'unknown')
    with pytest.raises(NotFoundError, match='Semantic event missing not found'):
        _service().save(
            experiment.id,
            {
                'id': 'missing',
                'event_type': 'broadening',
                'from_period': 1990,
                'description': 'Unknown update.',
            },
            test_user,
        )
    with pytest.raises(NotFoundError, match='Semantic event missing not found'):
        _service().remove(experiment.id, 'missing', test_user)


def test_remove_persists_and_tracks_deletion(db_session, test_user):
    experiment = _temporal_experiment(db_session, test_user, 'remove')
    created = _service().save(
        experiment.id,
        {
            'event_type': 'broadening',
            'from_period': 1990,
            'description': 'Remove this event.',
        },
        test_user,
    )['semantic_events'][0]
    provenance = ProvenanceRecorder()

    result = _service(provenance).remove(
        experiment.id,
        created['id'],
        test_user,
    )

    assert result == {'success': True, 'semantic_events': []}
    assert json.loads(experiment.configuration)['semantic_events'] == []
    assert provenance.calls[0]['is_deletion'] is True
    assert provenance.calls[0]['event_metadata']['id'] == created['id']


def test_provenance_failure_does_not_undo_committed_event(
    db_session, test_user
):
    experiment = _temporal_experiment(db_session, test_user, 'provenance')
    service = _service(ProvenanceRecorder(RuntimeError('PROV unavailable')))

    result = service.save(
        experiment.id,
        {
            'event_type': 'broadening',
            'from_period': 1990,
            'description': 'Durable event.',
        },
        test_user,
    )

    db_session.refresh(experiment)
    assert result['success'] is True
    assert json.loads(experiment.configuration)['semantic_events'][0][
        'description'
    ] == 'Durable event.'


def test_event_permissions_and_type_are_enforced(
    db_session, test_user, admin_user, entity_extraction_experiment
):
    from app.services.base_service import PermissionError, ValidationError

    experiment = _temporal_experiment(db_session, test_user, 'permission')
    stranger = _user(db_session, 'stranger')
    payload = {
        'event_type': 'broadening',
        'from_period': 1990,
        'description': 'Permission test.',
    }
    with pytest.raises(PermissionError):
        _service().save(experiment.id, payload, stranger)
    admin_result = _service().save(experiment.id, payload, admin_user)
    assert admin_result['success'] is True
    with pytest.raises(ValidationError, match='only available for temporal'):
        _service().save(entity_extraction_experiment.id, payload, admin_user)


def test_related_documents_must_belong_to_experiment(
    db_session, test_user, sample_document
):
    from app.services.base_service import ValidationError

    experiment = _temporal_experiment(db_session, test_user, 'evidence')
    with pytest.raises(
        ValidationError,
        match='Related documents must belong to the experiment',
    ):
        _service().save(
            experiment.id,
            {
                'event_type': 'broadening',
                'from_period': 1990,
                'description': 'Invalid evidence.',
                'related_document_ids': [sample_document.id],
            },
            test_user,
        )


@pytest.mark.parametrize(
    ('payload', 'message'),
    [
        (None, 'JSON payload required'),
        ({}, 'Missing required fields'),
        (
            {
                'event_type': 'broadening',
                'from_period': 'invalid',
                'description': 'Description',
            },
            'from_period must be a valid year',
        ),
        (
            {
                'event_type': 'broadening',
                'from_period': 2000,
                'to_period': 1990,
                'description': 'Description',
            },
            'to_period must not precede from_period',
        ),
        (
            {
                'event_type': 'broadening',
                'from_period': 1990,
                'description': 'Description',
                'related_document_ids': 'not-a-list',
            },
            'related_document_ids must be a list',
        ),
    ],
)
def test_event_validation(db_session, test_user, payload, message):
    from app.services.base_service import ValidationError

    experiment = _temporal_experiment(db_session, test_user, f'validation-{len(message)}')
    with pytest.raises(ValidationError, match=message):
        _service().save(experiment.id, payload, test_user)


def test_semantic_event_route_contracts(
    auth_client, db_session, temporal_experiment
):
    create = auth_client.post(
        f'/experiments/{temporal_experiment.id}/save_semantic_event',
        json={
            'event_type': 'unrecorded_type',
            'from_period': 1990,
            'description': 'Created through the API.',
        },
    )
    assert create.status_code == 200
    event_id = create.get_json()['semantic_events'][0]['id']
    UUID(event_id)

    update = auth_client.post(
        f'/experiments/{temporal_experiment.id}/save_semantic_event',
        json={
            'id': event_id,
            'event_type': 'unrecorded_type',
            'from_period': 1995,
            'description': 'Updated through the API.',
        },
    )
    invalid = auth_client.post(
        f'/experiments/{temporal_experiment.id}/save_semantic_event',
        json={},
    )
    missing = auth_client.post(
        f'/experiments/{temporal_experiment.id}/remove_semantic_event',
        json={'event_id': 'missing'},
    )
    remove = auth_client.post(
        f'/experiments/{temporal_experiment.id}/remove_semantic_event',
        json={'event_id': event_id},
    )

    assert update.status_code == 200
    assert update.get_json()['semantic_events'][0]['from_period'] == 1995
    assert invalid.status_code == 400
    assert missing.status_code == 404
    assert remove.status_code == 200
    assert remove.get_json()['semantic_events'] == []


def test_semantic_event_routes_require_authentication(app, temporal_experiment):
    client = app.test_client()
    create = client.post(
        f'/experiments/{temporal_experiment.id}/save_semantic_event',
        json={},
    )
    remove = client.post(
        f'/experiments/{temporal_experiment.id}/remove_semantic_event',
        json={},
    )
    assert create.status_code == 401
    assert remove.status_code == 401


def test_template_uses_registered_removal_route_and_server_ids():
    from pathlib import Path

    template = (
        Path(__file__).resolve().parents[1]
        / 'app/templates/experiments/temporal_term_manager.html'
    ).read_text()
    assert 'remove_semantic_event/${' not in template
    assert "method: 'DELETE'" not in template
    assert 'eventData.id = eventId' in template
    assert 'eventData.id = editId' in template
    assert 'id: eventId || Date.now()' not in template
    assert 'const eventId = editId || `event_${Date.now()}`' not in template
