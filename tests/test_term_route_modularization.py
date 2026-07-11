"""Regression coverage for modular term CRUD routes."""


def test_term_crud_routes_are_grouped_by_responsibility(app):
    expected_modules = {
        "terms.term_index": "app.routes.terms.crud.pages",
        "terms.view_term": "app.routes.terms.crud.pages",
        "terms.add_term": "app.routes.terms.crud.creation",
        "terms.edit_term": "app.routes.terms.crud.editing",
        "terms.delete_term": "app.routes.terms.crud.deletion",
        "terms.add_version": "app.routes.terms.crud.versions",
    }

    actual_modules = {
        endpoint: app.view_functions[endpoint].__module__
        for endpoint in expected_modules
    }

    assert actual_modules == expected_modules


def test_term_index_and_detail_are_public(client, sample_term):
    assert client.get("/terms/").status_code == 200
    assert client.get(f"/terms/{sample_term.id}").status_code == 200


def test_term_writes_require_authentication(client, sample_term):
    assert client.get("/terms/add").status_code in (302, 401)
    assert client.get(f"/terms/{sample_term.id}/edit").status_code in (302, 401)
    assert client.get(f"/terms/{sample_term.id}/add-version").status_code in (302, 401)
    assert client.post(f"/terms/{sample_term.id}/delete").status_code in (302, 401)


def test_non_admin_cannot_delete_term(auth_client, sample_term):
    response = auth_client.post(f"/terms/{sample_term.id}/delete")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/terms/")


def test_add_version_page_renders(auth_client, sample_term):
    response = auth_client.get(f"/terms/{sample_term.id}/add-version")

    assert response.status_code == 200


def test_add_term_creates_initial_version(
    auth_client, test_user, monkeypatch
):
    from app.models import Term, TermVersion
    from app.routes.terms.crud import creation

    monkeypatch.setattr(
        creation.provenance_service,
        "track_term_creation",
        lambda *args, **kwargs: None,
    )

    response = auth_client.post(
        "/terms/add",
        data={
            "term_text": "computational agency",
            "meaning_description": (
                "The capacity of a computational system to act toward goals."
            ),
            "temporal_period": "2000-present",
            "temporal_start_year": "2000",
            "confidence_level": "high",
            "research_domain": "Artificial Intelligence",
        },
    )

    assert response.status_code == 302
    term = Term.query.filter_by(term_text="computational agency").one()
    assert term.created_by == test_user.id
    assert response.headers["Location"].endswith(f"/terms/{term.id}")

    version = TermVersion.query.filter_by(term_id=term.id).one()
    assert version.version_number == 1
    assert version.is_current is True
    assert version.temporal_period == "2000-present"


def test_owner_can_edit_term(
    auth_client, db_session, test_user, sample_term, monkeypatch
):
    from app.routes.terms.crud import editing

    sample_term.created_by = test_user.id
    db_session.commit()
    monkeypatch.setattr(
        editing.provenance_service,
        "track_term_update",
        lambda *args, **kwargs: None,
    )

    response = auth_client.post(
        f"/terms/{sample_term.id}/edit",
        data={
            "term_text": sample_term.term_text,
            "research_domain": "Algorithm Studies",
            "status": "provisional",
            "notes": "Updated during route modularization testing.",
        },
    )

    assert response.status_code == 302
    db_session.refresh(sample_term)
    assert sample_term.research_domain == "Algorithm Studies"
    assert sample_term.status == "provisional"
    assert sample_term.updated_by == test_user.id


def test_add_version_creates_next_version(
    auth_client, sample_term
):
    from app.models import TermVersion

    response = auth_client.post(
        f"/terms/{sample_term.id}/add-version",
        data={
            "meaning_description": (
                "A later meaning of algorithm used in automated systems."
            ),
            "temporal_period": "2010-present",
            "temporal_start_year": "2010",
            "confidence_level": "medium",
            "is_current": "on",
        },
    )

    assert response.status_code == 302
    version = TermVersion.query.filter_by(term_id=sample_term.id).one()
    assert version.version_number == 1
    assert version.temporal_period == "2010-present"
    assert version.is_current is True


def test_admin_can_delete_term(
    admin_client, sample_term, monkeypatch
):
    from app.models import Term
    from app.routes.terms.crud import deletion

    monkeypatch.setattr(
        deletion.provenance_service,
        "delete_or_invalidate_term_provenance",
        lambda term_id: {"deleted": 0},
    )

    response = admin_client.post(f"/terms/{sample_term.id}/delete")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/terms/")
    assert db_get(Term, sample_term.id) is None


def db_get(model, object_id):
    from app import db

    return db.session.get(model, object_id)
