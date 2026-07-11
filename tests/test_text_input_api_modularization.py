"""Regression coverage for modular document APIs and metadata service."""

from datetime import date


def test_text_input_api_routes_are_grouped_by_responsibility(app):
    expected_modules = {
        "text_input.api_document_content": "app.routes.text_input.api.documents",
        "text_input.api_document_list": "app.routes.text_input.api.documents",
        "text_input.get_document_metadata": "app.routes.text_input.api.metadata",
        "text_input.update_document_metadata": "app.routes.text_input.api.metadata",
    }
    actual_modules = {
        endpoint: app.view_functions[endpoint].__module__
        for endpoint in expected_modules
    }
    assert actual_modules == expected_modules


def test_document_content_and_list_apis(auth_client, sample_document):
    content_response = auth_client.get(
        f"/input/api/document/{sample_document.id}/content"
    )
    list_response = auth_client.get("/input/api/documents?per_page=1")

    assert content_response.status_code == 200
    assert content_response.get_json()["content"] == sample_document.content
    assert list_response.status_code == 200
    assert list_response.get_json()["total"] >= 1
    assert len(list_response.get_json()["documents"]) == 1


def test_metadata_get_uses_root_document(
    auth_client, db_session, sample_document
):
    from app.models.document import Document

    sample_document.authors = "Root Author"
    sample_document.source_metadata = {"conference_location": "Philadelphia"}
    version = Document(
        title="Derived title",
        content="Derived content",
        content_type="text/plain",
        document_type="document",
        status="completed",
        user_id=sample_document.user_id,
        source_document_id=sample_document.id,
        version_number=2,
        version_type="processed",
    )
    db_session.add(version)
    db_session.commit()

    response = auth_client.get(f"/input/document/{version.uuid}/metadata")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["is_version"] is True
    assert payload["root_uuid"] == str(sample_document.uuid)
    assert payload["metadata"]["title"] == sample_document.title
    assert payload["metadata"]["authors"] == "Root Author"
    assert payload["metadata"]["conference_location"] == "Philadelphia"


def test_metadata_update_changes_columns_and_custom_fields(
    auth_client, sample_document, monkeypatch
):
    from app.routes.text_input.api import metadata as metadata_routes

    tracked = []
    monkeypatch.setattr(
        metadata_routes.provenance_service,
        "track_metadata_update",
        lambda document, user, changes: tracked.append(changes),
    )

    response = auth_client.put(
        f"/input/document/{sample_document.uuid}/metadata",
        json={
            "title": "Updated title",
            "authors": "Ada Lovelace",
            "publication_date": "2024-05-01",
            "editor": "Grace Hopper",
            "notes": "Updated notes",
            "conference_location": "Philadelphia",
        },
    )

    assert response.status_code == 200
    assert sample_document.title == "Updated title"
    assert sample_document.authors == "Ada Lovelace"
    assert sample_document.publication_date == date(2024, 5, 1)
    assert sample_document.editor == "Grace Hopper"
    assert sample_document.source_metadata["conference_location"] == "Philadelphia"
    assert tracked and tracked[0]["title"]["new"] == "Updated title"


def test_metadata_update_preserves_existing_clear_semantics(
    auth_client, db_session, sample_document
):
    sample_document.title = "Original title"
    sample_document.journal = "Original journal"
    sample_document.editor = "Original editor"
    sample_document.publication_date = date(2020, 1, 1)
    db_session.commit()

    response = auth_client.put(
        f"/input/document/{sample_document.uuid}/metadata",
        json={
            "title": "",
            "journal": None,
            "editor": "",
            "publication_date": "not-a-date",
        },
    )

    assert response.status_code == 200
    assert sample_document.title == "Original title"
    assert sample_document.journal == "Original journal"
    assert sample_document.editor is None
    assert sample_document.publication_date == date(2020, 1, 1)


def test_metadata_update_requires_owner(
    auth_client, db_session, sample_document, admin_user
):
    sample_document.user_id = admin_user.id
    db_session.commit()

    response = auth_client.put(
        f"/input/document/{sample_document.uuid}/metadata",
        json={"title": "Forbidden update"},
    )

    assert response.status_code == 403
    assert response.get_json()["error"] == "Permission denied"
