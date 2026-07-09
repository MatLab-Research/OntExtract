from flask import url_for
import pytest


def test_start_processing_returns_not_implemented_for_existing_document(
    client, sample_document
):
    response = client.get(f"/process/start/{sample_document.id}")

    assert response.status_code == 501
    payload = response.get_json()
    assert payload["error"] == "Processing startup is not implemented"
    assert payload["document_id"] == sample_document.id
    assert payload["document_title"] == sample_document.title
    assert "processing workflow" in payload["message"].lower()


def test_start_processing_returns_not_found_for_unknown_document(client):
    response = client.get("/process/start/999999")

    assert response.status_code == 404
    assert response.get_json()["error"] == "Document not found"


def test_start_processing_compatibility_alias(client, sample_document):
    response = client.get(f"/process/processing/start/{sample_document.id}")

    assert response.status_code == 501
    assert response.get_json()["document_id"] == sample_document.id


def test_start_processing_short_url_is_canonical(app):
    with app.test_request_context():
        generated_url = url_for("processing.start_processing", document_id=42)

    assert generated_url == "/process/start/42"


def test_processing_routes_are_grouped_by_responsibility(app):
    expected_modules = {
        "processing.start_processing": "app.routes.processing.pipeline",
        "processing.generate_embeddings": "app.routes.processing.embeddings",
        "processing.segment_document": "app.routes.processing.segmentation",
        "processing.delete_document_segments": "app.routes.processing.segmentation",
        "processing.extract_entities": "app.routes.processing.entities",
        "processing.analyze_metadata": "app.routes.processing.metadata",
        "processing.clean_text": "app.routes.processing.text_cleanup",
        "processing.save_cleaned_text": "app.routes.processing.text_cleanup",
        "processing.enhanced_document_processing": "app.routes.processing.enhanced",
        "processing.batch_enhanced_processing": "app.routes.processing.batch",
        "processing.clear_document_jobs": "app.routes.processing.validation",
        "processing.job_list": "app.routes.processing.status",
        "processing.get_langextract_details": "app.routes.processing.status",
        "processing.get_job_status": "app.routes.processing.status",
        "processing.get_document_processing_jobs": "app.routes.processing.status",
        "processing.view_embeddings_results": "app.routes.processing.results.embeddings",
        "processing.view_entities_results": "app.routes.processing.results.entities",
        "processing.view_segments_results": "app.routes.processing.results.segments",
        "processing.view_clean_text_results": "app.routes.processing.results.clean_text",
        "processing.view_enhanced_results": "app.routes.processing.results.enhanced",
        "processing.view_definitions_results": "app.routes.processing.results.definitions",
        "processing.view_temporal_results": "app.routes.processing.results.temporal",
        "processing.clear_definitions": "app.routes.processing.cleanup",
    }

    actual_modules = {
        endpoint: app.view_functions[endpoint].__module__
        for endpoint in expected_modules
    }

    assert actual_modules == expected_modules


def test_legacy_provenance_models_are_registered_without_route_side_effects():
    from app import db
    from app.models import ProvenanceActivity, ProvenanceEntity

    assert ProvenanceActivity.__table__ is db.metadata.tables["provenance_activities"]
    assert ProvenanceEntity.__table__ is db.metadata.tables["provenance_entities"]


def test_admin_routes_are_grouped_by_responsibility(app):
    expected_modules = {
        "admin.dashboard": "app.routes.admin.dashboard",
        "admin.list_users": "app.routes.admin.users",
        "admin.view_user": "app.routes.admin.users",
        "admin.edit_user": "app.routes.admin.users",
        "admin.set_user_password": "app.routes.admin.users",
        "admin.toggle_admin": "app.routes.admin.users",
        "admin.suspend_user": "app.routes.admin.users",
        "admin.activate_user": "app.routes.admin.users",
        "admin.delete_user": "app.routes.admin.users",
        "admin.make_admin": "app.routes.admin.users",
        "admin.error_log": "app.routes.admin.errors",
        "admin.system_health": "app.routes.admin.health",
        "admin.api_health": "app.routes.admin.health",
        "admin.background_tasks": "app.routes.admin.tasks",
        "admin.cancel_task": "app.routes.admin.tasks",
        "admin.data_management": "app.routes.admin.data",
        "admin.cleanup_failed_jobs": "app.routes.admin.data",
        "admin.cleanup_draft_experiments": "app.routes.admin.data",
    }

    actual_modules = {
        endpoint: app.view_functions[endpoint].__module__
        for endpoint in expected_modules
    }

    assert actual_modules == expected_modules


def test_processing_job_view_adapts_experiment_processing(
    experiment_with_processing,
):
    from app.models.experiment_document import ExperimentDocument
    from app.models.experiment_processing import ExperimentDocumentProcessing
    from app.services.processing_results import append_experiment_jobs

    experiment_document = ExperimentDocument.query.filter_by(
        experiment_id=experiment_with_processing.id
    ).first()
    processing = ExperimentDocumentProcessing.query.filter_by(
        experiment_document_id=experiment_document.id,
        processing_type="embeddings",
    ).first()

    jobs = append_experiment_jobs(
        [],
        [experiment_document.document_id],
        "embeddings",
    )

    assert len(jobs) == 1
    assert jobs[0].status == processing.status
    assert jobs[0].job_type == "embeddings"
    assert jobs[0].get_parameters() == {
        "method": "period_aware",
        "processing_type": "embeddings",
    }


def test_document_family_query_includes_base_and_derived_versions(
    db_session, sample_document
):
    from app.models.document import Document
    from app.services.processing_results import get_document_family_ids

    derived = Document(
        title="Derived document",
        content="Derived content",
        content_type="text/plain",
        document_type="document",
        status="completed",
        user_id=sample_document.user_id,
        source_document_id=sample_document.id,
        version_number=2,
        version_type="processed",
    )
    db_session.add(derived)
    db_session.commit()

    assert set(get_document_family_ids(derived)) == {
        sample_document.id,
        derived.id,
    }


@pytest.mark.parametrize(
    "result_type",
    [
        "embeddings",
        "entities",
        "segments",
        "clean-text",
        "enhanced",
        "definitions",
        "temporal",
    ],
)
def test_document_processing_result_pages_render(
    client, sample_document, result_type
):
    response = client.get(
        f"/process/document/{sample_document.uuid}/results/{result_type}"
    )

    assert response.status_code == 200


@pytest.mark.parametrize(
    "path",
    ["/admin", "/admin/users", "/admin/data"],
)
def test_admin_pages_render_after_route_split(admin_client, path):
    response = admin_client.get(path)

    assert response.status_code == 200
