"""Regression coverage for owner-scoped experiment pipeline access."""

from types import SimpleNamespace

import pytest


def _user(db_session, suffix):
    from app.models.user import User

    user = User(
        username=f'pipeline-access-{suffix}',
        email=f'pipeline-access-{suffix}@example.com',
        password='password',
        account_status='active',
    )
    db_session.add(user)
    db_session.commit()
    return user


def _client_for(app, user):
    client = app.test_client()
    with client.session_transaction() as session:
        session['_user_id'] = str(user.id)
        session['_fresh'] = True
    return client


def _resources(experiment):
    from app.models.experiment_document import ExperimentDocument
    from app.models.experiment_processing import ExperimentDocumentProcessing

    experiment_document = ExperimentDocument.query.filter_by(
        experiment_id=experiment.id
    ).first()
    processing = ExperimentDocumentProcessing.query.filter_by(
        experiment_document_id=experiment_document.id
    ).first()
    return experiment_document, processing


def test_pipeline_routes_remain_canonical(app):
    expected = {
        'experiments.document_pipeline': 'app.routes.experiments.pipeline.pages',
        'experiments.process_document': 'app.routes.experiments.pipeline.pages',
        'experiments.apply_embeddings_to_experiment_document': (
            'app.routes.experiments.pipeline.execution'
        ),
        'experiments.start_experiment_processing': (
            'app.routes.experiments.pipeline.execution'
        ),
        'experiments.get_experiment_document_processing_status': (
            'app.routes.experiments.pipeline.queries'
        ),
        'experiments.get_processing_artifacts': (
            'app.routes.experiments.pipeline.queries'
        ),
    }
    assert {
        endpoint: app.view_functions[endpoint].__module__
        for endpoint in expected
    } == expected


@pytest.mark.parametrize(
    ('processing_type', 'processing_method'),
    [
        ('embeddings', 'local'),
        ('embeddings', 'openai'),
        ('embeddings', 'sentence_transformers'),
        ('embeddings', 'gemini'),
        ('embeddings', 'period_aware'),
        ('segmentation', 'paragraph'),
        ('segmentation', 'sentence'),
        ('segmentation', 'semantic'),
        ('entities', 'spacy'),
        ('entities', 'nltk'),
        ('entities', 'llm'),
        ('temporal', 'spacy'),
        ('definitions', 'pattern'),
        ('enhanced_processing', 'enhanced'),
    ],
)
def test_start_processing_dto_accepts_supported_pairs(
    processing_type, processing_method
):
    from app.dto.pipeline_dto import StartProcessingDTO

    dto = StartProcessingDTO(
        experiment_document_id=1,
        processing_type=processing_type,
        processing_method=processing_method,
    )
    assert dto.processing_type == processing_type
    assert dto.processing_method == processing_method


@pytest.mark.parametrize(
    'payload',
    [
        {
            'experiment_document_id': 1,
            'processing_type': 'definitions',
            'processing_method': 'llm',
        },
        {
            'experiment_document_id': 1,
            'processing_type': 'etymology',
            'processing_method': 'pattern',
        },
        {
            'experiment_document_id': 1,
            'processing_type': 'temporal',
            'processing_method': 'nltk',
        },
        {
            'experiment_document_id': 1,
            'processing_type': 'segmentation',
            'processing_method': 'paragraph',
            'unexpected': True,
        },
    ],
)
def test_start_processing_dto_rejects_invalid_pairs_and_extra_fields(payload):
    from pydantic import ValidationError

    from app.dto.pipeline_dto import StartProcessingDTO

    with pytest.raises(ValidationError):
        StartProcessingDTO(**payload)


def test_access_service_resolves_owner_and_admin_and_rejects_foreign_user(
    db_session, test_user, admin_user, experiment_with_processing
):
    from app.services.base_service import PermissionError
    from app.services.pipeline_access_service import PipelineAccessService

    experiment_document, processing = _resources(experiment_with_processing)
    stranger = _user(db_session, 'resolver-stranger')
    assert PipelineAccessService.experiment(
        experiment_with_processing.id,
        test_user.id,
    ) is experiment_with_processing
    assert PipelineAccessService.experiment_document(
        experiment_document.id,
        admin_user.id,
    ) is experiment_document
    assert PipelineAccessService.processing(
        processing.id,
        test_user.id,
    ) is processing
    with pytest.raises(PermissionError):
        PipelineAccessService.experiment(
            experiment_with_processing.id,
            stranger.id,
        )
    with pytest.raises(PermissionError):
        PipelineAccessService.experiment_document(
            experiment_document.id,
            stranger.id,
        )
    with pytest.raises(PermissionError):
        PipelineAccessService.processing(processing.id, stranger.id)


def test_pipeline_reads_are_actor_scoped(
    db_session, test_user, admin_user, experiment_with_processing
):
    from app.services.base_service import PermissionError
    from app.services.pipeline_service import get_pipeline_service

    experiment_document, processing = _resources(experiment_with_processing)
    service = get_pipeline_service()
    overview = service.get_pipeline_overview(
        experiment_with_processing.id,
        test_user.id,
    )
    document_data = service.get_process_document_data(
        experiment_with_processing.id,
        experiment_document.document_id,
        admin_user.id,
    )
    status = service.get_processing_status(
        experiment_document.id,
        test_user.id,
    )
    artifacts = service.get_processing_artifacts(
        processing.id,
        admin_user.id,
    )
    assert overview['experiment'] is experiment_with_processing
    assert document_data['experiment_document'] is experiment_document
    assert status['experiment_document_id'] == experiment_document.id
    assert artifacts['processing_id'] == str(processing.id)

    stranger = _user(db_session, 'read-stranger')
    for action in (
        lambda: service.get_pipeline_overview(
            experiment_with_processing.id,
            stranger.id,
        ),
        lambda: service.get_process_document_data(
            experiment_with_processing.id,
            experiment_document.document_id,
            stranger.id,
        ),
        lambda: service.get_processing_status(
            experiment_document.id,
            stranger.id,
        ),
        lambda: service.get_processing_artifacts(processing.id, stranger.id),
    ):
        with pytest.raises(PermissionError):
            action()


def test_foreign_processing_writes_are_rejected_before_creation_or_embedding_import(
    db_session, experiment_with_processing, monkeypatch
):
    from app.models.experiment_processing import ExperimentDocumentProcessing
    from app.services.base_service import PermissionError
    from app.services.pipeline_service import get_pipeline_service

    experiment_document, _ = _resources(experiment_with_processing)
    stranger = _user(db_session, 'write-stranger')
    service = get_pipeline_service()
    before = ExperimentDocumentProcessing.query.count()
    with pytest.raises(PermissionError):
        service.start_processing(
            experiment_document_id=experiment_document.id,
            processing_type='segmentation',
            processing_method='paragraph',
            user_id=stranger.id,
        )
    with pytest.raises(PermissionError):
        service.apply_embeddings(
            experiment_with_processing.id,
            experiment_document.document_id,
            stranger.id,
        )
    assert ExperimentDocumentProcessing.query.count() == before


def test_direct_service_rejects_unsupported_type_method_pair(
    experiment_with_processing, test_user
):
    from app.services.base_service import ValidationError
    from app.services.pipeline_service import get_pipeline_service

    experiment_document, _ = _resources(experiment_with_processing)
    with pytest.raises(ValidationError, match='Unsupported method'):
        get_pipeline_service().start_processing(
            experiment_document_id=experiment_document.id,
            processing_type='definitions',
            processing_method='llm',
            user_id=test_user.id,
        )


def test_private_pipeline_get_routes_require_authentication(
    app, experiment_with_processing
):
    experiment_document, processing = _resources(experiment_with_processing)
    client = app.test_client()
    paths = (
        f'/experiments/{experiment_with_processing.id}/document_pipeline',
        f'/experiments/{experiment_with_processing.id}/process_document/'
        f'{experiment_document.document.uuid}',
        '/experiments/api/experiment-document/'
        f'{experiment_document.id}/processing-status',
        f'/experiments/api/processing/{processing.id}/artifacts',
    )
    assert all(client.get(path).status_code == 302 for path in paths)


def test_pipeline_write_routes_require_authentication(
    app, experiment_with_processing
):
    experiment_document, _ = _resources(experiment_with_processing)
    client = app.test_client()
    embeddings = client.post(
        f'/experiments/{experiment_with_processing.id}/document/'
        f'{experiment_document.document_id}/apply_embeddings'
    )
    processing = client.post(
        '/experiments/api/experiment-processing/start',
        json={
            'experiment_document_id': experiment_document.id,
            'processing_type': 'segmentation',
            'processing_method': 'paragraph',
        },
    )
    assert embeddings.status_code == 401
    assert processing.status_code == 401


def test_owner_pipeline_routes_return_private_data(
    auth_client, experiment_with_processing
):
    experiment_document, processing = _resources(experiment_with_processing)
    overview = auth_client.get(
        f'/experiments/{experiment_with_processing.id}/document_pipeline'
    )
    document = auth_client.get(
        f'/experiments/{experiment_with_processing.id}/process_document/'
        f'{experiment_document.document.uuid}'
    )
    status = auth_client.get(
        '/experiments/api/experiment-document/'
        f'{experiment_document.id}/processing-status'
    )
    artifacts = auth_client.get(
        f'/experiments/api/processing/{processing.id}/artifacts'
    )
    assert overview.status_code == 200
    assert document.status_code == 200
    assert status.status_code == 200
    assert artifacts.status_code == 200


def test_foreign_pipeline_routes_are_forbidden(
    app, db_session, experiment_with_processing
):
    experiment_document, processing = _resources(experiment_with_processing)
    stranger = _user(db_session, 'route-stranger')
    client = _client_for(app, stranger)
    html_paths = (
        f'/experiments/{experiment_with_processing.id}/document_pipeline',
        f'/experiments/{experiment_with_processing.id}/process_document/'
        f'{experiment_document.document.uuid}',
    )
    json_paths = (
        '/experiments/api/experiment-document/'
        f'{experiment_document.id}/processing-status',
        f'/experiments/api/processing/{processing.id}/artifacts',
    )
    assert all(client.get(path).status_code == 403 for path in html_paths)
    for path in json_paths:
        response = client.get(path)
        assert response.status_code == 403
        assert response.get_json()['error'] == 'Permission denied'

    before = type(processing).query.count()
    start = client.post('/experiments/api/experiment-processing/start', json={
        'experiment_document_id': experiment_document.id,
        'processing_type': 'segmentation',
        'processing_method': 'paragraph',
    })
    embeddings = client.post(
        f'/experiments/{experiment_with_processing.id}/document/'
        f'{experiment_document.document_id}/apply_embeddings'
    )
    assert start.status_code == 403
    assert embeddings.status_code == 403
    assert type(processing).query.count() == before


def test_pipeline_execution_route_passes_actor_and_maps_safe_errors(
    auth_client, test_user, monkeypatch
):
    from app.routes.experiments.pipeline import execution
    from app.services.base_service import ServiceError

    calls = []

    def start_processing(**kwargs):
        calls.append(kwargs)
        return {'processing_id': 'processing-id', 'status': 'completed'}

    monkeypatch.setattr(
        execution,
        'pipeline_service',
        SimpleNamespace(
            start_processing=start_processing,
            apply_embeddings=lambda *args: (_ for _ in ()).throw(
                ServiceError('secret embedding failure')
            ),
        ),
    )
    success = auth_client.post(
        '/experiments/api/experiment-processing/start',
        json={
            'experiment_document_id': 7,
            'processing_type': 'definitions',
            'processing_method': 'pattern',
        },
    )
    invalid = auth_client.post(
        '/experiments/api/experiment-processing/start',
        json={
            'experiment_document_id': 7,
            'processing_type': 'definitions',
            'processing_method': 'llm',
        },
    )
    failure = auth_client.post('/experiments/1/document/2/apply_embeddings')
    assert success.status_code == 200
    assert calls == [{
        'experiment_document_id': 7,
        'processing_type': 'definitions',
        'processing_method': 'pattern',
        'user_id': test_user.id,
    }]
    assert invalid.status_code == 400
    assert invalid.get_json()['error'] == 'Validation failed'
    assert failure.status_code == 500
    assert failure.get_json()['error'] == 'Failed to apply embeddings'
    assert 'secret' not in str(failure.get_json())


def test_failed_processing_result_hides_internal_error(
    auth_client, monkeypatch
):
    from app.routes.experiments.pipeline import execution

    monkeypatch.setattr(
        execution,
        'pipeline_service',
        SimpleNamespace(start_processing=lambda **kwargs: {
            'processing_id': 'failed-processing-id',
            'status': 'failed',
            'error': 'Processing failed: secret model details',
        }),
    )
    response = auth_client.post(
        '/experiments/api/experiment-processing/start',
        json={
            'experiment_document_id': 7,
            'processing_type': 'definitions',
            'processing_method': 'pattern',
        },
    )
    assert response.status_code == 400
    assert response.get_json() == {
        'success': False,
        'error': 'Processing operation failed',
        'processing_id': 'failed-processing-id',
    }


def test_pipeline_query_routes_hide_unexpected_errors(
    auth_client, monkeypatch
):
    from app.routes.experiments.pipeline import queries

    monkeypatch.setattr(
        queries,
        'pipeline_service',
        SimpleNamespace(
            get_processing_status=lambda *args: (_ for _ in ()).throw(
                RuntimeError('secret status error')
            ),
            get_processing_artifacts=lambda *args: (_ for _ in ()).throw(
                RuntimeError('secret artifact error')
            ),
        ),
    )
    status = auth_client.get(
        '/experiments/api/experiment-document/1/processing-status'
    )
    artifacts = auth_client.get(
        '/experiments/api/processing/'
        '00000000-0000-0000-0000-000000000001/artifacts'
    )
    assert status.status_code == 500
    assert status.get_json()['error'] == 'Failed to get processing status'
    assert artifacts.status_code == 500
    assert artifacts.get_json()['error'] == 'Failed to get processing artifacts'
    assert 'secret' not in str(status.get_json())
    assert 'secret' not in str(artifacts.get_json())
