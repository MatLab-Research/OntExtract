"""Regression coverage for authorized family-wide definition cleanup."""

import pytest


def _user(db_session, suffix):
    from app.models.user import User

    user = User(
        username=f'definition-cleanup-{suffix}',
        email=f'definition-cleanup-{suffix}@example.com',
        password='password',
        account_status='active',
    )
    db_session.add(user)
    db_session.commit()
    return user


def _experiment(db_session, user, suffix):
    from app.models.experiment import Experiment

    experiment = Experiment(
        name=f'Definition Cleanup {suffix}',
        experiment_type='entity_extraction',
        user_id=user.id,
        status='draft',
    )
    db_session.add(experiment)
    db_session.commit()
    return experiment


def _version(db_session, root, suffix):
    from app.models.document import Document

    version = Document(
        title=f'{root.title} {suffix}',
        content=root.content,
        content_type='text',
        document_type='document',
        status='completed',
        user_id=root.user_id,
        source_document_id=root.id,
        version_number=2,
        version_type='processed',
    )
    db_session.add(version)
    db_session.commit()
    return version


def _canonical_processing(
    db_session,
    experiment,
    document,
    processing_type,
    artifact_type,
):
    from app.models.experiment_document import ExperimentDocument
    from app.models.experiment_processing import (
        DocumentProcessingIndex,
        ExperimentDocumentProcessing,
        ProcessingArtifact,
    )

    association = ExperimentDocument.query.filter_by(
        experiment_id=experiment.id,
        document_id=document.id,
    ).first()
    if not association:
        association = ExperimentDocument(
            experiment_id=experiment.id,
            document_id=document.id,
        )
        db_session.add(association)
        db_session.flush()
    operation = ExperimentDocumentProcessing(
        experiment_document_id=association.id,
        processing_type=processing_type,
        processing_method='test-method',
        status='completed',
    )
    db_session.add(operation)
    db_session.flush()
    artifact = ProcessingArtifact(
        processing_id=operation.id,
        document_id=document.id,
        artifact_type=artifact_type,
        artifact_index=0,
    )
    index = DocumentProcessingIndex(
        document_id=document.id,
        experiment_id=experiment.id,
        processing_id=operation.id,
        processing_type=processing_type,
        processing_method='test-method',
        status='completed',
    )
    db_session.add_all([artifact, index])
    db_session.commit()
    return association, operation, artifact, index


def _legacy_job(db_session, user, document, job_type):
    from app.models.processing_job import ProcessingJob

    job = ProcessingJob(
        document_id=document.id,
        user_id=user.id,
        job_type=job_type,
        status='completed',
    )
    db_session.add(job)
    db_session.commit()
    return job


def test_definition_cleanup_route_remains_canonical(app):
    assert app.view_functions['processing.clear_definitions'].__module__ == (
        'app.routes.processing.cleanup'
    )


def test_clear_removes_definition_records_across_family_and_preserves_unrelated(
    db_session, test_user, sample_document
):
    from app.models.experiment_document import ExperimentDocument
    from app.models.experiment_processing import (
        DocumentProcessingIndex,
        ExperimentDocumentProcessing,
        ProcessingArtifact,
    )
    from app.models.processing_job import ProcessingJob
    from app.services.definition_cleanup_service import DefinitionCleanupService

    version = _version(db_session, sample_document, 'processed')
    experiment = _experiment(db_session, test_user, 'family')
    _, root_definition, _, _ = _canonical_processing(
        db_session,
        experiment,
        sample_document,
        'definitions',
        'term_definition',
    )
    _, version_definition, _, _ = _canonical_processing(
        db_session,
        experiment,
        version,
        'definitions',
        'term_definition',
    )
    _, entity_operation, entity_artifact, entity_index = _canonical_processing(
        db_session,
        experiment,
        version,
        'entities',
        'extracted_entity',
    )
    definition_job = _legacy_job(
        db_session,
        test_user,
        sample_document,
        'definition_extraction',
    )
    version_definition_job = _legacy_job(
        db_session,
        test_user,
        version,
        'definition_extraction',
    )
    entity_job = _legacy_job(
        db_session,
        test_user,
        version,
        'entity_extraction',
    )
    root_definition_id = root_definition.id
    version_definition_id = version_definition.id
    definition_job_id = definition_job.id
    version_definition_job_id = version_definition_job.id
    entity_operation_id = entity_operation.id
    entity_artifact_id = entity_artifact.id
    entity_index_id = entity_index.id
    entity_job_id = entity_job.id

    result = DefinitionCleanupService.clear(version.uuid, test_user.id)

    assert result == {
        'success': True,
        'deleted_count': 2,
        'jobs_deleted': 4,
        'message': 'Deleted 2 definitions and 4 processing jobs',
    }
    assert db_session.get(ExperimentDocumentProcessing, root_definition_id) is None
    assert db_session.get(ExperimentDocumentProcessing, version_definition_id) is None
    assert db_session.get(ProcessingJob, definition_job_id) is None
    assert db_session.get(ProcessingJob, version_definition_job_id) is None
    assert db_session.get(ExperimentDocumentProcessing, entity_operation_id) is not None
    assert db_session.get(ProcessingArtifact, entity_artifact_id) is not None
    assert db_session.get(DocumentProcessingIndex, entity_index_id) is not None
    assert db_session.get(ProcessingJob, entity_job_id) is not None
    assert ExperimentDocument.query.filter_by(experiment_id=experiment.id).count() == 2


def test_clear_counts_family_artifacts_without_canonical_operation(
    db_session, test_user, sample_document
):
    from app.models.experiment_processing import ProcessingArtifact
    from app.services.definition_cleanup_service import DefinitionCleanupService

    version = _version(db_session, sample_document, 'orphan-artifact')
    experiment = _experiment(db_session, test_user, 'orphan-artifact')
    _, operation, _, _ = _canonical_processing(
        db_session,
        experiment,
        version,
        'entities',
        'extracted_entity',
    )
    artifact = ProcessingArtifact(
        processing_id=operation.id,
        document_id=version.id,
        artifact_type='term_definition',
        artifact_index=1,
    )
    db_session.add(artifact)
    db_session.commit()
    artifact_id = artifact.id
    operation_id = operation.id

    result = DefinitionCleanupService.clear(sample_document.uuid, test_user.id)
    assert result['deleted_count'] == 1
    assert result['jobs_deleted'] == 0
    assert db_session.get(ProcessingArtifact, artifact_id) is None
    assert db_session.get(
        type(operation),
        operation_id,
    ) is not None


def test_clear_is_idempotent_without_definition_results(
    test_user, sample_document
):
    from app.services.definition_cleanup_service import DefinitionCleanupService

    result = DefinitionCleanupService.clear(sample_document.uuid, test_user.id)
    assert result['deleted_count'] == 0
    assert result['jobs_deleted'] == 0


def test_clear_requires_root_owner_or_admin(
    db_session, test_user, admin_user, sample_document
):
    from app.services.base_service import PermissionError
    from app.services.definition_cleanup_service import DefinitionCleanupService

    version = _version(db_session, sample_document, 'authorization')
    stranger = _user(db_session, 'stranger')
    with pytest.raises(PermissionError):
        DefinitionCleanupService.clear(version.uuid, stranger.id)
    assert DefinitionCleanupService.clear(version.uuid, admin_user.id)['success'] is True


@pytest.mark.parametrize('document_uuid', ['not-a-uuid', '00000000-0000-0000-0000-000000000000'])
def test_clear_missing_document_is_typed_not_found(test_user, document_uuid):
    from app.services.base_service import NotFoundError
    from app.services.definition_cleanup_service import DefinitionCleanupService

    with pytest.raises(NotFoundError, match='Document not found'):
        DefinitionCleanupService.clear(document_uuid, test_user.id)


def test_clear_failure_rolls_back_all_definition_records(
    db_session, test_user, sample_document, monkeypatch
):
    from app.models.experiment_processing import (
        DocumentProcessingIndex,
        ExperimentDocumentProcessing,
        ProcessingArtifact,
    )
    from app.services.base_service import ServiceError
    from app.services.definition_cleanup_service import DefinitionCleanupService

    experiment = _experiment(db_session, test_user, 'rollback')
    _, operation, artifact, index = _canonical_processing(
        db_session,
        experiment,
        sample_document,
        'definitions',
        'term_definition',
    )
    operation_id = operation.id
    artifact_id = artifact.id
    index_id = index.id
    monkeypatch.setattr(
        DefinitionCleanupService,
        '_delete_legacy_jobs',
        staticmethod(lambda *args: (_ for _ in ()).throw(
            RuntimeError('forced cleanup failure')
        )),
    )
    with pytest.raises(ServiceError, match='Failed to clear definition results'):
        DefinitionCleanupService.clear(sample_document.uuid, test_user.id)
    assert db_session.get(ExperimentDocumentProcessing, operation_id) is not None
    assert db_session.get(ProcessingArtifact, artifact_id) is not None
    assert db_session.get(DocumentProcessingIndex, index_id) is not None


def test_definition_cleanup_route_contracts(
    auth_client, db_session, test_user, sample_document
):
    from app.models.processing_job import ProcessingJob

    job = _legacy_job(
        db_session,
        test_user,
        sample_document,
        'definition_extraction',
    )
    job_id = job.id
    success = auth_client.delete(
        f'/process/document/{sample_document.uuid}/clear/definitions'
    )
    missing = auth_client.delete(
        '/process/document/not-a-uuid/clear/definitions'
    )
    assert success.status_code == 200
    assert success.get_json()['jobs_deleted'] == 1
    assert db_session.get(ProcessingJob, job_id) is None
    assert missing.status_code == 404

    other_owner = _user(db_session, 'route-owner')
    from app.models.document import Document
    foreign_document = Document(
        title='Foreign cleanup document',
        content='Definition content.',
        content_type='text',
        document_type='document',
        status='completed',
        user_id=other_owner.id,
    )
    db_session.add(foreign_document)
    db_session.commit()
    forbidden = auth_client.delete(
        f'/process/document/{foreign_document.uuid}/clear/definitions'
    )
    assert forbidden.status_code == 403
    assert forbidden.get_json()['error'] == 'Permission denied'


def test_admin_can_clear_foreign_definition_results(
    admin_client, db_session
):
    from app.models.document import Document

    owner = _user(db_session, 'admin-route-owner')
    document = Document(
        title='Admin cleanup document',
        content='Definition content.',
        content_type='text',
        document_type='document',
        status='completed',
        user_id=owner.id,
    )
    db_session.add(document)
    db_session.commit()
    response = admin_client.delete(
        f'/process/document/{document.uuid}/clear/definitions'
    )
    assert response.status_code == 200


def test_definition_cleanup_route_requires_authentication(app, sample_document):
    response = app.test_client().delete(
        f'/process/document/{sample_document.uuid}/clear/definitions'
    )
    assert response.status_code == 401


def test_definition_cleanup_route_hides_service_error(
    auth_client, sample_document, monkeypatch
):
    from app.routes.processing import cleanup
    from app.services.base_service import ServiceError

    monkeypatch.setattr(
        cleanup.DefinitionCleanupService,
        'clear',
        lambda *args: (_ for _ in ()).throw(
            ServiceError('secret database details')
        ),
    )
    response = auth_client.delete(
        f'/process/document/{sample_document.uuid}/clear/definitions'
    )
    assert response.status_code == 500
    assert response.get_json()['error'] == 'Failed to clear definition results'
    assert 'secret' not in str(response.get_json())
