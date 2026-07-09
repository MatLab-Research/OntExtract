"""Deterministic tests for the OntServe domain client."""

import os
from unittest.mock import AsyncMock

import pytest

from app.services.mcp_client import MCPClientError
from app.services.ontserve_client import OntServeClient


def test_event_types_are_mapped_from_sparql_bindings():
    client = OntServeClient()
    client.mcp_client = AsyncMock()
    client.mcp_client.call_mcp.return_value = {
        "results": {
            "bindings": [{
                "eventType": {"value": f"{client.namespace}SemanticDrift"},
                "label": {"value": "Semantic Drift"},
                "comment": {"value": "Gradual meaning change"},
                "examples": {"value": "Example one|||Example two"},
            }]
        }
    }

    assert client.get_event_types() == [{
        "uri": f"{client.namespace}SemanticDrift",
        "name": "SemanticDrift",
        "label": "Semantic Drift",
        "description": "Gradual meaning change",
        "color": "#d63384",
        "icon": "fas fa-water",
        "examples": ["Example one", "Example two"],
    }]


def test_properties_are_mapped_from_sparql_bindings():
    client = OntServeClient()
    client.mcp_client = AsyncMock()
    client.mcp_client.call_mcp.return_value = {
        "results": {
            "bindings": [{
                "property": {"value": f"{client.namespace}hasEvidence"},
                "label": {"value": "has evidence"},
                "type": {"value": "http://www.w3.org/2002/07/owl#ObjectProperty"},
                "comment": {"value": "Links an event to evidence"},
                "domain": {"value": f"{client.namespace}SemanticChangeEvent"},
            }]
        }
    }

    assert client.get_properties() == [{
        "uri": f"{client.namespace}hasEvidence",
        "name": "hasEvidence",
        "label": "has evidence",
        "type": "ObjectProperty",
        "comment": "Links an event to evidence",
        "domain": f"{client.namespace}SemanticChangeEvent",
        "range": None,
    }]


@pytest.mark.parametrize(
    ("event_name", "expected"),
    [("InflectionPoint", True), ("InvalidEvent", False)],
)
def test_uri_validation_fallback_only_accepts_known_events(event_name, expected):
    client = OntServeClient()
    client.mcp_client = AsyncMock()
    client.mcp_client.call_mcp.side_effect = MCPClientError("OntServe unavailable")

    assert client.validate_event_uri(f"{client.namespace}{event_name}") is expected


@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv("RUN_ONTSERVE_INTEGRATION") != "1",
    reason="Set RUN_ONTSERVE_INTEGRATION=1 to query a live OntServe instance",
)
def test_live_ontserve_client():
    client = OntServeClient()

    assert client.get_event_types()
    assert client.get_properties()
