"""SPARQL request contract tests for OntServe."""

from unittest.mock import AsyncMock

from app.services.ontserve_client import OntServeClient


def test_event_type_query_targets_the_semantic_change_ontology():
    client = OntServeClient()
    client.mcp_client = AsyncMock()
    client.mcp_client.call_mcp.return_value = {"results": {"bindings": []}}

    client.get_event_types()

    method, payload = client.mcp_client.call_mcp.call_args.args
    assert method == "sparql_query"
    assert payload["ontology"] == "semantic-change-ontology"
    assert "sco:SemanticChangeEvent" in payload["query"]
    assert "GROUP_CONCAT" in payload["query"]


def test_property_query_requests_object_and_datatype_properties():
    client = OntServeClient()
    client.mcp_client = AsyncMock()
    client.mcp_client.call_mcp.return_value = {"results": {"bindings": []}}

    client.get_properties()

    method, payload = client.mcp_client.call_mcp.call_args.args
    assert method == "sparql_query"
    assert "owl:ObjectProperty" in payload["query"]
    assert "owl:DatatypeProperty" in payload["query"]
