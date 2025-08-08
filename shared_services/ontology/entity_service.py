"""
Ontology Entity Service for extracting entities from RDF/TTL ontologies.

This service provides comprehensive ontology processing with support for:
- RDF/TTL parsing and entity extraction
- Dynamic GuidelineConceptType discovery
- Entity relationship mapping
- Ontology caching and validation
"""

import rdflib
from rdflib import Graph, Namespace, RDF, RDFS
import logging
from typing import Dict, List, Any, Optional, Set, Tuple
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class BaseOntologyStore(ABC):
    """Abstract base class for ontology storage backends."""
    
    @abstractmethod
    def get_ontology_content(self, ontology_id: str) -> str:
        """Get ontology content by ID."""
        pass
    
    @abstractmethod
    def list_ontologies(self) -> List[Dict[str, Any]]:
        """List available ontologies."""
        pass

class FileOntologyStore(BaseOntologyStore):
    """File-based ontology storage."""
    
    def __init__(self, ontology_dir: str):
        self.ontology_dir = ontology_dir
        self.ontologies = {}
        self._scan_ontologies()
    
    def _scan_ontologies(self):
        """Scan directory for ontology files."""
        import os
        import glob
        
        if not os.path.exists(self.ontology_dir):
            logger.warning(f"Ontology directory not found: {self.ontology_dir}")
            return
        
        # Look for TTL files
        for file_path in glob.glob(os.path.join(self.ontology_dir, "*.ttl")):
            filename = os.path.basename(file_path)
            ontology_id = filename.replace('.ttl', '')
            
            self.ontologies[ontology_id] = {
                'id': ontology_id,
                'path': file_path,
                'format': 'turtle'
            }
            logger.info(f"Found ontology: {ontology_id} at {file_path}")
    
    def get_ontology_content(self, ontology_id: str) -> str:
        """Get ontology content from file."""
        if ontology_id not in self.ontologies:
            raise ValueError(f"Ontology not found: {ontology_id}")
        
        file_path = self.ontologies[ontology_id]['path']
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            raise ValueError(f"Error reading ontology file {file_path}: {e}")
    
    def list_ontologies(self) -> List[Dict[str, Any]]:
        """List available ontologies."""
        return list(self.ontologies.values())

class DatabaseOntologyStore(BaseOntologyStore):
    """Database-based ontology storage (for integration with existing systems)."""
    
    def __init__(self, db_session=None):
        self.db_session = db_session
    
    def get_ontology_content(self, ontology_id: str) -> str:
        """Get ontology content from database."""
        if not self.db_session:
            raise RuntimeError("Database session not available")
        
        # This would be implemented based on the specific database schema
        # For now, return placeholder
        raise NotImplementedError("Database ontology store not yet implemented")
    
    def list_ontologies(self) -> List[Dict[str, Any]]:
        """List ontologies from database."""
        if not self.db_session:
            return []
        
        # This would be implemented based on the specific database schema
        return []

class OntologyEntityService:
    """
    Service for extracting entities from ontologies stored in various backends.
    """
    
    def __init__(self, ontology_store: BaseOntologyStore = None, ontology_dir: str = None):
        """
        Initialize the ontology entity service.
        
        Args:
            ontology_store: Storage backend for ontologies
            ontology_dir: Directory containing ontology files (for FileOntologyStore)
        """
        if ontology_store:
            self.ontology_store = ontology_store
        elif ontology_dir:
            self.ontology_store = FileOntologyStore(ontology_dir)
        else:
            # Default to looking for ontologies directory
            import os
            default_dir = os.path.join(os.getcwd(), 'ontologies')
            self.ontology_store = FileOntologyStore(default_dir)
        
        # Cache to avoid repeated parsing
        self.ontology_cache = {}
        
        # Define common namespaces
        self.namespaces = {
            "engineering-ethics": Namespace("http://proethica.org/ontology/engineering-ethics#"),
            "intermediate": Namespace("http://proethica.org/ontology/intermediate#"),
            "proethica-intermediate": Namespace("http://proethica.org/ontology/intermediate#"),
            "nspe": Namespace("http://proethica.org/nspe/"),
            "bfo": Namespace("http://purl.obolibrary.org/obo/")
        }
    
    def get_entities(self, ontology_id: str) -> Dict[str, Any]:
        """
        Get entities for a specific ontology.
        
        Args:
            ontology_id: ID of the ontology to process
            
        Returns:
            Dictionary containing entities organized by type
        """
        # Check cache first
        cache_key = f"ontology_{ontology_id}"
        if cache_key in self.ontology_cache:
            logger.info(f"Using cached entities for ontology {ontology_id}")
            return self.ontology_cache[cache_key]
        
        try:
            # Get ontology content
            ontology_content = self.ontology_store.get_ontology_content(ontology_id)
            
            # Extract entities
            entities = self._extract_entities_from_content(ontology_content, ontology_id)
            
            # Cache the results
            self.ontology_cache[cache_key] = entities
            
            return entities
            
        except Exception as e:
            logger.error(f"Error extracting entities from ontology {ontology_id}: {e}")
            return {"entities": {}, "is_mock": False, "error": str(e)}
    
    def _extract_entities_from_content(self, content: str, ontology_id: str) -> Dict[str, Any]:
        """
        Extract entities from ontology content using RDFLib.
        
        Args:
            content: RDF/TTL content of the ontology
            ontology_id: ID of the ontology for logging
            
        Returns:
            Dictionary containing entities organized by type
        """
        # Parse the ontology content into a graph
        g = Graph()
        try:
            g.parse(data=content, format="turtle")
            logger.info(f"Successfully parsed ontology {ontology_id} with {len(g)} triples")
        except Exception as e:
            logger.error(f"Error parsing ontology {ontology_id}: {e}")
            return {"entities": {}, "is_mock": False, "error": f"Parse error: {str(e)}"}
        
        # Extract GuidelineConceptTypes for dynamic entity extraction
        guideline_concept_types = self._extract_guideline_concept_types(g)
        
        # Extract entities for each GuidelineConceptType found
        entities = {}
        for concept_type_name, concept_type_uri in guideline_concept_types.items():
            entity_list = self._extract_entities_by_type(g, concept_type_name, concept_type_uri)
            if entity_list:  # Only include types that have entities
                entities[concept_type_name.lower()] = entity_list
        
        # If no dynamic types found, use hardcoded extraction
        if not entities:
            logger.info(f"No GuidelineConceptTypes found in ontology {ontology_id}, using hardcoded extraction")
            entities = self._extract_hardcoded_entities(g)
        
        result = {
            "entities": entities,
            "is_mock": False,
            "ontology_id": ontology_id
        }
        
        # Log summary
        for entity_type, entity_list in entities.items():
            logger.info(f"Found {len(entity_list)} {entity_type} entities in ontology {ontology_id}")
        
        return result
    
    def _extract_guideline_concept_types(self, graph: Graph) -> Dict[str, str]:
        """
        Extract GuidelineConceptTypes from the ontology.
        
        Args:
            graph: RDFLib Graph
            
        Returns:
            Dictionary mapping concept type names to their URIs
        """
        guideline_concept_types = {}
        proeth_namespace = self.namespaces["intermediate"]
        
        # Find all classes that are GuidelineConceptTypes
        for concept_type in graph.subjects(RDF.type, proeth_namespace.GuidelineConceptType):
            # Get the label for this concept type
            label = next(graph.objects(concept_type, RDFS.label), None)
            if label:
                concept_name = str(label)
                guideline_concept_types[concept_name] = str(concept_type)
                logger.debug(f"Found GuidelineConceptType: {concept_name} -> {concept_type}")
        
        # If none found, try loading from intermediate ontology or use defaults
        if not guideline_concept_types:
            guideline_concept_types = self._get_default_concept_types()
        
        return guideline_concept_types
    
    def _get_default_concept_types(self) -> Dict[str, str]:
        """Get default concept types as fallback."""
        return {
            "Role": "http://proethica.org/ontology/intermediate#Role",
            "Principle": "http://proethica.org/ontology/intermediate#Principle", 
            "Obligation": "http://proethica.org/ontology/intermediate#Obligation",
            "State": "http://proethica.org/ontology/intermediate#State",
            "Resource": "http://proethica.org/ontology/intermediate#Resource",
            "Action": "http://proethica.org/ontology/intermediate#Action",
            "Event": "http://proethica.org/ontology/intermediate#Event", 
            "Capability": "http://proethica.org/ontology/intermediate#Capability"
        }
    
    def _extract_entities_by_type(self, graph: Graph, concept_type_name: str, concept_type_uri: str) -> List[Dict[str, Any]]:
        """
        Extract entities of a specific GuidelineConceptType from the graph.
        
        Args:
            graph: RDFLib Graph
            concept_type_name: Name of the concept type
            concept_type_uri: URI of the concept type
            
        Returns:
            List of entity dictionaries
        """
        entities = []
        proeth_namespace = self.namespaces["intermediate"]
        concept_type_ref = rdflib.URIRef(concept_type_uri)
        
        # Helper functions
        def get_label(s):
            return str(next(graph.objects(s, RDFS.label), 
                           s.split('/')[-1].split('#')[-1]))
        
        def get_description(s):
            return str(next(graph.objects(s, RDFS.comment), ""))
        
        # Find entities of this type using multiple strategies
        entity_subjects = set()
        
        # Direct instances
        entity_subjects.update(graph.subjects(RDF.type, concept_type_ref))
        
        # EntityType instances that also have this concept type
        entity_type_subjects = set(graph.subjects(RDF.type, proeth_namespace.EntityType))
        for s in entity_type_subjects:
            if (s, RDF.type, concept_type_ref) in graph:
                entity_subjects.add(s)
        
        # Special handling for resource types
        if concept_type_name.lower() == "resource":
            resource_type_ref = proeth_namespace.ResourceType
            entity_subjects.update(graph.subjects(RDF.type, resource_type_ref))
        
        # Create entity objects
        for s in entity_subjects:
            # Skip the concept type definition itself
            if s == concept_type_ref:
                continue
            
            # Get parent class
            parent_class = next(graph.objects(s, RDFS.subClassOf), None)
            parent_class_uri = str(parent_class) if parent_class else None
            
            entity = {
                "id": str(s),
                "uri": str(s), 
                "label": get_label(s),
                "description": get_description(s),
                "parent_class": parent_class_uri,
                "type": concept_type_name.lower()
            }
            
            # Special handling for roles - include capabilities
            if concept_type_name.lower() == "role":
                entity["capabilities"] = [
                    {
                        "id": str(o),
                        "label": get_label(o),
                        "description": get_description(o)
                    }
                    for o in graph.objects(s, proeth_namespace.hasCapability)
                ]
            
            entities.append(entity)
        
        return entities
    
    def _extract_hardcoded_entities(self, graph: Graph) -> Dict[str, List[Dict[str, Any]]]:
        """
        Extract entities using hardcoded types (fallback method).
        
        Args:
            graph: RDFLib Graph
            
        Returns:
            Dictionary of entity lists by type
        """
        entities = {}
        
        # Use the existing extraction methods as fallback
        extractors = {
            "role": self._extract_roles,
            "principle": self._extract_principles,
            "obligation": self._extract_obligations,
            "state": self._extract_states,
            "resource": self._extract_resources,
            "event": self._extract_events,
            "action": self._extract_actions,
            "capability": self._extract_capabilities
        }
        
        for entity_type, extractor in extractors.items():
            try:
                entity_list = extractor(graph)
                if entity_list:
                    entities[entity_type] = entity_list
            except Exception as e:
                logger.warning(f"Error extracting {entity_type} entities: {e}")
        
        return entities
    
    def _extract_roles(self, graph: Graph) -> List[Dict[str, Any]]:
        """Extract Role entities."""
        roles = []
        proeth_namespace = self.namespaces["intermediate"]
        
        def get_label(s):
            return str(next(graph.objects(s, RDFS.label), s.split('#')[-1]))
        
        def get_description(s):
            return str(next(graph.objects(s, RDFS.comment), ""))
        
        # Find Role instances
        role_subjects = set()
        role_subjects.update(graph.subjects(RDF.type, proeth_namespace.Role))
        
        for s in role_subjects:
            parent_class = next(graph.objects(s, RDFS.subClassOf), None)
            
            roles.append({
                "id": str(s),
                "uri": str(s),
                "label": get_label(s),
                "description": get_description(s),
                "parent_class": str(parent_class) if parent_class else None,
                "type": "role",
                "capabilities": [
                    {
                        "id": str(o),
                        "label": get_label(o),
                        "description": get_description(o)
                    }
                    for o in graph.objects(s, proeth_namespace.hasCapability)
                ]
            })
        
        return roles
    
    def _extract_principles(self, graph: Graph) -> List[Dict[str, Any]]:
        """Extract Principle entities."""
        return self._extract_simple_entities(graph, "Principle", "principle")
    
    def _extract_obligations(self, graph: Graph) -> List[Dict[str, Any]]:
        """Extract Obligation entities."""
        return self._extract_simple_entities(graph, "Obligation", "obligation")
    
    def _extract_states(self, graph: Graph) -> List[Dict[str, Any]]:
        """Extract State entities."""
        return self._extract_simple_entities(graph, "State", "state")
    
    def _extract_resources(self, graph: Graph) -> List[Dict[str, Any]]:
        """Extract Resource entities."""
        resources = []
        proeth_namespace = self.namespaces["intermediate"]
        
        # Look for ResourceType entities
        resource_subjects = set()
        resource_subjects.update(graph.subjects(RDF.type, proeth_namespace.ResourceType))
        
        return self._create_entity_objects(graph, resource_subjects, "resource")
    
    def _extract_events(self, graph: Graph) -> List[Dict[str, Any]]:
        """Extract Event entities."""
        return self._extract_simple_entities(graph, "Event", "event")
    
    def _extract_actions(self, graph: Graph) -> List[Dict[str, Any]]:
        """Extract Action entities."""
        return self._extract_simple_entities(graph, "Action", "action")
    
    def _extract_capabilities(self, graph: Graph) -> List[Dict[str, Any]]:
        """Extract Capability entities."""
        return self._extract_simple_entities(graph, "Capability", "capability")
    
    def _extract_simple_entities(self, graph: Graph, concept_name: str, entity_type: str) -> List[Dict[str, Any]]:
        """Helper method to extract simple entities."""
        proeth_namespace = self.namespaces["intermediate"]
        concept_ref = getattr(proeth_namespace, concept_name)
        
        entity_subjects = set()
        entity_subjects.update(graph.subjects(RDF.type, concept_ref))
        
        return self._create_entity_objects(graph, entity_subjects, entity_type)
    
    def _create_entity_objects(self, graph: Graph, subjects: Set, entity_type: str) -> List[Dict[str, Any]]:
        """Create entity objects from subjects."""
        entities = []
        
        def get_label(s):
            return str(next(graph.objects(s, RDFS.label), s.split('#')[-1]))
        
        def get_description(s):
            return str(next(graph.objects(s, RDFS.comment), ""))
        
        for s in subjects:
            parent_class = next(graph.objects(s, RDFS.subClassOf), None)
            
            entities.append({
                "id": str(s),
                "uri": str(s),
                "label": get_label(s),
                "description": get_description(s),
                "parent_class": str(parent_class) if parent_class else None,
                "type": entity_type
            })
        
        return entities
    
    def invalidate_cache(self, ontology_id: str = None):
        """
        Invalidate cached entities.
        
        Args:
            ontology_id: Specific ontology to invalidate, or None for all
        """
        if ontology_id:
            cache_key = f"ontology_{ontology_id}"
            if cache_key in self.ontology_cache:
                del self.ontology_cache[cache_key]
                logger.info(f"Invalidated cache for ontology {ontology_id}")
        else:
            self.ontology_cache.clear()
            logger.info("Invalidated all ontology caches")
    
    def list_ontologies(self) -> List[Dict[str, Any]]:
        """Get list of available ontologies."""
        return self.ontology_store.list_ontologies()
    
    def validate_ontology(self, ontology_id: str) -> Dict[str, Any]:
        """
        Validate an ontology and return validation results.
        
        Args:
            ontology_id: ID of the ontology to validate
            
        Returns:
            Dictionary containing validation results
        """
        try:
            content = self.ontology_store.get_ontology_content(ontology_id)
            
            # Try parsing
            g = Graph()
            g.parse(data=content, format="turtle")
            
            # Basic validation
            triple_count = len(g)
            class_count = len(list(g.subjects(RDF.type, rdflib.OWL.Class)))
            property_count = len(list(g.subjects(RDF.type, rdflib.OWL.ObjectProperty)))
            
            return {
                "valid": True,
                "ontology_id": ontology_id,
                "triple_count": triple_count,
                "class_count": class_count,
                "property_count": property_count,
                "errors": []
            }
            
        except Exception as e:
            return {
                "valid": False,
                "ontology_id": ontology_id,
                "errors": [str(e)]
            }
