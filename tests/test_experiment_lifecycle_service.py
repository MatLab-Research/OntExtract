"""Regression coverage for canonical experiment lifecycle transitions."""

import json

import pytest


def test_lifecycle_routes_remain_canonical(app):
    expected = 'app.routes.experiments.crud.lifecycle'
    for endpoint in (
        'experiments.delete',
        'experiments.duplicate',
        'experiments.mark_complete',
        'experiments.run',
    ):
        assert app.view_functions[endpoint].__module__ == expected


def test_duplicate_copies_configuration_term_documents_and_references(
    db_session,
    experiment_with_documents,
    sample_term,
    test_user,
    sample_document,
):
    from app import db
    from app.models.experiment import Experiment, experiment_references
    from app.models.experiment_document import ExperimentDocument
    from app.services.experiment_lifecycle_service import ExperimentLifecycleService

    experiment_with_documents.configuration = json.dumps({'mode': 'temporal'})
    experiment_with_documents.term_id = sample_term.id
    reference = sample_document
    reference.document_type = 'reference'
    db_session.execute(experiment_references.insert().values(
        experiment_id=experiment_with_documents.id,
        reference_id=reference.id,
        include_in_analysis=True,
        notes='Copied note',
    ))
    db_session.commit()

    duplicate = ExperimentLifecycleService.duplicate(
        experiment_with_documents.id,
        test_user.id,
    )

    assert duplicate.name == f'{experiment_with_documents.name} (Copy)'
    assert duplicate.status == 'draft'
    assert duplicate.user_id == test_user.id
    assert duplicate.term_id == sample_term.id
    assert duplicate.configuration == experiment_with_documents.configuration
    original_ids = {
        row.document_id
        for row in ExperimentDocument.query.filter_by(
            experiment_id=experiment_with_documents.id
        ).all()
    }
    duplicate_rows = ExperimentDocument.query.filter_by(
        experiment_id=duplicate.id
    ).all()
    assert {row.document_id for row in duplicate_rows} == original_ids
    assert all(row.processing_status == 'pending' for row in duplicate_rows)
    assert {document.id for document in duplicate.documents} == original_ids
    reference_row = db_session.execute(
        db.select(experiment_references).where(
            experiment_references.c.experiment_id == duplicate.id
        )
    ).mappings().one()
    assert reference_row['reference_id'] == reference.id
    assert reference_row['include_in_analysis'] is True
    assert reference_row['notes'] == 'Copied note'
    assert db_session.get(Experiment, duplicate.id) is duplicate


def test_mark_complete_requires_completed_canonical_processing(
    db_session, temporal_experiment, sample_document, test_user
):
    from app.models.experiment_document import ExperimentDocument
    from app.models.experiment_processing import ExperimentDocumentProcessing
    from app.services.base_service import ValidationError
    from app.services.experiment_lifecycle_service import ExperimentLifecycleService

    association = ExperimentDocument(
        experiment_id=temporal_experiment.id,
        document_id=sample_document.id,
    )
    db_session.add(association)
    db_session.flush()
    operation = ExperimentDocumentProcessing(
        experiment_document_id=association.id,
        processing_type='embeddings',
        processing_method='local',
        status='failed',
    )
    db_session.add(operation)
    db_session.commit()

    with pytest.raises(ValidationError, match='No processing results found'):
        ExperimentLifecycleService.mark_complete(
            temporal_experiment.id,
            test_user.id,
        )

    operation.status = 'completed'
    db_session.commit()
    completed = ExperimentLifecycleService.mark_complete(
        temporal_experiment.id,
        test_user.id,
    )
    assert completed.status == 'completed'
    assert completed.completed_at is not None


def test_mark_complete_isolated_from_shared_document_processing(
    db_session, test_user, sample_document
):
    from app.models.experiment import Experiment
    from app.models.experiment_document import ExperimentDocument
    from app.models.experiment_processing import ExperimentDocumentProcessing
    from app.services.base_service import ValidationError
    from app.services.experiment_lifecycle_service import ExperimentLifecycleService

    owner = Experiment(
        name='Processing owner', experiment_type='entity_extraction',
        user_id=test_user.id, status='draft',
    )
    viewer = Experiment(
        name='Shared viewer', experiment_type='entity_extraction',
        user_id=test_user.id, status='draft',
    )
    db_session.add_all([owner, viewer])
    db_session.flush()
    owner_link = ExperimentDocument(
        experiment_id=owner.id, document_id=sample_document.id
    )
    viewer_link = ExperimentDocument(
        experiment_id=viewer.id, document_id=sample_document.id
    )
    db_session.add_all([owner_link, viewer_link])
    db_session.flush()
    db_session.add(ExperimentDocumentProcessing(
        experiment_document_id=owner_link.id,
        processing_type='entities', processing_method='spacy', status='completed',
    ))
    db_session.commit()

    assert ExperimentLifecycleService.mark_complete(
        owner.id, test_user.id
    ).status == 'completed'
    with pytest.raises(ValidationError, match='No processing results found'):
        ExperimentLifecycleService.mark_complete(viewer.id, test_user.id)


def test_lifecycle_transitions_require_owner(
    db_session, temporal_experiment, admin_user
):
    from app.services.base_service import PermissionError
    from app.services.experiment_lifecycle_service import ExperimentLifecycleService

    stranger = _make_user(db_session, 'lifecycle-stranger')
    with pytest.raises(PermissionError):
        ExperimentLifecycleService.mark_complete(
            temporal_experiment.id, stranger.id
        )
    # Admin permission remains valid.
    temporal_experiment.status = 'completed'
    db_session.commit()
    with pytest.raises(Exception) as exc:
        ExperimentLifecycleService.mark_complete(
            temporal_experiment.id, admin_user.id
        )
    assert not isinstance(exc.value, PermissionError)


def _make_user(db_session, suffix):
    from app.models.user import User

    user = User(
        username=suffix,
        email=f'{suffix}@example.com',
        password='password',
        account_status='active',
    )
    db_session.add(user)
    db_session.commit()
    return user


def test_run_non_domain_experiment_persists_results(
    db_session, experiment_with_documents, test_user
):
    from app.models.experiment_document import ExperimentDocument
    from app.services.experiment_lifecycle_service import ExperimentLifecycleService

    completed = ExperimentLifecycleService().run(
        experiment_with_documents.id,
        test_user.id,
    )
    result = json.loads(completed.results)
    assert completed.status == 'completed'
    assert completed.results_summary.startswith('Analyzed')
    assert result['experiment_type'] == experiment_with_documents.experiment_type
    assert result['document_count'] == ExperimentDocument.query.filter_by(
        experiment_id=experiment_with_documents.id
    ).count()


def test_run_failure_marks_loaded_experiment_error(
    db_session, experiment_with_documents, test_user, sample_document
):
    from app.services.experiment_lifecycle_service import ExperimentLifecycleService

    class FailingDomain:
        def run(self, experiment, text_service):
            raise RuntimeError('Analysis failed')

    experiment_with_documents.experiment_type = 'domain_comparison'
    # Domain comparison can_run requires a reference.
    reference = sample_document
    reference.document_type = 'reference'
    experiment_with_documents.references.append(reference)
    db_session.commit()
    service = ExperimentLifecycleService(
        domain_service_factory=FailingDomain,
        text_service_factory=lambda: object(),
    )

    with pytest.raises(RuntimeError, match='Analysis failed'):
        service.run(experiment_with_documents.id, test_user.id)
    assert experiment_with_documents.status == 'error'


def test_lifecycle_routes_return_correct_errors(
    auth_client, db_session, temporal_experiment, test_user
):
    stranger = _make_user(db_session, 'route-lifecycle-stranger')
    with auth_client.application.test_client() as stranger_client:
        with stranger_client.session_transaction() as session:
            session['_user_id'] = str(stranger.id)
            session['_fresh'] = True
        forbidden = stranger_client.post(
            f'/experiments/{temporal_experiment.id}/mark-complete'
        )

    missing_run = auth_client.post('/experiments/999999/run')
    missing_duplicate = auth_client.post('/experiments/999999/duplicate')
    missing_delete = auth_client.post('/experiments/999999/delete')

    assert forbidden.status_code == 403
    assert missing_run.status_code == 404
    assert missing_duplicate.status_code == 404
    assert missing_delete.status_code == 404


def test_run_route_sanitizes_unexpected_failures(
    auth_client, monkeypatch, experiment_with_documents
):
    from app.routes.experiments.crud import lifecycle

    monkeypatch.setattr(
        lifecycle.ExperimentLifecycleService,
        'run',
        lambda self, experiment_id, actor_id: (_ for _ in ()).throw(
            RuntimeError('secret analysis detail')
        ),
    )
    response = auth_client.post(
        f'/experiments/{experiment_with_documents.id}/run'
    )
    assert response.status_code == 500
    assert response.get_json() == {'error': 'Failed to run experiment'}
    assert 'secret' not in str(response.get_json())


def test_experiment_detail_hides_mutation_controls_from_non_owner(
    app, db_session, test_user, temporal_experiment
):
    stranger = _make_user(db_session, 'lifecycle-viewer')
    client = app.test_client()
    with client.session_transaction() as session:
        session['_user_id'] = str(stranger.id)
        session['_fresh'] = True

    temporal_experiment.status = 'draft'
    db_session.commit()
    draft = client.get(f'/experiments/{temporal_experiment.id}')
    assert draft.status_code == 200
    assert b'id="delete-experiment"' not in draft.data
    assert b'>Edit<' not in draft.data
    assert b'id="mark-complete-experiment"' not in draft.data


def test_completed_experiment_still_allows_authenticated_viewer_to_duplicate(
    app, db_session, test_user, temporal_experiment
):
    stranger = _make_user(db_session, 'lifecycle-duplicator')
    temporal_experiment.status = 'completed'
    db_session.commit()
    client = app.test_client()
    with client.session_transaction() as session:
        session['_user_id'] = str(stranger.id)
        session['_fresh'] = True

    response = client.get(f'/experiments/{temporal_experiment.id}')
    assert response.status_code == 200
    assert b'id="duplicate-experiment"' in response.data
    assert b'id="delete-experiment"' not in response.data
