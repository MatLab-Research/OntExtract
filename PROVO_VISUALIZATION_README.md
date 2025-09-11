# PROV-O Provenance Graph Visualization for OntExtract

## Overview
An interactive web-based PROV-O provenance graph visualization has been created for OntExtract that demonstrates how the system tracks document processing workflows using the W3C PROV-O standard.

## Features

### Interactive Visualization
- **Technology**: Built with Cytoscape.js for interactive graph manipulation
- **Interactivity**: 
  - Click nodes to see detailed information
  - Drag to pan around the graph
  - Scroll to zoom in/out
  - Export as PNG for publication

### PROV-O Elements Represented

#### Entities (Document Versions)
- Original uploaded documents
- Processed versions (LangExtract, Semantic Segments, Named Entities)
- Generated outputs (Embeddings, Drift Analysis)
- Displayed as rounded rectangles with peach coloring

#### Activities (Processing Operations)
- Upload, Extract, Segment, NER
- Embedding generation, Synthesis
- Displayed as circles with light blue coloring

#### Agents (Tools & Orchestrators)
- Human researchers/curators
- LLM models (Gemini)
- NLP tools (spaCy, NLTK)
- Sentence Transformers
- LLM Orchestrator
- Displayed as diamonds with light green coloring

### Relationships
- **wasDerivedFrom** (blue arrows): Shows entity lineage
- **wasGeneratedBy** (red arrows): Links entities to generating activities
- **wasAssociatedWith** (green dashed arrows): Shows agent responsibility

### Multiple Scenarios
1. **Complete Workflow**: Full document processing pipeline with all tools
2. **Simple Processing**: Basic processing flow
3. **Multi-Version Analysis**: Demonstrates version tracking capabilities

## Accessing the Visualization

### To run the visualization:

1. Start OntExtract server:
   ```bash
   cd OntExtract
   python run.py
   ```

2. Access the visualization at:
   ```
   http://localhost:8765/provenance/graph
   ```

### Files Created:
- `app/templates/provenance_graph.html` - The complete HTML/JS visualization
- `app/routes/provenance_visualization.py` - Flask route to serve the page
- Modified `app/__init__.py` - Registered the blueprint

## For Paper Inclusion

### Option 1: Static Screenshot
The visualization includes an "Export PNG" button that generates a high-resolution image suitable for publication. The exported image will show:
- The complete PROV-O graph structure
- All three types of elements (entities, activities, agents)
- All three relationship types
- Color-coded elements for easy interpretation

### Option 2: Interactive Supplementary Material
The HTML file (`provenance_graph.html`) is completely self-contained and can be hosted as supplementary material, allowing readers to interact with the provenance graph directly.

### Caption Suggestion for Paper:
"Interactive PROV-O provenance graph showing OntExtract's document processing workflow. Entities (peach) represent document versions, activities (blue) show processing operations, and agents (green) indicate the tools responsible for each operation. Relationships trace the complete provenance chain from document upload through multi-source synthesis."

## Key Benefits Demonstrated

1. **Complete Traceability**: Every processing step is recorded
2. **Tool Attribution**: Clear identification of which tool performed each operation
3. **Version Lineage**: Explicit tracking of how versions derive from each other
4. **Multi-Source Synthesis**: Shows how multiple analytical pathways converge
5. **PROV-O Compliance**: Follows W3C standards for provenance representation

## Technical Implementation

- Uses standard PROV-O vocabulary (prov:Entity, prov:Activity, prov:Agent)
- Implements three core relationships (wasDerivedFrom, wasGeneratedBy, wasAssociatedWith)
- Provides multiple layout options (hierarchical, force-directed, circular)
- Supports provenance path highlighting to trace analytical lineage
- Includes statistics panel showing element counts

This visualization effectively demonstrates how OntExtract implements PROV-O provenance tracking as described in Section II-C of the paper, making the abstract concepts concrete and interactive for readers.
