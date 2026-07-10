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
        "processing.segment_document": "app.routes.processing.segmentation.routes",
        "processing.delete_document_segments": "app.routes.processing.segmentation.routes",
        "processing.extract_entities": "app.routes.processing.entities",
        "processing.analyze_metadata": "app.routes.processing.metadata",
        "processing.clean_text": "app.routes.processing.text_cleanup",
        "processing.save_cleaned_text": "app.routes.processing.text_cleanup",
        "processing.enhanced_document_processing": "app.routes.processing.enhanced",
        "processing.batch_enhanced_processing": "app.routes.processing.batch",
        "processing.clear_document_jobs": "app.routes.processing.validation",
        "processing.processing_home": "app.routes.processing.status",
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


def test_segment_document_creates_processing_version_and_segments(
    auth_client, sample_document
):
    from app.models.text_segment import TextSegment

    response = auth_client.post(
        f"/process/document/{sample_document.uuid}/segment",
        json={"method": "paragraph"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["segments_created"] > 0
    assert payload["processing_version_id"] != sample_document.id
    assert payload["redirect_url"].endswith(payload["processing_version_uuid"])
    assert TextSegment.query.filter_by(
        document_id=payload["processing_version_id"]
    ).count() == payload["segments_created"]


def test_segment_document_rejects_empty_content(
    auth_client, db_session, sample_document
):
    sample_document.content = ""
    db_session.commit()

    response = auth_client.post(
        f"/process/document/{sample_document.uuid}/segment",
        json={"method": "paragraph"},
    )

    assert response.status_code == 400
    assert response.get_json() == {
        "success": False,
        "error": "Document has no content to segment",
    }


def test_delete_document_segments_rejects_document_without_segments(
    auth_client, sample_document
):
    response = auth_client.delete(
        f"/process/document/{sample_document.id}/segments"
    )

    assert response.status_code == 400
    assert response.get_json() == {
        "success": False,
        "error": "No segments found to delete",
    }


def test_delete_document_segments_removes_segments_and_records_job(
    auth_client, db_session, sample_document
):
    from app.models.processing_job import ProcessingJob
    from app.models.text_segment import TextSegment

    segment = TextSegment(
        document_id=sample_document.id,
        content="A segment to remove.",
        segment_number=1,
    )
    db_session.add(segment)
    db_session.commit()

    response = auth_client.delete(
        f"/process/document/{sample_document.id}/segments"
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["segments_deleted"] == 1
    assert TextSegment.query.filter_by(document_id=sample_document.id).count() == 0

    job = db_session.get(ProcessingJob, payload["job_id"])
    assert job.status == "completed"
    assert job.get_result_data()["segments_deleted"] == 1


def test_langextract_unavailable_returns_fallback_without_external_call(
    auth_client, sample_document, monkeypatch
):
    from app.routes.processing.segmentation import langextract

    class UnavailableLangExtractService:
        service_ready = False

    monkeypatch.setattr(
        langextract,
        "IntegratedLangExtractService",
        UnavailableLangExtractService,
    )

    response = auth_client.post(
        f"/process/document/{sample_document.uuid}/segment",
        json={"method": "langextract"},
    )

    assert response.status_code == 400
    payload = response.get_json()
    assert payload["success"] is False
    assert payload["fallback_available"] is True
    assert "GOOGLE_GEMINI_API_KEY" in payload["error"]


def test_langextract_success_uses_integrated_service_package(
    auth_client, sample_document, monkeypatch
):
    from app.models.processing_job import ProcessingJob
    from app.routes.processing.segmentation import langextract

    class SuccessfulLangExtractService:
        service_ready = True

        def analyze_and_orchestrate_document(self, **kwargs):
            return {
                "success": True,
                "analysis_id": "analysis-1",
                "provenance_tracking": {"tracked": True},
            }

        def get_segmentation_recommendations(self, content):
            return {
                "structural_segments": [
                    {
                        "start_pos": 0,
                        "end_pos": min(25, len(content)),
                        "type": "introduction",
                        "element": "paragraph",
                        "confidence": 0.9,
                    }
                ],
                "semantic_segments": [],
                "temporal_segments": [],
                "confidence": 0.9,
            }

    monkeypatch.setattr(
        langextract,
        "IntegratedLangExtractService",
        SuccessfulLangExtractService,
    )
    monkeypatch.setattr(
        langextract.provenance_service,
        "track_document_segmentation",
        lambda *args, **kwargs: None,
    )

    response = auth_client.post(
        f"/process/document/{sample_document.uuid}/segment",
        json={"method": "langextract"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["analysis_id"] == "analysis-1"
    assert payload["segments_created"] == 1
    assert payload["segmentation_summary"]["structural_segments"] == 1

    job = ProcessingJob.query.filter_by(
        document_id=payload["processing_version_id"],
        job_type="langextract_segmentation",
    ).one()
    assert job.status == "completed"
    assert job.get_parameters()["segments_created"] == 1


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
