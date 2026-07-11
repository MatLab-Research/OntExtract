"""Regression coverage for modular provenance routes."""

import uuid


def test_provenance_routes_are_grouped_by_responsibility(app):
    expected_modules = {
        "provenance.provenance_graph": (
            "app.routes.provenance_visualization.graphs"
        ),
        "provenance.provenance_graph_compact": (
            "app.routes.provenance_visualization.graphs"
        ),
        "provenance.provenance_graph_simple": (
            "app.routes.provenance_visualization.graphs"
        ),
        "provenance.timeline": "app.routes.provenance_visualization.timeline",
        "provenance.experiment_timeline": (
            "app.routes.provenance_visualization.timeline"
        ),
        "provenance.api_timeline": "app.routes.provenance_visualization.api",
        "provenance.api_graph": "app.routes.provenance_visualization.api",
        "provenance.entity_lineage": (
            "app.routes.provenance_visualization.lineage"
        ),
        "provenance.delete_activity": (
            "app.routes.provenance_visualization.admin"
        ),
        "provenance.delete_all_provenance": (
            "app.routes.provenance_visualization.admin"
        ),
    }

    actual_modules = {
        endpoint: app.view_functions[endpoint].__module__
        for endpoint in expected_modules
    }

    assert actual_modules == expected_modules


def test_provenance_graph_variants_render(client, auth_client):
    assert auth_client.get("/provenance/graph").status_code == 200
    assert auth_client.get("/provenance/graph/compact").status_code == 200
    assert auth_client.get("/provenance/graph/simple").status_code == 200


def test_provenance_api_routes_forward_filters(
    auth_client, monkeypatch
):
    from app.routes.provenance_visualization import api

    monkeypatch.setattr(
        api.ProvenanceVisualizationService,
        "timeline_data",
        lambda args, actor_id: {
            "success": True,
            "timeline": [{"id": "activity-1"}],
            "count": 1,
        },
    )
    monkeypatch.setattr(
        api.ProvenanceVisualizationService,
        "graph_data",
        lambda args, actor_id: {
            "success": True,
            "nodes": [],
            "edges": [],
            "stats": {"activities": 0},
        },
    )

    timeline_response = auth_client.get(
        "/provenance/api/timeline?experiment_id=7&activity_type=tool_execution&limit=12"
    )
    graph_response = auth_client.get(
        "/provenance/api/graph?experiment_id=7&document_id=9&term_id=term-1&limit=8"
    )

    assert timeline_response.status_code == 200
    assert timeline_response.get_json()["count"] == 1
    assert graph_response.status_code == 200
    assert graph_response.get_json()["success"] is True


def test_lineage_rejects_invalid_uuid(auth_client):
    response = auth_client.get("/provenance/entity/not-a-uuid/lineage")

    assert response.status_code == 400


def test_provenance_deletion_requires_admin(auth_client):
    activity_id = uuid.uuid4()

    activity_response = auth_client.delete(
        f"/provenance/activity/{activity_id}"
    )
    all_response = auth_client.delete("/provenance/delete-all")

    assert activity_response.status_code == 403
    assert activity_response.get_json()["error"] == "Admin access required"
    assert all_response.status_code == 403
    assert all_response.get_json()["error"] == "Admin access required"


def test_admin_invalid_activity_id_is_rejected(admin_client):
    response = admin_client.delete("/provenance/activity/not-a-uuid")

    assert response.status_code == 400
    assert response.get_json()["error"] == "Invalid activity ID"
