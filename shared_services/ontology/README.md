# Ontology Services Documentation

## Overview

The Ontology Services module provides comprehensive functionality for importing, managing, and extracting entities from RDF/TTL ontologies. It includes special support for PROV-O (W3C Provenance Ontology) for experiment classification and tracking.

## Components

### 1. OntologyImporter (`ontology_importer.py`)

The main service for importing ontologies from various sources (URLs, local files) with caching support.

**Key Features:**
- Import ontologies from URLs (e.g., W3C PROV-O)
- Import ontologies from local files
- Automatic format detection (Turtle, RDF/XML, N3, JSON-LD)
- Local caching to avoid repeated downloads
- Metadata extraction (version, creator, license, etc.)
- Class and property extraction
- PROV-O specific concept extraction for experiments

### 2. OntologyEntityService (`entity_service.py`)

Service for extracting entities from RDF/TTL ontologies with support for dynamic GuidelineConceptType discovery.

**Key Features:**
- RDF/TTL parsing and entity extraction
- Dynamic GuidelineConceptType discovery
- Entity relationship mapping
- Ontology caching and validation
- Support for multiple storage backends (file-based, database)

## Installation

### Requirements

```bash
pip install rdflib requests
```

Or install from the shared services requirements:

```bash
pip install -r shared_services_requirements.txt
```

## Usage Examples

### Basic Import of PROV-O

```python
from shared_services.ontology.ontology_importer import OntologyImporter

# Create importer instance
importer = OntologyImporter(cache_dir='./ontology_cache')

# Import PROV-O ontology
result = importer.import_prov_o()

if result['success']:
    print(f"Imported {result['metadata']['triple_count']} triples")
    print(f"Found {result['metadata']['class_count']} classes")
    
    # Access experiment-specific concepts
    concepts = result['experiment_concepts']
    for activity in concepts['activities']:
        print(f"Activity: {activity['label']}")
```

### Import Custom Ontology from URL

```python
# Import any ontology from a URL
result = importer.import_from_url(
    url="https://example.org/my-ontology.ttl",
    ontology_id="my-ontology",
    name="My Custom Ontology",
    description="Description of my ontology"
)
```

### Import Local Ontology File

```python
# Import from local file
result = importer.import_from_file(
    file_path="/path/to/ontology.ttl",
    ontology_id="local-ontology",
    name="Local Ontology",
    format="turtle"  # or "xml", "n3", "json-ld"
)
```

### Extract Classes and Properties

```python
# Get imported ontology
ont_data = importer.get_imported_ontology('prov-o')

# Extract all classes
classes = importer.extract_classes('prov-o')
for cls in classes:
    print(f"Class: {cls['label']} - {cls['comment']}")

# Extract all properties
properties = importer.extract_properties('prov-o')
for prop in properties:
    print(f"Property: {prop['label']} ({prop['type']})")
```

### Entity Extraction with OntologyEntityService

```python
from shared_services.ontology.entity_service import OntologyEntityService, FileOntologyStore

# Create entity service with file-based storage
store = FileOntologyStore('/path/to/ontologies')
service = OntologyEntityService(ontology_store=store)

# Get entities from an ontology
entities = service.get_entities('engineering-ethics')

# Access entities by type
roles = entities['entities'].get('role', [])
for role in roles:
    print(f"Role: {role['label']}")
    for capability in role.get('capabilities', []):
        print(f"  - Can: {capability['label']}")
```

## Integration with ProEthica

### Database Integration

The ontology services can be integrated with ProEthica's database system:

```python
from shared_services.ontology.ontology_importer import OntologyImporter
from app.models.ontology import Ontology  # ProEthica model
from app import db

# Create importer with database backend
importer = OntologyImporter(storage_backend=db)

# Import PROV-O
result = importer.import_prov_o()

if result['success']:
    # Save to ProEthica database
    ontology = Ontology(
        domain_id=result['ontology_id'],
        content=result['graph'].serialize(format='turtle'),
        metadata=json.dumps(result['metadata'])
    )
    db.session.add(ontology)
    db.session.commit()
```

### Using with Experiments

PROV-O concepts can be used to classify and track experiment provenance:

```python
# Get PROV-O concepts for experiment tracking
result = importer.import_prov_o()
concepts = result['experiment_concepts']

# Use for experiment classification
experiment_data = {
    'activities': [],  # Track experiment steps
    'entities': [],    # Track data/artifacts
    'agents': [],      # Track participants
    'relations': []    # Track relationships
}

# Map experiment steps to PROV activities
for step in experiment_steps:
    activity = {
        'type': 'prov:Activity',
        'label': step.name,
        'startTime': step.start_time,
        'endTime': step.end_time
    }
    experiment_data['activities'].append(activity)

# Track data provenance
for data_item in experiment_data_items:
    entity = {
        'type': 'prov:Entity',
        'label': data_item.name,
        'wasGeneratedBy': data_item.generating_activity,
        'wasAttributedTo': data_item.creator
    }
    experiment_data['entities'].append(entity)
```

## PROV-O Concepts for Experiments

The PROV-O ontology provides key concepts for tracking experiment provenance:

### Core Classes

- **Activity**: Represents experiment steps, processes, or procedures
- **Entity**: Represents data, documents, or artifacts produced/used
- **Agent**: Represents people, organizations, or software involved

### Key Relationships

- **wasGeneratedBy**: Links data to the activity that created it
- **used**: Links activities to the data they consumed
- **wasAssociatedWith**: Links activities to responsible agents
- **wasAttributedTo**: Links entities to their creators
- **wasDerivedFrom**: Tracks data lineage and transformations

### Example Experiment Tracking

```python
# Define an experiment workflow using PROV-O concepts
experiment = {
    'id': 'exp-001',
    'type': 'prov:Activity',
    'label': 'Text Extraction Experiment',
    
    # Track inputs
    'used': [
        {'id': 'doc-001', 'type': 'prov:Entity', 'label': 'Input Document'},
        {'id': 'ont-001', 'type': 'prov:Entity', 'label': 'Domain Ontology'}
    ],
    
    # Track outputs
    'generated': [
        {'id': 'result-001', 'type': 'prov:Entity', 'label': 'Extracted Entities'},
        {'id': 'report-001', 'type': 'prov:Entity', 'label': 'Analysis Report'}
    ],
    
    # Track participants
    'wasAssociatedWith': [
        {'id': 'user-001', 'type': 'prov:Agent', 'label': 'Researcher'},
        {'id': 'system-001', 'type': 'prov:Agent', 'label': 'OntExtract System'}
    ]
}
```

## Caching

The importer automatically caches downloaded ontologies to avoid repeated downloads:

- Cache location: `./ontology_cache/` (configurable)
- Cache format: Turtle (`.ttl`) files with JSON metadata
- Force refresh: Use `force_refresh=True` to re-download

## Error Handling

```python
result = importer.import_from_url(url)

if result['success']:
    # Process successful import
    print(f"Imported: {result['ontology_id']}")
else:
    # Handle error
    print(f"Error: {result['error']}")
    print(f"Message: {result['message']}")
```

## Available Ontologies

### Pre-configured Imports

1. **PROV-O**: W3C Provenance Ontology
   - URL: https://www.w3.org/ns/prov.ttl
   - Use: `importer.import_prov_o()`

2. **BFO**: Basic Formal Ontology (if available locally)
   - Path: `/ontologies/bfo.ttl`
   - Use: `importer.import_from_file(path)`

### ProEthica Ontologies

The system can work with ProEthica's existing ontologies:

- `engineering-ethics.ttl`: Engineering ethics concepts
- `proethica-intermediate.ttl`: Intermediate ontology with GuidelineConceptTypes
- `owl-time.ttl`: Time ontology for temporal reasoning

## Testing

Run the test suite to verify functionality:

```bash
python test_ontology_import.py
```

This will:
1. Import PROV-O from W3C
2. Import local BFO ontology (if available)
3. List all imported ontologies
4. Extract and display classes/properties

## Future Enhancements

Potential improvements for the ontology services:

1. **OWL Reasoning**: Add reasoning capabilities for inference
2. **SPARQL Queries**: Support for SPARQL query execution
3. **Ontology Alignment**: Tools for mapping between ontologies
4. **Version Management**: Track ontology versions and changes
5. **Validation Rules**: Custom validation for domain-specific requirements
6. **GraphQL API**: Expose ontology data via GraphQL
7. **Visualization**: Generate ontology visualizations
8. **Export Formats**: Support additional export formats (OWL, OBO, etc.)

## Support

For questions or issues:
- Check the test files for usage examples
- Review the inline documentation in the source code
- Consult the ProEthica integration documentation

## License

This module is part of the OntExtract project and follows the same licensing terms.
