"""Smoke test for the /api/documents/<id>/methods endpoint.

This test assumes a running server and authenticated session is not strictly
enforced or a test user is logged in via client fixture. If authentication is
required, the test will be skipped gracefully.
"""

import os
import pytest

from app import create_app, db
from app.models.document import Document
from app.models.user import User


@pytest.fixture(scope="module")
def test_app():
    os.environ.setdefault("FLASK_ENV", "development")
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": os.environ.get(
            "ONTEXTRACT_DB_URL",
            "postgresql://postgres:PASS@localhost:5432/ontextract_db",
        ),
        "WTF_CSRF_ENABLED": False,
        "LOGIN_DISABLED": False,
    })
    with app.app_context():
        yield app


@pytest.fixture()
def client(test_app):
    return test_app.test_client()


@pytest.fixture()
def auth_user(test_app):
    with test_app.app_context():
        user = User.query.filter_by(username="methods_tester").first()
        if not user:
            user = User(
                username="methods_tester",
                email="methods_tester@example.com",
                password="password",
                is_admin=True,
            )
            db.session.add(user)
            db.session.commit()
        return user.id


def login(client, username, password):
    return client.post(
        "/auth/login",
        data={"username": username, "password": password},
        follow_redirects=True,
    )


def test_methods_endpoint_smoke(client, auth_user, test_app):
    # Log in
    rv = login(client, "methods_tester", "password")
    assert rv.status_code in (200, 302)

    # Ensure a document exists
    with test_app.app_context():
        doc = Document.query.filter_by(title="[TEST] Methods Doc").first()
        if not doc:
            doc = Document(
                title="[TEST] Methods Doc",
                content="Simple test content.\nSecond paragraph.",
                content_type="text",
                user_id=auth_user,
                word_count=5,
                character_count=40,
                status="completed",
            )
            db.session.add(doc)
            db.session.commit()
        doc_id = doc.id

    # Call endpoint
    resp = client.get(f"/api/documents/{doc_id}/methods")
    assert resp.status_code == 200, resp.data
    data = resp.get_json()
    assert data["success"] is True
    assert data["document_id"] == doc_id
    assert "groups" in data
    # Initial call may return empty groups (no segmentation yet) but should include list
    assert isinstance(data["groups"], list)
