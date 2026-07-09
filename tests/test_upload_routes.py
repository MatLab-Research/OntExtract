"""Regression coverage for the modular upload route package."""

import pytest


def test_upload_routes_are_grouped_by_responsibility(app):
    expected_modules = {
        "upload.unified": "app.routes.upload.pages",
        "upload.redirect_old_routes": "app.routes.upload.pages",
        "upload.upload_document": "app.routes.upload.legacy",
        "upload.extract_metadata": "app.routes.upload.metadata",
        "upload.extract_metadata_stream": "app.routes.upload.streaming",
        "upload.save_document": "app.routes.upload.persistence",
        "upload.create_reference": "app.routes.upload.references",
    }

    actual_modules = {
        endpoint: app.view_functions[endpoint].__module__
        for endpoint in expected_modules
    }

    assert actual_modules == expected_modules


def test_upload_page_renders(auth_client):
    response = auth_client.get("/upload/")

    assert response.status_code == 200


def test_legacy_upload_without_file_redirects(auth_client):
    response = auth_client.post("/upload/document")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/upload/")


def test_old_upload_route_preserves_experiment_query(auth_client):
    response = auth_client.get("/upload/redirect?experiment_id=42")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/upload/?experiment_id=42")


def test_metadata_extraction_requires_valid_source(auth_client):
    response = auth_client.post("/upload/extract_metadata", data={})

    assert response.status_code == 400
    assert response.get_json()["error"] == "Invalid source type"


def test_doi_metadata_extraction_requires_doi(auth_client):
    response = auth_client.post(
        "/upload/extract_metadata",
        data={"source_type": "doi"},
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "DOI is required"


def test_streaming_metadata_extraction_requires_file(auth_client):
    response = auth_client.post("/upload/extract_metadata_stream", data={})

    assert response.status_code == 400
    assert response.get_json()["error"] == "No file uploaded"


def test_save_document_requires_temporary_file(auth_client):
    response = auth_client.post(
        "/upload/save_document",
        json={"metadata": {"title": "Test"}},
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "No document file to save"


@pytest.mark.parametrize(
    "payload",
    [{}, {"title": "Title only"}, {"content": "Content only"}],
)
def test_create_reference_requires_title_and_content(auth_client, payload):
    response = auth_client.post("/upload/create_reference", json=payload)

    assert response.status_code == 400
    assert response.get_json() == {
        "success": False,
        "error": "Title and content are required",
    }