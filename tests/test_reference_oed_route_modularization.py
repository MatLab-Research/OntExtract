"""Regression coverage for modular OED reference routes."""


def test_oed_routes_are_grouped_by_responsibility(app):
    expected_modules = {
        "references.api_oed_entry": "app.routes.references.oed.api",
        "references.api_oed_word": "app.routes.references.oed.api",
        "references.api_oed_word_quotations": "app.routes.references.oed.api",
        "references.api_oed_suggest": "app.routes.references.oed.api",
        "references.api_oed_variants": "app.routes.references.oed.api",
        "references.new_oed_reference": "app.routes.references.oed.pages",
        "references.add_oed_reference": "app.routes.references.oed.creation",
        "references.add_oed_references_batch": "app.routes.references.oed.creation",
        "references.split_oed_reference": "app.routes.references.oed.splitting",
    }

    actual_modules = {
        endpoint: app.view_functions[endpoint].__module__
        for endpoint in expected_modules
    }

    assert actual_modules == expected_modules


def test_oed_api_validates_required_query_parameters(auth_client):
    assert auth_client.get("/references/api/oed/entry").status_code == 400
    assert auth_client.get("/references/api/oed/suggest").status_code == 400
    assert auth_client.get("/references/api/oed/variants").status_code == 400
    assert auth_client.get(
        "/references/api/oed/word/example/quotations?limit=invalid"
    ).status_code == 400


def test_new_oed_reference_page_renders(auth_client):
    response = auth_client.get("/references/oed/new?experiment_id=42")

    assert response.status_code == 200
    assert b'experiment_id' in response.data


def test_oed_api_routes_forward_to_service(auth_client, monkeypatch):
    from app.routes.references.oed import api

    class FakeOEDService:
        def get_entry(self, headword):
            return {"success": True, "headword": headword}

        def get_word(self, entry_id):
            return {"success": True, "entry_id": entry_id}

        def get_quotations(self, entry_id, *, limit=None, offset=None):
            return {
                "success": True,
                "entry_id": entry_id,
                "limit": limit,
                "offset": offset,
            }

        def suggest_ids(self, headword):
            return {"success": True, "headword": headword}

        def get_variants(self, headword):
            return {"success": True, "headword": headword}

    monkeypatch.setattr(api, "OEDService", FakeOEDService)

    entry = auth_client.get("/references/api/oed/entry?q=agency")
    word = auth_client.get("/references/api/oed/word/agency_nn01")
    quotations = auth_client.get(
        "/references/api/oed/word/agency_nn01/quotations?limit=5&offset=2"
    )
    suggestions = auth_client.get("/references/api/oed/suggest?q=agency")
    variants = auth_client.get("/references/api/oed/variants?q=agency")

    assert entry.get_json()["headword"] == "agency"
    assert word.get_json()["entry_id"] == "agency_nn01"
    assert quotations.get_json() == {
        "success": True,
        "entry_id": "agency_nn01",
        "limit": 5,
        "offset": 2,
    }
    assert suggestions.get_json()["headword"] == "agency"
    assert variants.get_json()["headword"] == "agency"


def test_add_oed_reference_creates_document(
    auth_client, test_user, monkeypatch
):
    from app.models.document import Document
    from app.routes.references.oed import creation

    class FakeOEDService:
        def get_word(self, entry_id):
            return {
                "success": True,
                "data": {
                    "headword": "agency",
                    "part_of_speech": "noun",
                    "extracted_senses": [
                        {
                            "sense_id": "sense-1",
                            "label": "capacity",
                            "definition": "The capacity to act independently.",
                        }
                    ],
                },
            }

    monkeypatch.setattr(creation, "OEDService", FakeOEDService)

    response = auth_client.post(
        "/references/oed/add",
        data={
            "entry_id": "agency_nn01",
            "sense_id": "sense-1",
            "title": "OED Agency",
        },
    )

    assert response.status_code == 302
    document = Document.query.filter_by(title="OED Agency").one()
    assert response.headers["Location"].endswith(f"/references/{document.id}")
    assert document.user_id == test_user.id
    assert document.document_type == "reference"
    assert document.reference_subtype == "dictionary_oed"
    assert document.source_metadata["oed_entry_id"] == "agency_nn01"
    assert document.source_metadata["selected_senses"] == [
        {
            "sense_id": "sense-1",
            "label": "capacity",
            "definition": "The capacity to act independently.",
        }
    ]


def test_oed_builder_returns_unsaved_document(test_user, monkeypatch):
    from app import db
    from app.routes.references.oed import builder

    class FakeOEDService:
        def get_word(self, entry_id):
            return {
                "success": True,
                "data": {
                    "headword": "agent",
                    "pos": "noun",
                    "extracted_senses": [
                        {
                            "sense_id": "sense-a",
                            "label": "actor",
                            "definition": (
                                "A person or thing that takes an active role."
                            ),
                        }
                    ],
                },
            }

    monkeypatch.setattr(builder, "OEDService", FakeOEDService)

    document, error = builder._build_oed_reference(
        "agent_nn01",
        test_user.id,
        selected_sense_ids=["sense-a"],
        title_override="OED Agent",
    )

    assert error is None
    assert document.id is None
    assert document not in db.session.new
    assert document.title == "OED Agent"
    assert document.source_metadata["selected_senses"][0]["sense_id"] == (
        "sense-a"
    )


def test_split_oed_reference_creates_each_sense_once(
    auth_client, db_session, test_user
):
    from app.models.document import Document

    parent = Document(
        title="OED: agency",
        content_type="text",
        document_type="reference",
        reference_subtype="dictionary_oed",
        content="OED entry: agency_nn01\nHeadword: agency",
        source_metadata={
            "oed_entry_id": "agency_nn01",
            "headword": "agency",
            "part_of_speech": "noun",
            "selected_senses": [
                {
                    "sense_id": "sense-1",
                    "label": "capacity",
                    "definition": "The capacity to act.",
                },
                {
                    "sense_id": "sense-2",
                    "label": "organization",
                    "definition": "An organization acting for another.",
                },
            ],
        },
        user_id=test_user.id,
        status="completed",
    )
    db_session.add(parent)
    db_session.commit()

    first_response = auth_client.post(f"/references/oed/split/{parent.id}")
    assert first_response.status_code == 302
    assert parent.children.count() == 2

    second_response = auth_client.post(f"/references/oed/split/{parent.id}")
    assert second_response.status_code == 302
    assert parent.children.count() == 2
