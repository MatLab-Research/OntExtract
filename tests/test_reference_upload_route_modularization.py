"""Regression coverage for modular reference-upload routes."""

from io import BytesIO
from types import SimpleNamespace


def test_reference_upload_routes_are_grouped_by_responsibility(app):
    expected_modules = {
        "references.upload": "app.routes.references.upload.files",
        "references.parse_oed_pdf": "app.routes.references.upload.oed_pdf",
        "references.upload_dictionary": "app.routes.references.upload.dictionary",
        "references.extract_metadata": "app.routes.references.upload.metadata",
    }

    actual_modules = {
        endpoint: app.view_functions[endpoint].__module__
        for endpoint in expected_modules
    }

    assert actual_modules == expected_modules


def test_reference_upload_page_variants_render(auth_client):
    assert auth_client.get("/references/upload").status_code == 200
    assert auth_client.get("/references/upload?tabbed=false").status_code == 200


def test_reference_upload_endpoints_validate_missing_inputs(auth_client):
    assert auth_client.post("/references/upload").status_code == 302
    assert auth_client.post("/references/parse_oed_pdf").status_code == 400
    assert auth_client.post("/references/extract_metadata").status_code == 400
    assert auth_client.post("/references/upload_dictionary").status_code == 302


def test_general_reference_upload_creates_document(
    app, auth_client, test_user, tmp_path, monkeypatch
):
    from app.models.document import Document
    from app.routes.references.upload import files

    class FakeTextProcessingService:
        def process_document(self, document):
            return document

    monkeypatch.setitem(app.config, "UPLOAD_FOLDER", str(tmp_path))
    monkeypatch.setitem(app.config, "PREFILL_METADATA", False)
    monkeypatch.setattr(
        files,
        "TextProcessingService",
        FakeTextProcessingService,
    )

    response = auth_client.post(
        "/references/upload",
        data={
            "file": (BytesIO(b"reference contents"), "reference.txt"),
            "title": "Uploaded Reference",
            "reference_subtype": "academic",
            "authors": "Ada Lovelace, Alan Turing",
            "doi": "10.1000/example",
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 302
    document = Document.query.filter_by(title="Uploaded Reference").one()
    assert response.headers["Location"].endswith(f"/references/{document.id}")
    assert document.user_id == test_user.id
    assert document.document_type == "reference"
    assert document.original_filename == "reference.txt"
    assert document.source_metadata["authors"] == [
        "Ada Lovelace",
        "Alan Turing",
    ]
    assert document.source_metadata["doi"] == "10.1000/example"
    assert tmp_path.joinpath("reference.txt").exists()


def test_oed_pdf_parser_returns_mocked_result(
    auth_client, monkeypatch
):
    from app.services import oed_parser_final

    class FakeOEDParser:
        def parse_pdf(self, path):
            return {"headword": "agency", "source_path": path}

    monkeypatch.setattr(oed_parser_final, "OEDParser", FakeOEDParser)

    response = auth_client.post(
        "/references/parse_oed_pdf",
        data={"file": (BytesIO(b"mock pdf"), "agency.pdf")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["data"]["headword"] == "agency"


def test_dictionary_upload_sanitizes_nul_characters(
    auth_client, test_user
):
    from app.models.document import Document

    response = auth_client.post(
        "/references/upload_dictionary",
        data={
            "title": "agency\x00",
            "content": "The capacity to act.\x00",
            "reference_subtype": "dictionary_general",
            "journal": "Example Dictionary\x00",
            "context": "philosophy\x00",
            "synonyms": "action, capacity\x00",
        },
    )

    assert response.status_code == 302
    document = Document.query.filter_by(title="agency").one()
    assert response.headers["Location"].endswith(f"/references/{document.id}")
    assert document.user_id == test_user.id
    assert "\x00" not in document.content
    assert document.source_metadata == {
        "journal": "Example Dictionary",
        "context": "philosophy",
        "synonyms": "action, capacity",
    }


def test_metadata_extraction_uses_service_and_removes_temp_file(
    auth_client, tmp_path, monkeypatch
):
    from app.services.upload_service import upload_service

    temp_file = tmp_path / "metadata.pdf"
    temp_file.write_bytes(b"temporary pdf")

    monkeypatch.setattr(
        upload_service,
        "save_to_temp",
        lambda file: SimpleNamespace(
            success=True,
            temp_path=str(temp_file),
            error=None,
        ),
    )
    monkeypatch.setattr(
        upload_service,
        "extract_metadata_from_pdf",
        lambda path: SimpleNamespace(
            success=True,
            metadata={"title": "Extracted title"},
            progress=["PDF analyzed"],
            source="file_analysis",
            error=None,
        ),
    )

    response = auth_client.post(
        "/references/extract_metadata",
        data={"file": (BytesIO(b"mock pdf"), "metadata.pdf")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "success": True,
        "metadata": {"title": "Extracted title"},
        "progress": ["PDF analyzed"],
        "source": "file_analysis",
    }
    assert not temp_file.exists()
