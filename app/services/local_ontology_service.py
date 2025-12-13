"""
Local ontology metadata service for JCDL demo.

Reads semantic-change-ontology-v2.ttl directly from disk using rdflib.
No runtime dependency on OntServe.

Post-conference: Replace with OntServeClient for full integration.
"""
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class SemanticChangeEventType:
    """Event type metadata from ontology"""
    uri: str
    label: str
    definition: str
    example: Optional[str] = None
    citation: Optional[str] = None
    parent_class: Optional[str] = None

class LocalOntologyService:
    """
    Parse semantic change ontology from local .ttl file.

    This provides the same interface as OntServeClient would,
    but reads directly from file instead of querying MCP server.
    """

    def __init__(self, ontology_path: Optional[Path] = None):
        """
        Initialize service with ontology file path.

        Args:
            ontology_path: Path to .ttl file. If None, uses default.
        """
        if ontology_path is None:
            # Default: ontologies/semantic-change-ontology-v2.ttl
            base_dir = Path(__file__).parent.parent.parent
            ontology_path = base_dir / 'ontologies' / 'semantic-change-ontology-v2.ttl'

        self.ontology_path = ontology_path
        self.graph = None
        self._event_types_cache = None

        # Lazy load on first access

    def _load_ontology(self):
        """Load ontology with rdflib (lazy initialization)"""
        if self.graph is not None:
            return

        try:
            from rdflib import Graph
            self.graph = Graph()

            logger.info(f"Loading ontology from {self.ontology_path}")
            self.graph.parse(str(self.ontology_path), format='turtle')
            logger.info(f"Loaded ontology: {len(self.graph)} triples")

        except ImportError:
            logger.error("rdflib not installed. Install with: pip install rdflib")
            raise
        except Exception as e:
            logger.error(f"Failed to load ontology: {e}")
            raise

    def get_semantic_change_event_types(self) -> List[SemanticChangeEventType]:
        """
        Get all semantic change event types from ontology.

        Returns cached results after first call for performance.

        Returns:
            List of event types with metadata
        """
        if self._event_types_cache is not None:
            return self._event_types_cache

        self._load_ontology()

        # SPARQL query to get event types
        # Use GROUP BY to avoid duplicates when classes have multiple examples
        query = """
        PREFIX sco: <http://ontextract.org/sco#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        PREFIX dcterms: <http://purl.org/dc/terms/>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>

        SELECT ?uri ?label ?definition (SAMPLE(?ex) AS ?example) (SAMPLE(?cit) AS ?citation) ?parent
        WHERE {
            ?uri a owl:Class ;
                 rdfs:subClassOf ?parent ;
                 rdfs:label ?label ;
                 skos:definition ?definition .

            # Only get direct subclasses of SemanticChangeEvent
            FILTER(?parent = sco:SemanticChangeEvent)

            OPTIONAL { ?uri skos:example ?ex }
            OPTIONAL { ?uri dcterms:bibliographicCitation ?cit }
        }
        GROUP BY ?uri ?label ?definition ?parent
        ORDER BY ?label
        """

        results = self.graph.query(query)

        event_types = []
        for row in results:
            event_types.append(SemanticChangeEventType(
                uri=str(row.uri),
                label=str(row.label),
                definition=str(row.definition),
                example=str(row.example) if row.example else None,
                citation=str(row.citation) if row.citation else None,
                parent_class=str(row.parent) if row.parent else None
            ))

        # Cache results
        self._event_types_cache = event_types

        logger.info(f"Loaded {len(event_types)} semantic change event types from ontology")
        return event_types

    def get_event_type_by_label(self, label: str) -> Optional[SemanticChangeEventType]:
        """
        Get event type by label (case-insensitive).

        Args:
            label: Event type label (e.g., "Pejoration")

        Returns:
            Event type metadata or None if not found
        """
        event_types = self.get_semantic_change_event_types()

        label_lower = label.lower()
        for et in event_types:
            if et.label.lower() == label_lower:
                return et

        return None

    def get_all_for_dropdown(self) -> List[Dict]:
        """
        Get event types formatted for UI dropdown.

        Returns:
            List of dicts with {value, label, definition, citation}
        """
        event_types = self.get_semantic_change_event_types()

        return [
            {
                'value': et.label.lower().replace(' ', '_'),  # "Pejoration" -> "pejoration"
                'label': et.label,
                'definition': et.definition,
                'example': et.example,
                'citation': et.citation,
                'uri': et.uri  # Include for future OntServe migration
            }
            for et in event_types
        ]


# Singleton instance
_ontology_service = None

def get_ontology_service() -> LocalOntologyService:
    """Get singleton ontology service instance"""
    global _ontology_service
    if _ontology_service is None:
        _ontology_service = LocalOntologyService()
    return _ontology_service
