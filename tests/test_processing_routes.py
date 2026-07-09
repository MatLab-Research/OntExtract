from flask import url_for


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
        "processing.start_processing": "pipeline",
        "processing.generate_embeddings": "embeddings",
        "processing.segment_document": "segmentation",
        "processing.delete_document_segments": "segmentation",
        "processing.extract_entities": "entities",
        "processing.analyze_metadata": "metadata",
        "processing.clean_text": "text_cleanup",
        "processing.save_cleaned_text": "text_cleanup",
        "processing.enhanced_document_processing": "enhanced",
        "processing.batch_enhanced_processing": "batch",
        "processing.clear_document_jobs": "validation",
        "processing.job_list": "status",
        "processing.get_langextract_details": "status",
        "processing.get_job_status": "status",
        "processing.get_document_processing_jobs": "status",
        "processing.view_embeddings_results": "results",
        "processing.view_entities_results": "results",
        "processing.view_segments_results": "results",
        "processing.view_clean_text_results": "results",
        "processing.view_enhanced_results": "results",
        "processing.view_definitions_results": "results",
        "processing.view_temporal_results": "results",
        "processing.clear_definitions": "cleanup",
    }

    actual_modules = {
        endpoint: app.view_functions[endpoint].__module__.rsplit(".", 1)[-1]
        for endpoint in expected_modules
    }

    assert actual_modules == expected_modules


def test_legacy_provenance_models_are_registered_without_route_side_effects():
    from app import db
    from app.models import ProvenanceActivity, ProvenanceEntity

    assert ProvenanceActivity.__table__ is db.metadata.tables["provenance_activities"]
    assert ProvenanceEntity.__table__ is db.metadata.tables["provenance_entities"]
