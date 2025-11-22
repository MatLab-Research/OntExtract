"""
OntServe Client for Semantic Change Ontology

High-level ontology operations using MCP integration layer.
Provides domain-specific methods for semantic change event types,
SPARQL queries, and ontology validation.
"""

import logging
from typing import List, Dict, Any, Optional
from functools import lru_cache
from .mcp_client import get_mcp_client, MCPClientError

logger = logging.getLogger(__name__)


class OntServeClient:
    """
    Client for OntServe ontology operations.

    Provides high-level interface to semantic change ontology:
    - Fetch event types with metadata
    - Execute SPARQL queries
    - Validate URIs
    - Get property definitions
    """

    def __init__(self):
        """Initialize OntServe client with MCP integration."""
        self.mcp_client = get_mcp_client()
        self.namespace = "http://ontextract.org/sco#"
        self.ontology_name = "semantic-change-ontology"

        logger.info("OntServe client initialized for semantic change ontology")

    @lru_cache(maxsize=1)
    def get_event_types(self) -> List[Dict[str, Any]]:
        """
        Fetch semantic event types from SCO ontology.

        Returns synchronous result by running async code.
        Cached for application lifetime.

        Returns:
            List of event types with:
            - uri: Full ontology URI
            - name: Class name (e.g., "InflectionPoint")
            - label: Human-readable label
            - description: Event type description
            - color: UI color code
            - icon: FontAwesome icon class
            - examples: List of example annotations

        Raises:
            MCPClientError: If ontology query fails
        """
        import asyncio

        # Run async query synchronously
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self._fetch_event_types())

    async def _fetch_event_types(self) -> List[Dict[str, Any]]:
        """
        Async implementation of event type fetching.

        Returns:
            List of event type dictionaries
        """
        # SPARQL query to get all semantic event types
        sparql = f"""
        PREFIX sco: <{self.namespace}>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

        SELECT ?eventType ?label ?comment
               (GROUP_CONCAT(DISTINCT ?example; separator="|||") as ?examples)
        WHERE {{
            ?eventType rdfs:subClassOf* sco:SemanticChangeEvent .
            ?eventType rdfs:label ?label .
            OPTIONAL {{ ?eventType rdfs:comment ?comment }}
            OPTIONAL {{ ?eventType skos:example ?example }}
            FILTER(?eventType != sco:SemanticChangeEvent)
        }}
        GROUP BY ?eventType ?label ?comment
        ORDER BY ?label
        """

        try:
            result = await self.mcp_client.call_mcp("sparql_query", {
                "ontology": self.ontology_name,
                "query": sparql
            })

            # Transform SPARQL results to UI format
            event_types = []
            bindings = result.get("results", {}).get("bindings", [])

            for binding in bindings:
                uri = binding["eventType"]["value"]
                event_name = uri.split("#")[-1]

                # Split examples if present
                examples_str = binding.get("examples", {}).get("value", "")
                examples = [ex.strip() for ex in examples_str.split("|||") if ex.strip()]

                event_types.append({
                    "uri": uri,
                    "name": event_name,
                    "label": binding["label"]["value"],
                    "description": binding.get("comment", {}).get("value", ""),
                    "color": self._get_color_for_type(event_name),
                    "icon": self._get_icon_for_type(event_name),
                    "examples": examples
                })

            logger.info(f"Fetched {len(event_types)} semantic event types from ontology")
            return event_types

        except MCPClientError as e:
            logger.error(f"Failed to fetch event types: {e}")
            # Return hardcoded fallback
            return self._get_fallback_event_types()

    def _get_fallback_event_types(self) -> List[Dict[str, Any]]:
        """
        Fallback event types if ontology query fails.

        Returns:
            Hardcoded list of event types
        """
        logger.warning("Using fallback event types (ontology unavailable)")

        return [
            {
                "uri": f"{self.namespace}InflectionPoint",
                "name": "InflectionPoint",
                "label": "Inflection Point",
                "description": "Rapid semantic transition marking shift between distinct meanings",
                "color": "#6f42c1",
                "icon": "fas fa-turn-up",
                "examples": []
            },
            {
                "uri": f"{self.namespace}StablePolysemy",
                "name": "StablePolysemy",
                "label": "Stable Polysemy",
                "description": "Multiple distinct meanings coexist without conflict",
                "color": "#20c997",
                "icon": "fas fa-code-branch",
                "examples": []
            },
            {
                "uri": f"{self.namespace}DomainNetwork",
                "name": "DomainNetwork",
                "label": "Domain Network",
                "description": "Domain-specific semantic network develops",
                "color": "#fd7e14",
                "icon": "fas fa-project-diagram",
                "examples": []
            },
            {
                "uri": f"{self.namespace}ConceptualBridge",
                "name": "ConceptualBridge",
                "label": "Conceptual Bridge",
                "description": "Work mediates between different meanings",
                "color": "#17a2b8",
                "icon": "fas fa-link",
                "examples": []
            },
            {
                "uri": f"{self.namespace}SemanticDrift",
                "name": "SemanticDrift",
                "label": "Semantic Drift",
                "description": "Gradual meaning change over extended period",
                "color": "#d63384",
                "icon": "fas fa-water",
                "examples": []
            },
            {
                "uri": f"{self.namespace}Emergence",
                "name": "Emergence",
                "label": "Emergence",
                "description": "New meaning appears in discourse",
                "color": "#198754",
                "icon": "fas fa-seedling",
                "examples": []
            },
            {
                "uri": f"{self.namespace}Decline",
                "name": "Decline",
                "label": "Decline",
                "description": "Meaning becomes obsolete or rare",
                "color": "#dc3545",
                "icon": "fas fa-arrow-trend-down",
                "examples": []
            }
        ]

    def validate_event_uri(self, uri: str) -> bool:
        """
        Validate that URI exists in SCO ontology.

        Args:
            uri: Event type URI to validate

        Returns:
            True if URI is valid, False otherwise
        """
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self._validate_event_uri_async(uri))

    async def _validate_event_uri_async(self, uri: str) -> bool:
        """
        Async implementation of URI validation.

        Args:
            uri: Event type URI

        Returns:
            True if valid
        """
        # SPARQL query to check if URI exists as a class
        sparql = f"""
        PREFIX sco: <{self.namespace}>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        ASK {{
            <{uri}> rdfs:subClassOf* sco:SemanticChangeEvent .
        }}
        """

        try:
            result = await self.mcp_client.call_mcp("sparql_query", {
                "ontology": self.ontology_name,
                "query": sparql
            })

            return result.get("boolean", False)

        except MCPClientError as e:
            logger.error(f"URI validation failed: {e}")
            # Fallback: check if URI matches known pattern
            return uri.startswith(self.namespace)

    def get_properties(self) -> List[Dict[str, Any]]:
        """
        Get all SCO properties (object and datatype).

        Returns:
            List of property dictionaries
        """
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self._fetch_properties())

    async def _fetch_properties(self) -> List[Dict[str, Any]]:
        """
        Async implementation of property fetching.

        Returns:
            List of properties with metadata
        """
        sparql = f"""
        PREFIX sco: <{self.namespace}>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>

        SELECT ?property ?label ?type ?comment ?domain ?range
        WHERE {{
            VALUES ?type {{ owl:ObjectProperty owl:DatatypeProperty }}
            ?property a ?type .
            ?property rdfs:label ?label .
            OPTIONAL {{ ?property rdfs:comment ?comment }}
            OPTIONAL {{ ?property rdfs:domain ?domain }}
            OPTIONAL {{ ?property rdfs:range ?range }}
            FILTER(STRSTARTS(STR(?property), "{self.namespace}"))
        }}
        ORDER BY ?type ?label
        """

        try:
            result = await self.mcp_client.call_mcp("sparql_query", {
                "ontology": self.ontology_name,
                "query": sparql
            })

            properties = []
            bindings = result.get("results", {}).get("bindings", [])

            for binding in bindings:
                uri = binding["property"]["value"]
                prop_name = uri.split("#")[-1]
                prop_type = binding["type"]["value"].split("#")[-1]

                properties.append({
                    "uri": uri,
                    "name": prop_name,
                    "label": binding["label"]["value"],
                    "type": prop_type,
                    "comment": binding.get("comment", {}).get("value", ""),
                    "domain": binding.get("domain", {}).get("value"),
                    "range": binding.get("range", {}).get("value")
                })

            logger.info(f"Fetched {len(properties)} properties from ontology")
            return properties

        except MCPClientError as e:
            logger.error(f"Failed to fetch properties: {e}")
            return []

    def _get_color_for_type(self, event_name: str) -> str:
        """
        Map event type to UI color.

        Args:
            event_name: Event class name

        Returns:
            Hex color code
        """
        colors = {
            "InflectionPoint": "#6f42c1",
            "StablePolysemy": "#20c997",
            "DomainNetwork": "#fd7e14",
            "ConceptualBridge": "#17a2b8",
            "SemanticDrift": "#d63384",
            "Emergence": "#198754",
            "Decline": "#dc3545"
        }
        return colors.get(event_name, "#6c757d")

    def _get_icon_for_type(self, event_name: str) -> str:
        """
        Map event type to FontAwesome icon.

        Args:
            event_name: Event class name

        Returns:
            FontAwesome class string
        """
        icons = {
            "InflectionPoint": "fas fa-turn-up",
            "StablePolysemy": "fas fa-code-branch",
            "DomainNetwork": "fas fa-project-diagram",
            "ConceptualBridge": "fas fa-link",
            "SemanticDrift": "fas fa-water",
            "Emergence": "fas fa-seedling",
            "Decline": "fas fa-arrow-trend-down"
        }
        return icons.get(event_name, "fas fa-circle")


# Global OntServe client instance
_global_ontserve_client: Optional[OntServeClient] = None


def get_ontserve_client() -> OntServeClient:
    """
    Get global OntServe client instance.

    Returns:
        Singleton OntServeClient instance
    """
    global _global_ontserve_client
    if _global_ontserve_client is None:
        _global_ontserve_client = OntServeClient()
    return _global_ontserve_client
