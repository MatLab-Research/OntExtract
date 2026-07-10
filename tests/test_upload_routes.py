"""Regression coverage for the modular upload route package."""

from io import BytesIO
from types import SimpleNamespace

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


def test_doi_metadata_extraction_builds_review_payload(
    auth_client, monkeypatch
):
    from app.routes.upload import metadata

    fake_service = SimpleNamespace(
        extract_metadata_from_doi=lambda doi: SimpleNamespace(
            success=True,
            metadata={"title": "Agency", "doi": doi},
            error=None,
        )
    )
    monkeypatch.setattr(metadata, "upload_service", fake_service)

    response = auth_client.post(
        "/upload/extract_metadata",
        data={"source_type": "doi", "doi": "10.1000/agency"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["needs_file"] is True
    assert payload["metadata"]["title"] == "Agency"
    assert payload["provenance"]["doi"]["source"] == "crossref"


def test_file_metadata_with_crossref_disabled_preserves_temp_file(
    auth_client, tmp_path, monkeypatch
):
    from app.routes.upload import metadata

    temp_file = tmp_path / "review.pdf"
    temp_file.write_bytes(b"pdf")
    cleaned = []
    fake_service = SimpleNamespace(
        save_to_temp=lambda file: SimpleNamespace(
            success=True,
            temp_path=str(temp_file),
            error=None,
        ),
        merge_metadata=lambda *items: {
            key: value
            for item in items
            for key, value in item.items()
            if value is not None
        },
        cleanup_temp=lambda path: cleaned.append(path),
    )
    monkeypatch.setattr(metadata, "upload_service", fake_service)

    response = auth_client.post(
        "/upload/extract_metadata",
        data={
            "source_type": "file",
            "document_file": (BytesIO(b"pdf"), "review.pdf"),
            "enable_crossref": "false",
            "title": "User title",
            "authors": "Ada Lovelace, Alan Turing",
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["metadata"]["title"] == "User title"
    assert payload["metadata"]["authors"] == "Ada Lovelace, Alan Turing"
    assert payload["temp_path"] == str(temp_file)
    assert cleaned == []


def test_file_metadata_without_title_cleans_temp_file(
    auth_client, tmp_path, monkeypatch
):
    from app.routes.upload import metadata

    temp_file = tmp_path / "invalid.pdf"
    temp_file.write_bytes(b"pdf")
    cleaned = []
    fake_service = SimpleNamespace(
        save_to_temp=lambda file: SimpleNamespace(
            success=True,
            temp_path=str(temp_file),
            error=None,
        ),
        merge_metadata=lambda *items: {},
        cleanup_temp=lambda path: cleaned.append(path),
    )
    monkeypatch.setattr(metadata, "upload_service", fake_service)

    response = auth_client.post(
        "/upload/extract_metadata",
        data={
            "source_type": "file",
            "document_file": (BytesIO(b"pdf"), "invalid.pdf"),
            "enable_crossref": "false",
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert cleaned == [str(temp_file)]


def test_file_metadata_uses_successful_pdf_extraction(
    auth_client, tmp_path, monkeypatch
):
    from app.routes.upload import metadata

    temp_file = tmp_path / "matched.pdf"
    temp_file.write_bytes(b"pdf")
    fake_service = SimpleNamespace(
        save_to_temp=lambda file: SimpleNamespace(
            success=True,
            temp_path=str(temp_file),
            error=None,
        ),
        extract_metadata_from_pdf=lambda path: SimpleNamespace(
            success=True,
            metadata={
                "title": "Matched title",
                "doi": "10.1000/matched",
                "extraction_method": None,
                "confidence_level": "high",
                "match_score": 92.0,
            },
            source="crossref",
            progress=["PDF analyzed", "CrossRef matched"],
        ),
        merge_metadata=lambda *items: next(
            (
                dict(item)
                for item in items
                if item and item.get("title") == "Matched title"
            ),
            {},
        ),
        cleanup_temp=lambda path: None,
    )
    monkeypatch.setattr(metadata, "upload_service", fake_service)

    response = auth_client.post(
        "/upload/extract_metadata",
        data={
            "source_type": "file",
            "document_file": (BytesIO(b"pdf"), "matched.pdf"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["crossref_found"] is True
    assert payload["extraction_method"] == "pdf_analysis"
    assert payload["metadata"]["title"] == "Matched title"
    assert payload["progress"] == ["PDF analyzed", "CrossRef matched"]
    assert payload["provenance"]["doi"]["confidence"] == 0.85


def test_file_metadata_falls_back_to_user_title_lookup(
    auth_client, tmp_path, monkeypatch
):
    from app.routes.upload import metadata

    temp_file = tmp_path / "fallback.pdf"
    temp_file.write_bytes(b"pdf")

    def merge_metadata(*items):
        merged = {}
        for item in items:
            for key, value in item.items():
                if value is not None and key not in merged:
                    merged[key] = value
        return merged

    fake_service = SimpleNamespace(
        save_to_temp=lambda file: SimpleNamespace(
            success=True,
            temp_path=str(temp_file),
            error=None,
        ),
        extract_metadata_from_pdf=lambda path: SimpleNamespace(
            success=False,
            metadata={},
            source="pdf_analysis",
            progress=["No identifier found"],
        ),
        extract_metadata_from_title=lambda title: SimpleNamespace(
            success=True,
            metadata={"title": "CrossRef title", "match_score": 88.0},
            error=None,
        ),
        merge_metadata=merge_metadata,
        cleanup_temp=lambda path: None,
    )
    monkeypatch.setattr(metadata, "upload_service", fake_service)

    response = auth_client.post(
        "/upload/extract_metadata",
        data={
            "source_type": "file",
            "document_file": (BytesIO(b"pdf"), "fallback.pdf"),
            "title": "User supplied title",
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["crossref_found"] is True
    assert payload["extraction_method"] == "title_from_user"
    assert payload["metadata"]["title"] == "CrossRef title"
    assert "your provided title" in payload["message"]


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
