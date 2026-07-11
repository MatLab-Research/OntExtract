"""Regression coverage for the modular PipelineService implementation."""


def test_pipeline_service_methods_are_grouped_by_responsibility():
    from app.services.pipeline_service import PipelineService

    expected_modules = {
        "get_pipeline_overview": "app.services.pipeline.overview",
        "get_process_document_data": "app.services.pipeline.overview",
        "get_processing_status": "app.services.pipeline.queries",
        "get_processing_artifacts": "app.services.pipeline.queries",
        "apply_embeddings": "app.services.pipeline.execution",
        "start_processing": "app.services.pipeline.execution",
        "_process_embeddings": "app.services.pipeline.embeddings",
        "_process_segmentation": "app.services.pipeline.segmentation",
        "_process_entities": "app.services.pipeline.entities",
        "_extract_entities_spacy": "app.services.pipeline.entities",
        "_extract_entities_nltk": "app.services.pipeline.entities",
        "_extract_entities_llm": "app.services.pipeline.entities",
        "_process_temporal": "app.services.pipeline.extraction",
        "_process_definitions": "app.services.pipeline.extraction",
        "_process_enhanced": "app.services.pipeline.extraction",
        "_create_provenance_record": "app.services.pipeline.provenance",
    }

    actual_modules = {
        method_name: getattr(PipelineService, method_name).__module__
        for method_name in expected_modules
    }

    assert actual_modules == expected_modules


def test_experiment_pipeline_route_uses_public_service_singleton():
    from app.routes.experiments.pipeline import pipeline_service
    from app.services.pipeline_service import get_pipeline_service

    assert pipeline_service is get_pipeline_service()


def test_pipeline_routes_are_grouped_by_http_responsibility(app):
    expected_modules = {
        "experiments.document_pipeline": "app.routes.experiments.pipeline.pages",
        "experiments.process_document": "app.routes.experiments.pipeline.pages",
        "experiments.apply_embeddings_to_experiment_document": (
            "app.routes.experiments.pipeline.execution"
        ),
        "experiments.start_experiment_processing": (
            "app.routes.experiments.pipeline.execution"
        ),
        "experiments.get_experiment_document_processing_status": (
            "app.routes.experiments.pipeline.queries"
        ),
        "experiments.get_processing_artifacts": (
            "app.routes.experiments.pipeline.queries"
        ),
    }
    assert {
        endpoint: app.view_functions[endpoint].__module__
        for endpoint in expected_modules
    } == expected_modules


def test_document_pipeline_page_renders(auth_client, experiment_with_documents):
    response = auth_client.get(
        f"/experiments/{experiment_with_documents.id}/document_pipeline"
    )

    assert response.status_code == 200


def test_process_document_page_renders(auth_client, experiment_with_documents):
    from app.models.experiment_document import ExperimentDocument

    experiment_document = ExperimentDocument.query.filter_by(
        experiment_id=experiment_with_documents.id
    ).first()
    document = experiment_document.document

    response = auth_client.get(
        f"/experiments/{experiment_with_documents.id}/process_document/{document.uuid}"
    )

    assert response.status_code == 200


def test_experiment_processing_status_api(auth_client, experiment_with_processing):
    from app.models.experiment_document import ExperimentDocument

    experiment_document = ExperimentDocument.query.filter_by(
        experiment_id=experiment_with_processing.id
    ).first()

    response = auth_client.get(
        "/experiments/api/experiment-document/"
        f"{experiment_document.id}/processing-status"
    )

    assert response.status_code == 200
    assert response.get_json()["experiment_document_id"] == experiment_document.id


def test_processing_artifacts_api(auth_client, experiment_with_processing):
    from app.models.experiment_document import ExperimentDocument
    from app.models.experiment_processing import ExperimentDocumentProcessing

    experiment_document = ExperimentDocument.query.filter_by(
        experiment_id=experiment_with_processing.id
    ).first()
    processing = ExperimentDocumentProcessing.query.filter_by(
        experiment_document_id=experiment_document.id
    ).first()

    response = auth_client.get(
        f"/experiments/api/processing/{processing.id}/artifacts"
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["processing_id"] == str(processing.id)
    assert payload["artifacts"]


def test_experiment_route_package_is_not_hidden_by_gitignore():
    from pathlib import Path
    import subprocess

    project_root = Path(__file__).resolve().parents[1]
    route_path = "app/routes/experiments/pipeline.py"
    result = subprocess.run(
        ["git", "check-ignore", "--no-index", route_path],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
