"""
Ontology Import Service for importing and managing external ontologies.

This service provides functionality to import ontologies from various sources,
with special support for PROV-O (W3C Provenance Ontology) and other standard ontologies.
It can be integrated with the proethica system for unified ontology management.

Enhanced with OntServe integration for centralized ontology management.

Author: OntExtract Team
Date: 2025-01-19
Updated: 2025-08-22 (OntServe integration)
"""

import os
import logging
import json
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from urllib.parse import urlparse
import requests
import rdflib
from rdflib import Graph, Namespace, RDF, RDFS, OWL
from rdflib.namespace import PROV, FOAF, DCTERMS, XSD

logger = logging.getLogger(__name__)

# Try to import OntServe client
try:
    # Assume OntServe client is available in the same environment or via path
    import sys
    from pathlib import Path
    
    # Try to find OntServe client
    possible_paths = [
        Path(__file__).parent.parent.parent.parent / "OntServe" / "client",
        Path.cwd() / "OntServe" / "client",
        Path("/home/chris/onto/OntServe/client")
    ]
    
    ontserve_client_found = False
    for path in possible_paths:
        if (path / "ontextract_client.py").exists():
            sys.path.insert(0, str(path))
            from ontextract_client import OntExtractClient, OntServeConnectionError
            ontserve_client_found = True
            logger.info(f"Found OntServe client at {path}")
            break
    
    if not ontserve_client_found:
        raise ImportError("OntServe client not found")
        
except ImportError as e:
    logger.warning(f"OntServe client not available: {e}. Using fallback mode only.")
    OntExtractClient = None
    OntServeConnectionError = Exception

# Standard ontology namespaces
STANDARD_NAMESPACES = {
    'prov': PROV,
    'foaf': FOAF,
    'dcterms': DCTERMS,
    'xsd': XSD,
    'owl': OWL,
    'rdf': RDF,
    'rdfs': RDFS,
    'bfo': Namespace("http://purl.obolibrary.org/obo/"),
    'obo': Namespace("http://purl.obolibrary.org/obo/"),
    'time': Namespace("http://www.w3.org/2006/time#"),
    'skos': Namespace("http://www.w3.org/2004/02/skos/core#"),
    'dcat': Namespace("http://www.w3.org/ns/dcat#"),
    'void': Namespace("http://rdfs.org/ns/void#"),
}

# PROV-O specific namespaces
PROV_NAMESPACES = {
    'prov': PROV,
    'provo': Namespace("http://www.w3.org/ns/prov#"),
    'prov-o': Namespace("http://www.w3.org/ns/prov-o#"),
    'prov-aq': Namespace("http://www.w3.org/ns/prov-aq#"),
    'prov-dc': Namespace("http://www.w3.org/ns/prov-dc#"),
    'prov-dictionary': Namespace("http://www.w3.org/ns/prov-dictionary#"),
    'prov-links': Namespace("http://www.w3.org/ns/prov-links#"),
}

class OntologyImporter:
    """
    Service for importing ontologies from various sources.
    
    This class handles:
    - Fetching ontologies from URLs
    - Parsing and validating ontology content
    - Extracting metadata and structure
    - Caching imported ontologies
    - Integration with proethica ontology system
    - OntServe integration for centralized ontology management
    """
    
    def __init__(self, cache_dir: str = None, storage_backend: Any = None, 
                 use_ontserve: bool = None, ontserve_url: str = None):
        """
        Initialize the ontology importer.
        
        Args:
            cache_dir: Directory for caching downloaded ontologies
            storage_backend: Optional storage backend (e.g., database) for persistence
            use_ontserve: Whether to use OntServe (auto-detected if None)
            ontserve_url: OntServe URL (optional)
        """
        self.cache_dir = cache_dir or os.path.join(os.getcwd(), 'ontology_cache')
        self.storage_backend = storage_backend
        self.imported_ontologies = {}
        
        # OntServe configuration
        self.use_ontserve = use_ontserve if use_ontserve is not None else (
            os.environ.get('USE_ONTSERVE', 'true').lower() == 'true' and 
            OntExtractClient is not None
        )
        self.ontserve_client = None
        
        if self.use_ontserve and OntExtractClient:
            try:
                self.ontserve_client = OntExtractClient(ontserve_url=ontserve_url)
                logger.info("OntServe client initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize OntServe client: {e}")
                self.use_ontserve = False
        
        # Create cache directory if it doesn't exist
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Initialize namespace manager
        from rdflib.namespace import NamespaceManager
        self.namespace_manager = NamespaceManager(Graph())
        for prefix, ns in STANDARD_NAMESPACES.items():
            self.namespace_manager.bind(prefix, ns)
    
    def import_prov_o(self, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """
        Import the W3C PROV-O ontology.
        
        Enhanced to use OntServe when available, with fallback to direct download.
        
        Args:
            force_refresh: Force re-download even if cached
            
        Returns:
            Dictionary containing imported ontology information
        """
        logger.info("Importing PROV-O ontology...")
        
        # Try OntServe first if available
        if self.use_ontserve and self.ontserve_client:
            try:
                logger.info("Attempting to get PROV-O from OntServe...")
                domain_info = self.ontserve_client.get_domain_info('prov-o')
                
                if domain_info and not domain_info.get('error'):
                    # Get PROV-O entities from OntServe
                    experiment_concepts = self.ontserve_client.get_prov_experiment_concepts()
                    
                    # Create a virtual result that matches the expected format
                    result = {
                        'success': True,
                        'ontology_id': 'prov-o',
                        'metadata': {
                            'name': 'W3C Provenance Ontology (PROV-O)',
                            'description': 'The PROV Ontology (PROV-O) provides a set of classes, properties, and restrictions for representing provenance information',
                            'source': 'OntServe',
                            'ontology_id': 'prov-o'
                        },
                        'graph': None,  # We don't have the raw graph from OntServe
                        'experiment_concepts': experiment_concepts,
                        'from_ontserve': True,
                        'message': f"Successfully retrieved PROV-O from OntServe with {sum(len(concepts) for concepts in experiment_concepts.values())} concepts"
                    }
                    
                    logger.info(f"Retrieved PROV-O from OntServe with {sum(len(concepts) for concepts in experiment_concepts.values())} concepts")
                    return result
                    
            except Exception as e:
                logger.warning(f"Failed to get PROV-O from OntServe: {e}")
                logger.info("Falling back to direct download...")
        
        # Fallback to direct download
        prov_o_ttl_url = "https://www.w3.org/ns/prov.ttl"
        
        # Try to import from the TTL file directly
        result = self.import_from_url(
            prov_o_ttl_url,
            ontology_id="prov-o",
            name="W3C Provenance Ontology (PROV-O)",
            description="The PROV Ontology (PROV-O) provides a set of classes, properties, and restrictions for representing provenance information",
            format='turtle',
            force_refresh=force_refresh
        )
        
        # Extract PROV-O specific concepts for experiment classification
        if result.get('success'):
            if result.get('graph'):
                result['experiment_concepts'] = self._extract_prov_experiment_concepts(result['graph'])
                logger.info(f"Extracted {sum(len(concepts) for concepts in result['experiment_concepts'].values())} PROV-O concepts for experiments")
        
        return result
    
    def import_from_url(self, url: str, ontology_id: Optional[str] = None, 
                       name: Optional[str] = None, description: Optional[str] = None,
                       format: Optional[str] = None, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Import an ontology from a URL.
        
        Args:
            url: URL of the ontology to import
            ontology_id: Unique identifier for the ontology
            name: Human-readable name for the ontology
            description: Description of the ontology
            format: RDF format (turtle, xml, n3, etc.)
            force_refresh: Force re-download even if cached
            
        Returns:
            Dictionary containing import results
        """
        # Generate ontology ID if not provided
        if not ontology_id:
            ontology_id = self._generate_ontology_id(url)
        
        # Check cache first
        cache_file = os.path.join(self.cache_dir, f"{ontology_id}.ttl")
        metadata_file = os.path.join(self.cache_dir, f"{ontology_id}.json")
        
        if not force_refresh and os.path.exists(cache_file):
            logger.info(f"Loading ontology {ontology_id} from cache")
            cached_data = self._load_from_cache(ontology_id)
            if cached_data:
                return cached_data
        
        try:
            # Download ontology
            logger.info(f"Downloading ontology from {url}")
            response = requests.get(url, headers={'Accept': 'text/turtle, application/rdf+xml'})
            response.raise_for_status()
            
            # Parse ontology
            g = Graph()
            
            # Auto-detect format if not specified
            if not format:
                content_type = response.headers.get('Content-Type', '')
                format = self._detect_format(content_type, url)
            
            g.parse(data=response.text, format=format)
            logger.info(f"Successfully parsed ontology with {len(g)} triples")
            
            # Extract metadata
            metadata = self._extract_metadata(g, url, name, description)
            metadata['ontology_id'] = ontology_id
            metadata['source_url'] = url
            metadata['import_date'] = datetime.now().isoformat()
            metadata['format'] = format
            metadata['triple_count'] = len(g)
            
            # Save to cache
            g.serialize(destination=cache_file, format='turtle')
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Store in memory
            self.imported_ontologies[ontology_id] = {
                'graph': g,
                'metadata': metadata,
                'content': g.serialize(format='turtle')
            }
            
            # Optionally save to storage backend
            if self.storage_backend:
                self._save_to_storage(ontology_id, g, metadata)
            
            return {
                'success': True,
                'ontology_id': ontology_id,
                'metadata': metadata,
                'graph': g,
                'message': f"Successfully imported ontology {ontology_id}"
            }
            
        except Exception as e:
            logger.error(f"Error importing ontology from {url}: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': f"Failed to import ontology from {url}"
            }
    
    def import_from_file(self, file_path: str, ontology_id: Optional[str] = None,
                        name: Optional[str] = None, description: Optional[str] = None,
                        format: str = 'turtle') -> Dict[str, Any]:
        """
        Import an ontology from a local file.
        
        Args:
            file_path: Path to the ontology file
            ontology_id: Unique identifier for the ontology
            name: Human-readable name for the ontology
            description: Description of the ontology
            format: RDF format (turtle, xml, n3, etc.)
            
        Returns:
            Dictionary containing import results
        """
        # Generate ontology ID if not provided
        if not ontology_id:
            ontology_id = os.path.splitext(os.path.basename(file_path))[0]
        
        try:
            # Parse ontology
            g = Graph()
            g.parse(file_path, format=format)
            logger.info(f"Successfully parsed ontology from {file_path} with {len(g)} triples")
            
            # Extract metadata
            metadata = self._extract_metadata(g, file_path, name, description)
            metadata['ontology_id'] = ontology_id
            metadata['source_file'] = file_path
            metadata['import_date'] = datetime.now().isoformat()
            metadata['format'] = format
            metadata['triple_count'] = len(g)
            
            # Save to cache
            cache_file = os.path.join(self.cache_dir, f"{ontology_id}.ttl")
            metadata_file = os.path.join(self.cache_dir, f"{ontology_id}.json")
            
            g.serialize(destination=cache_file, format='turtle')
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Store in memory
            self.imported_ontologies[ontology_id] = {
                'graph': g,
                'metadata': metadata,
                'content': g.serialize(format='turtle')
            }
            
            # Optionally save to storage backend
            if self.storage_backend:
                self._save_to_storage(ontology_id, g, metadata)
            
            return {
                'success': True,
                'ontology_id': ontology_id,
                'metadata': metadata,
                'graph': g,
                'message': f"Successfully imported ontology {ontology_id}"
            }
            
        except Exception as e:
            logger.error(f"Error importing ontology from {file_path}: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': f"Failed to import ontology from {file_path}"
            }
    
    def get_imported_ontology(self, ontology_id: str) -> Optional[Dict[str, Any]]:
        """
        Get an imported ontology by ID.
        
        Args:
            ontology_id: ID of the ontology to retrieve
            
        Returns:
            Dictionary containing ontology data or None if not found
        """
        # Check memory first
        if ontology_id in self.imported_ontologies:
            return self.imported_ontologies[ontology_id]
        
        # Try to load from cache
        return self._load_from_cache(ontology_id)
    
    def list_imported_ontologies(self) -> List[Dict[str, Any]]:
        """
        List all imported ontologies.
        
        Returns:
            List of ontology metadata dictionaries
        """
        ontologies = []
        
        # Get from memory
        for ont_id, ont_data in self.imported_ontologies.items():
            ontologies.append(ont_data['metadata'])
        
        # Get from cache (excluding those already in memory)
        for filename in os.listdir(self.cache_dir):
            if filename.endswith('.json'):
                ont_id = filename[:-5]  # Remove .json extension
                if ont_id not in self.imported_ontologies:
                    try:
                        with open(os.path.join(self.cache_dir, filename), 'r') as f:
                            metadata = json.load(f)
                            ontologies.append(metadata)
                    except Exception as e:
                        logger.warning(f"Error loading metadata for {ont_id}: {e}")
        
        return ontologies
    
    def extract_classes(self, ontology_id: str) -> List[Dict[str, Any]]:
        """
        Extract all classes from an imported ontology.
        
        Args:
            ontology_id: ID of the ontology
            
        Returns:
            List of class definitions
        """
        ont_data = self.get_imported_ontology(ontology_id)
        if not ont_data:
            return []
        
        g = ont_data['graph']
        classes = []
        
        for s in g.subjects(RDF.type, OWL.Class):
            class_info = {
                'uri': str(s),
                'label': self._get_label(g, s),
                'comment': self._get_comment(g, s),
                'subclass_of': [str(o) for o in g.objects(s, RDFS.subClassOf)]
            }
            classes.append(class_info)
        
        return classes
    
    def extract_properties(self, ontology_id: str) -> List[Dict[str, Any]]:
        """
        Extract all properties from an imported ontology.
        
        Args:
            ontology_id: ID of the ontology
            
        Returns:
            List of property definitions
        """
        ont_data = self.get_imported_ontology(ontology_id)
        if not ont_data:
            return []
        
        g = ont_data['graph']
        properties = []
        
        # Object properties
        for s in g.subjects(RDF.type, OWL.ObjectProperty):
            prop_info = {
                'uri': str(s),
                'type': 'object_property',
                'label': self._get_label(g, s),
                'comment': self._get_comment(g, s),
                'domain': [str(o) for o in g.objects(s, RDFS.domain)],
                'range': [str(o) for o in g.objects(s, RDFS.range)]
            }
            properties.append(prop_info)
        
        # Datatype properties
        for s in g.subjects(RDF.type, OWL.DatatypeProperty):
            prop_info = {
                'uri': str(s),
                'type': 'datatype_property',
                'label': self._get_label(g, s),
                'comment': self._get_comment(g, s),
                'domain': [str(o) for o in g.objects(s, RDFS.domain)],
                'range': [str(o) for o in g.objects(s, RDFS.range)]
            }
            properties.append(prop_info)
        
        return properties
    
    def _extract_prov_experiment_concepts(self, graph: Graph) -> Dict[str, List[Dict[str, Any]]]:
        """
        Extract PROV-O concepts relevant for experiment classification.
        
        Args:
            graph: RDF graph containing PROV-O ontology
            
        Returns:
            Dictionary of concept categories with their terms
        """
        concepts = {
            'activities': [],
            'entities': [],
            'agents': [],
            'relations': [],
            'qualified_relations': []
        }
        
        # Extract Activity subclasses (for experiment steps/processes)
        for s in graph.subjects(RDFS.subClassOf, PROV.Activity):
            concepts['activities'].append({
                'uri': str(s),
                'label': self._get_label(graph, s),
                'comment': self._get_comment(graph, s),
                'type': 'activity'
            })
        
        # Extract Entity subclasses (for experiment artifacts/data)
        for s in graph.subjects(RDFS.subClassOf, PROV.Entity):
            concepts['entities'].append({
                'uri': str(s),
                'label': self._get_label(graph, s),
                'comment': self._get_comment(graph, s),
                'type': 'entity'
            })
        
        # Extract Agent subclasses (for experiment participants)
        for s in graph.subjects(RDFS.subClassOf, PROV.Agent):
            concepts['agents'].append({
                'uri': str(s),
                'label': self._get_label(graph, s),
                'comment': self._get_comment(graph, s),
                'type': 'agent'
            })
        
        # Extract core PROV properties for relationships
        prov_properties = [
            (PROV.wasGeneratedBy, 'generation'),
            (PROV.used, 'usage'),
            (PROV.wasInformedBy, 'communication'),
            (PROV.wasStartedBy, 'start'),
            (PROV.wasEndedBy, 'end'),
            (PROV.wasInvalidatedBy, 'invalidation'),
            (PROV.wasDerivedFrom, 'derivation'),
            (PROV.wasAttributedTo, 'attribution'),
            (PROV.wasAssociatedWith, 'association'),
            (PROV.actedOnBehalfOf, 'delegation'),
            (PROV.wasInfluencedBy, 'influence')
        ]
        
        for prop_uri, prop_type in prov_properties:
            prop_info = {
                'uri': str(prop_uri),
                'label': self._get_label(graph, prop_uri) or prop_uri.split('#')[-1],
                'comment': self._get_comment(graph, prop_uri),
                'type': prop_type
            }
            concepts['relations'].append(prop_info)
        
        # Add core PROV classes
        core_classes = [
            (PROV.Activity, 'activities'),
            (PROV.Entity, 'entities'),
            (PROV.Agent, 'agents')
        ]
        
        for class_uri, category in core_classes:
            class_info = {
                'uri': str(class_uri),
                'label': self._get_label(graph, class_uri) or class_uri.split('#')[-1],
                'comment': self._get_comment(graph, class_uri),
                'type': category[:-1]  # Remove 's' from plural
            }
            if class_info not in concepts[category]:
                concepts[category].insert(0, class_info)  # Add at beginning
        
        return concepts
    
    def _extract_metadata(self, graph: Graph, source: str, 
                         name: Optional[str] = None, description: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract metadata from an ontology graph.
        
        Args:
            graph: RDF graph
            source: Source URL or file path
            name: Override name
            description: Override description
            
        Returns:
            Dictionary containing metadata
        """
        metadata = {
            'source': source,
            'name': name or '',
            'description': description or ''
        }
        
        # Try to find ontology declaration
        for s in graph.subjects(RDF.type, OWL.Ontology):
            if not name:
                metadata['name'] = self._get_label(graph, s) or str(s)
            if not description:
                comment = self._get_comment(graph, s)
                if comment:
                    metadata['description'] = comment
            
            # Get version info
            version = next(graph.objects(s, OWL.versionInfo), None)
            if version:
                metadata['version'] = str(version)
            
            # Get other metadata
            for pred, key in [
                (DCTERMS.title, 'title'),
                (DCTERMS.creator, 'creator'),
                (DCTERMS.publisher, 'publisher'),
                (DCTERMS.license, 'license'),
                (DCTERMS.created, 'created'),
                (DCTERMS.modified, 'modified')
            ]:
                value = next(graph.objects(s, pred), None)
                if value:
                    metadata[key] = str(value)
            
            break  # Use first ontology declaration found
        
        # Count classes and properties
        metadata['class_count'] = str(len(list(graph.subjects(RDF.type, OWL.Class))))
        metadata['property_count'] = str(
            len(list(graph.subjects(RDF.type, OWL.ObjectProperty))) +
            len(list(graph.subjects(RDF.type, OWL.DatatypeProperty)))
        )
        
        return metadata
    
    def _get_label(self, graph: Graph, subject: Any) -> Optional[str]:
        """Get rdfs:label for a subject."""
        label = next(graph.objects(subject, RDFS.label), None)
        return str(label) if label else None
    
    def _get_comment(self, graph: Graph, subject: Any) -> Optional[str]:
        """Get rdfs:comment for a subject."""
        comment = next(graph.objects(subject, RDFS.comment), None)
        return str(comment) if comment else None
    
    def _generate_ontology_id(self, url: str) -> str:
        """Generate a unique ID for an ontology based on its URL."""
        parsed = urlparse(url)
        # Use domain and path to create ID
        id_parts = []
        if parsed.netloc:
            id_parts.append(parsed.netloc.replace('.', '-'))
        if parsed.path:
            path = parsed.path.strip('/').replace('/', '-').replace('.', '-')
            if path:
                id_parts.append(path)
        
        if id_parts:
            return '-'.join(id_parts)
        else:
            # Fallback to hash
            return hashlib.md5(url.encode()).hexdigest()[:8]
    
    def _detect_format(self, content_type: str, url: str) -> str:
        """Detect RDF format from content type or URL."""
        # Check content type
        if 'turtle' in content_type or 'ttl' in content_type:
            return 'turtle'
        elif 'rdf+xml' in content_type or 'application/rdf' in content_type:
            return 'xml'
        elif 'n3' in content_type:
            return 'n3'
        elif 'json-ld' in content_type:
            return 'json-ld'
        
        # Check URL extension
        if url.endswith('.ttl'):
            return 'turtle'
        elif url.endswith('.rdf') or url.endswith('.xml'):
            return 'xml'
        elif url.endswith('.n3'):
            return 'n3'
        elif url.endswith('.jsonld'):
            return 'json-ld'
        
        # Default to turtle
        return 'turtle'
    
    def _load_from_cache(self, ontology_id: str) -> Optional[Dict[str, Any]]:
        """Load an ontology from cache."""
        cache_file = os.path.join(self.cache_dir, f"{ontology_id}.ttl")
        metadata_file = os.path.join(self.cache_dir, f"{ontology_id}.json")
        
        if not os.path.exists(cache_file) or not os.path.exists(metadata_file):
            return None
        
        try:
            # Load metadata
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            # Load graph
            g = Graph()
            g.parse(cache_file, format='turtle')
            
            # Store in memory
            self.imported_ontologies[ontology_id] = {
                'graph': g,
                'metadata': metadata,
                'content': g.serialize(format='turtle')
            }
            
            return self.imported_ontologies[ontology_id]
            
        except Exception as e:
            logger.error(f"Error loading ontology {ontology_id} from cache: {e}")
            return None
    
    def _save_to_storage(self, ontology_id: str, graph: Graph, metadata: Dict[str, Any]):
        """
        Save ontology to storage backend.
        
        This is a placeholder for integration with proethica's database.
        """
        # TODO: Implement storage backend integration
        # This would save to the Ontology model in proethica's database
        pass


# Integration comment for proethica:
"""
This ontology importer can be integrated into the proethica system by:

1. Using it in conjunction with the existing OntologyEntityService
2. Storing imported ontologies in the proethica database (Ontology model)
3. Extending the World model to reference imported ontologies
4. Using PROV-O concepts for experiment tracking and provenance

Example integration in proethica:

from shared_services.ontology.ontology_importer import OntologyImporter

# In a route or service
importer = OntologyImporter(storage_backend=db)
result = importer.import_prov_o()

if result['success']:
    # Save to proethica database
    ontology = Ontology(
        domain_id=result['ontology_id'],
        content=result['graph'].serialize(format='turtle'),
        metadata=json.dumps(result['metadata'])
    )
    db.session.add(ontology)
    db.session.commit()
"""
