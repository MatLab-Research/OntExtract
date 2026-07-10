"""Regression coverage for authorized document segmentation workflows."""

from types import SimpleNamespace

import pytest


class RunnerRecorder:
    def __init__(self):
        self.version_calls = []
        self.traditional_calls = []
        self.langextract_calls = []

    def version(self, document, experiment_id, actor, method, chunk_size, overlap, logger):
        self.version_calls.append({
            'document': document,
            'experiment_id': experiment_id,
            'actor': actor,
            'method': method,
            'chunk_size': chunk_size,
            'overlap': overlap,
            'logger': logger,
        })
        return document

    def traditional(self, version, document, actor, method, chunk_size, overlap):
        self.traditional_calls.append((
            version,
            document,
            actor,
            method,
            chunk_size,
            overlap,
        ))
        return {
            'job': SimpleNamespace(id=42),
            'segment_count': 3,
        }, 200

    def langextract(self, version, document, actor):
        self.langextract_calls.append((version, document, actor))
        return {'success': True, 'segments_created': 2}, 200


def _service(recorder=None):
    from app.services.document_segmentation_service import (
        DocumentSegmentationService,
    )

    recorder = recorder or RunnerRecorder()
    service = DocumentSegmentationService(
        recorder.version,
        recorder.traditional,
        recorder.langextract,
        workflow_logger=SimpleNamespace(info=lambda *args, **kwargs: None),
    )
    return service, recorder


def _user(db_session, suffix):
    from app.models.user import User

    user = User(
        username=f'segmentation-{suffix}',
        email=f'segmentation-{suffix}@example.com',
        password='password',
        account_status='active',
    )
    db_session.add(user)
    db_session.commit()
    return user


def _experiment(db_session, user, suffix):
    from app.models.experiment import Experiment

    experiment = Experiment(
        name=f'Segmentation {suffix}',
        experiment_type='temporal_evolution',
        user_id=user.id,
        status='draft',
    )
    db_session.add(experiment)
    db_session.commit()
    return experiment


def _link(db_session, experiment, document):
    from app.models.experiment_document import ExperimentDocument

    association = ExperimentDocument(
        experiment_id=experiment.id,
        document_id=document.id,
    )
    db_session.add(association)
    db_session.commit()
    return association


def test_segmentation_routes_remain_canonical(app):
    expected = 'app.routes.processing.segmentation.routes'
    assert app.view_functions['processing.segment_document'].__module__ == expected
    assert (
        app.view_functions['processing.delete_document_segments'].__module__
        == expected
    )


@pytest.mark.parametrize(
    ('data', 'message'),
    [
        ({'method': 'unsupported'}, 'Unsupported segmentation method'),
        ({'chunk_size': 'large'}, 'chunk_size must be an integer'),
        ({'chunk_size': 49}, 'chunk_size must be between 50 and 100000'),
        ({'chunk_size': 100, 'overlap': -1}, 'overlap must be non-negative'),
        ({'chunk_size': 100, 'overlap': 100}, 'overlap must be non-negative'),
        ({'experiment_id': 'invalid'}, 'experiment_id must be an integer'),
    ],
)
def test_segmentation_request_validation(data, message):
    from app.services.base_service import ValidationError
    from app.services.document_segmentation_service import (
        DocumentSegmentationService,
    )

    with pytest.raises(ValidationError, match=message):
        DocumentSegmentationService._validated_request(data)


def test_owner_segmentation_dispatches_traditional_runner(test_user, sample_document):
    service, recorder = _service()
    payload, status = service.segment(
        str(sample_document.uuid),
        {'method': 'sentence', 'chunk_size': 800, 'overlap': 25},
        test_user.id,
    )

    assert status == 200
    assert payload['success'] is True
    assert payload['job_id'] == 42
    assert payload['segments_created'] == 3
    assert payload['processing_version_id'] == sample_document.id
    assert payload['processing_version_uuid'] == str(sample_document.uuid)
    assert recorder.version_calls[0]['method'] == 'sentence'
    assert recorder.version_calls[0]['experiment_id'] is None
    assert recorder.traditional_calls[0][3:] == ('sentence', 800, 25)
    assert recorder.langextract_calls == []


def test_langextract_dispatch_preserves_runner_payload(test_user, sample_document):
    service, recorder = _service()
    payload, status = service.segment(
        str(sample_document.uuid),
        {'method': 'langextract'},
        test_user.id,
    )
    assert status == 200
    assert payload == {'success': True, 'segments_created': 2}
    assert len(recorder.langextract_calls) == 1
    assert recorder.traditional_calls == []


def test_non_owner_cannot_segment_before_version_creation(
    db_session, sample_document
):
    from app.services.base_service import PermissionError

    stranger = _user(db_session, 'stranger')
    service, recorder = _service()
    with pytest.raises(PermissionError):
        service.segment(
            str(sample_document.uuid),
            {'method': 'paragraph'},
            stranger.id,
        )
    assert recorder.version_calls == []


def test_admin_can_segment_another_users_document(admin_user, sample_document):
    service, recorder = _service()
    payload, status = service.segment(
        str(sample_document.uuid),
        {'method': 'paragraph'},
        admin_user.id,
    )
    assert status == 200
    assert payload['success'] is True
    assert recorder.version_calls[0]['actor'] is admin_user


def test_experiment_owner_can_segment_linked_document_owned_by_another_user(
    db_session, test_user, sample_document
):
    experiment_owner = _user(db_session, 'experiment-owner')
    experiment = _experiment(db_session, experiment_owner, 'owned')
    _link(db_session, experiment, sample_document)
    service, recorder = _service()

    payload, status = service.segment(
        str(sample_document.uuid),
        {'method': 'paragraph', 'experiment_id': experiment.id},
        experiment_owner.id,
    )
    assert status == 200
    assert payload['success'] is True
    assert recorder.version_calls[0]['experiment_id'] == experiment.id


def test_experiment_segmentation_requires_access_and_membership(
    db_session, test_user, sample_document
):
    from app.services.base_service import PermissionError, ValidationError

    owner = _user(db_session, 'unlinked-owner')
    stranger = _user(db_session, 'experiment-stranger')
    experiment = _experiment(db_session, owner, 'unlinked')
    service, recorder = _service()

    with pytest.raises(PermissionError):
        service.segment(
            str(sample_document.uuid),
            {'experiment_id': experiment.id},
            stranger.id,
        )
    with pytest.raises(ValidationError, match='not linked'):
        service.segment(
            str(sample_document.uuid),
            {'experiment_id': experiment.id},
            owner.id,
        )
    assert recorder.version_calls == []


def test_empty_document_and_missing_resources_are_typed_errors(
    db_session, test_user, sample_document
):
    from app.services.base_service import NotFoundError, ValidationError

    service, recorder = _service()
    with pytest.raises(NotFoundError, match='Document not found'):
        service.segment('00000000-0000-0000-0000-000000000000', {}, test_user.id)
    sample_document.content = ''
    db_session.commit()
    with pytest.raises(ValidationError, match='no content'):
        service.segment(str(sample_document.uuid), {}, test_user.id)
    assert recorder.version_calls == []


def test_delete_segments_requires_owner_and_records_audit_job(
    db_session, test_user, sample_document
):
    from app.models.processing_job import ProcessingJob
    from app.models.text_segment import TextSegment
    from app.services.base_service import PermissionError
    from app.services.document_segmentation_service import (
        DocumentSegmentationService,
    )

    stranger = _user(db_session, 'delete-stranger')
    db_session.add(TextSegment(
        document_id=sample_document.id,
        content='Segment to delete.',
        segment_number=1,
    ))
    db_session.commit()
    with pytest.raises(PermissionError):
        DocumentSegmentationService.delete_segments(
            sample_document.id,
            stranger.id,
        )
    assert TextSegment.query.filter_by(document_id=sample_document.id).count() == 1

    result = DocumentSegmentationService.delete_segments(
        sample_document.id,
        test_user.id,
    )
    assert result['segments_deleted'] == 1
    assert TextSegment.query.filter_by(document_id=sample_document.id).count() == 0
    job = db_session.get(ProcessingJob, result['job_id'])
    assert job.user_id == test_user.id
    assert job.get_result_data()['deletion_method'] == 'bulk_delete'


def test_experiment_owner_can_delete_segments_from_experiment_version(
    db_session, test_user, sample_document
):
    from app.models.document import Document
    from app.models.text_segment import TextSegment
    from app.services.document_segmentation_service import (
        DocumentSegmentationService,
    )

    owner = _user(db_session, 'version-experiment-owner')
    experiment = _experiment(db_session, owner, 'version')
    version = Document(
        title='Experiment-owned version',
        content='Version content.',
        content_type='text',
        document_type='document',
        status='completed',
        user_id=test_user.id,
        source_document_id=sample_document.id,
        version_number=2,
        version_type='experimental',
        experiment_id=experiment.id,
    )
    db_session.add(version)
    db_session.flush()
    db_session.add(TextSegment(
        document_id=version.id,
        content='Owned experiment segment.',
        segment_number=1,
    ))
    db_session.commit()

    result = DocumentSegmentationService.delete_segments(version.id, owner.id)
    assert result['segments_deleted'] == 1


def test_delete_rejects_missing_document_and_empty_segments(test_user, sample_document):
    from app.services.base_service import NotFoundError, ValidationError
    from app.services.document_segmentation_service import (
        DocumentSegmentationService,
    )

    with pytest.raises(NotFoundError):
        DocumentSegmentationService.delete_segments(999999, test_user.id)
    with pytest.raises(ValidationError, match='No segments found'):
        DocumentSegmentationService.delete_segments(
            sample_document.id,
            test_user.id,
        )


def test_segmentation_routes_map_validation_and_permission_errors(
    app, db_session, test_user, sample_document
):
    stranger = _user(db_session, 'route-stranger')
    client = app.test_client()
    with client.session_transaction() as session:
        session['_user_id'] = str(stranger.id)
        session['_fresh'] = True

    forbidden = client.post(
        f'/process/document/{sample_document.uuid}/segment',
        json={'method': 'paragraph'},
    )
    invalid = client.post(
        f'/process/document/{sample_document.uuid}/segment',
        json={'method': 'invalid'},
    )
    missing = client.post(
        '/process/document/00000000-0000-0000-0000-000000000000/segment',
        json={'method': 'paragraph'},
    )
    assert forbidden.status_code == 403
    assert forbidden.get_json()['error'] == 'Permission denied'
    assert invalid.status_code == 400
    assert invalid.get_json()['error'] == 'Unsupported segmentation method'
    assert missing.status_code == 404


def test_segmentation_routes_require_authentication(app, sample_document):
    client = app.test_client()
    segment = client.post(
        f'/process/document/{sample_document.uuid}/segment',
        json={},
    )
    delete = client.delete(
        f'/process/document/{sample_document.id}/segments'
    )
    assert segment.status_code == 401
    assert delete.status_code == 401
