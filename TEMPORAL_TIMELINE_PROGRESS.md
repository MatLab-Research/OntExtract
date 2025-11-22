# Temporal Timeline Feature - Progress Document

**Last Updated**: 2025-11-21
**Branch**: development
**Last Commit**: `2089d04 update temporal experiment cards`

## Overview

Implemented a unified timeline visualization for temporal evolution experiments that merges period cards and semantic event cards into a single chronological display.

## Completed Features

### 1. Unified Timeline Display
- **Location**: `/experiments/<id>/manage_temporal_terms`
- **Description**: Merged period cards and semantic event cards into single chronological timeline
- **Implementation**:
  - Server-side Jinja template logic merges and sorts timeline items by year
  - Client-side JavaScript dynamically rebuilds timeline on add/remove operations
  - Changed header from "Time Period Configuration" to "Temporal Timeline"

### 2. Period Cards (Auto-generated, Manual, OED)
- **Auto-generated** (blue border): Created from document publication dates
  - One period per unique publication year
  - Automatically links documents to their period
  - Shows document count and titles
- **Manual** (gray border): User-specified periods
  - Two entry modes: comma-separated list or year range with intervals
  - Example: "1910, 1956, 1995, 2019" or "1900-2025 with 5-year intervals"
- **OED** (green border): Generated from Oxford English Dictionary data
  - Pulls historical quotation dates for terms
  - Automatically creates periods based on OED timeline

### 3. Semantic Event Cards (Colored by Type)
Event types for tracking temporal transitions:
- **Inflection Point** (purple `#6f42c1`): Major semantic shift
- **Stable Polysemy** (teal `#20c997`): Multiple stable meanings coexist
- **Domain Network** (orange `#fd7e14`): Domain-specific semantic usage
- **Semantic Shift** (pink `#d63384`): Gradual meaning change
- **Emergence** (green `#198754`): New meaning emerging
- **Decline** (red `#dc3545`): Meaning fading or becoming obsolete

### 4. Document Linking
- Period cards show linked documents with clickable links
- Semantic event cards can reference supporting documents as evidence
- Fixed routing: Uses `text_input.document_detail` with UUID (not ID)
- Links format: `/document/{uuid}`

### 5. Data Architecture
- **Single Source of Truth**: `Document.publication_date` field
  - Supports flexible formats: year-only, year-month, full date
  - Parsed via `app/utils/date_parser.py`
  - Falls back to `created_at` (upload date) if no publication date set
- **Storage**: Experiment configuration JSON stores:
  - `time_periods`: List of years (integers)
  - `semantic_events`: List of event objects
  - `period_documents`: Map of year → document list
  - `period_metadata`: Map of year → metadata (source type, document count)

## File Changes

### 1. Frontend: `/app/templates/experiments/temporal_term_manager.html`
**Key Changes**:
- Lines 330-524: Unified timeline section with merged cards
- Lines 1062-1219: `refreshTimelineUI()` function (replaces separate refresh functions)
- Lines 550-612: Semantic event modal for add/edit
- Lines 943-1110: JavaScript functions for semantic events

**Jinja Template Merge Logic** (lines 394-425):
```jinja
{# Build a merged timeline of periods and events #}
{% set timeline_items = [] %}

{# Add periods to timeline #}
{% for period in time_periods %}
    {% set _ = timeline_items.append({
        'type': 'period',
        'year': period,
        'sort_key': period,
        ...
    }) %}
{% endfor %}

{# Add semantic events to timeline #}
{% if semantic_events %}
    {% for event in semantic_events %}
        {% set _ = timeline_items.append({
            'type': 'event',
            'year': event.from_period,
            'sort_key': event.from_period,
            ...
        }) %}
    {% endfor %}
{% endif %}

{# Sort timeline by year #}
{% set sorted_timeline = timeline_items|sort(attribute='sort_key') %}
```

### 2. Backend Routes: `/app/routes/experiments/temporal.py`
**New Endpoints**:
- `GET /experiments/<id>/documents` (line 249): Fetch experiment documents for event linking
- `POST /experiments/<id>/save_semantic_event` (line 290): Create/update semantic event
- `POST /experiments/<id>/remove_semantic_event` (line 384): Delete semantic event
- `POST /experiments/<id>/generate_periods_from_documents` (line 173): Auto-generate periods

**Key Implementation** (lines 290-381):
```python
@experiments_bp.route('/<int:experiment_id>/save_semantic_event', methods=['POST'])
@api_require_login_for_write
def save_semantic_event(experiment_id):
    # Get event data from request
    event_data = request.get_json()

    # Get related documents with UUID
    related_documents = [
        {
            'id': doc.id,
            'uuid': str(doc.uuid),
            'title': doc.title or 'Untitled Document'
        }
        for doc in documents
    ]

    # Save to experiment configuration JSON
    config['semantic_events'] = semantic_events
    experiment.configuration = json.dumps(config)
    db.session.commit()
```

### 3. Service Layer: `/app/services/temporal_service.py`
**Changes**:
- Line 133: Added `semantic_events` to return data
- Lines 310-425: `generate_periods_from_documents()` method
  - Extracts years from `Document.publication_date`
  - Falls back to `created_at` if needed
  - Stores document-to-period mappings

## Known Issues

### ⚠️ Current Bug: Semantic Event Save Error

**Symptom**: When adding a semantic event, JavaScript shows:
```
Error saving semantic event: Unexpected token '<', "<!doctype "... is not valid JSON
```

**Analysis**:
- Error occurs in `saveSemanticEvent()` function (temporal_term_manager.html:1018-1079)
- POST request to `/experiments/${experimentId}/save_semantic_event` returns HTML instead of JSON
- Indicates server-side exception is being thrown before JSON response can be generated

**Possible Causes**:
1. Server-side exception in `save_semantic_event` route
2. Authentication failure (though decorator should handle this)
3. Database error during commit
4. JSON serialization issue with event data

**Debug Steps**:
1. Check Flask logs for Python traceback
2. Add console.log to verify request payload in JavaScript
3. Add try-catch logging to backend route
4. Verify `experiment.configuration` JSON is valid

**Request Payload** (line 1043-1050):
```javascript
const eventData = {
    id: eventId || Date.now().toString(),
    event_type: eventType,
    from_period: parseInt(fromPeriod),
    to_period: toPeriod ? parseInt(toPeriod) : null,
    description: description.trim(),
    related_document_ids: relatedDocIds
};
```

## Technical Architecture

### Data Flow
1. **Page Load**:
   - Flask route calls `temporal_service.get_temporal_ui_data(experiment_id)`
   - Returns time_periods, semantic_events, period_documents, period_metadata
   - Jinja template merges and sorts timeline items server-side

2. **Add Period**:
   - User clicks "Add Period" button → `showAddPeriodDialog()`
   - Updates `timePeriods` array client-side
   - Calls `refreshTimelineUI()` to rebuild DOM

3. **Add Semantic Event**:
   - User clicks "Add Event" → `showAddSemanticEventDialog()`
   - Modal opens with event form
   - On save: POST to `/experiments/<id>/save_semantic_event`
   - Backend updates `experiment.configuration` JSON
   - Returns updated `semantic_events` array
   - Client calls `refreshTimelineUI()` to rebuild DOM

### Database Schema
- **Experiment**: Stores configuration as JSON text field
- **Document**: Has `publication_date` (DATE) field
- **DocumentTemporalMetadata**: Has deprecated `publication_year` field (use Document.publication_date instead)

### Related Models
- `app/models/temporal_experiment.py`:
  - `DocumentTemporalMetadata` (deprecated publication_year field)
  - `OEDTimelineMarker` (OED quotation data)
  - `TermDisciplinaryDefinition` (discipline-specific definitions)
  - `SemanticShiftAnalysis` (identified semantic shifts)

## Configuration Structure

Experiment configuration JSON format:
```json
{
  "time_periods": [1910, 1956, 1995, 2019],
  "start_year": 1910,
  "end_year": 2019,
  "periods_source": "documents",
  "period_documents": {
    "1910": [
      {
        "id": 123,
        "uuid": "abc-123-def",
        "title": "Document Title",
        "date_source": "publication_date"
      }
    ]
  },
  "period_metadata": {
    "1910": {
      "source": "auto-generated",
      "document_count": 1
    }
  },
  "semantic_events": [
    {
      "id": "1732220400000",
      "event_type": "inflection_point",
      "from_period": 1950,
      "to_period": 1960,
      "description": "Major shift in term usage...",
      "related_documents": [
        {
          "id": 124,
          "uuid": "def-456-ghi",
          "title": "Evidence Document"
        }
      ]
    }
  ]
}
```

## UI/UX Features

### Timeline Container
- Flexbox layout with gap-3 (Bootstrap spacing)
- Cards display in chronological order (sorted by year)
- Period and event cards have consistent card design
- Hover effects: shadow increases, slight upward transform

### Card Design
- **Header**: Year/date range + source badge/event type
- **Body**: Documents list (periods) or description (events)
- **Footer**: Action buttons (edit, remove)

### Modals
1. **Manual Period Entry**: Two modes (list or range)
2. **Semantic Event**: Full form with event type, date range, description, related documents

## Migration Notes

### Publication Date Migration
- Script: `/migrations/migrate_publication_dates.py`
- Migrates data from `DocumentTemporalMetadata.publication_year` → `Document.publication_date`
- Run with: `PYTHONPATH=/home/chris/OntExtract venv-ontextract/bin/python migrations/migrate_publication_dates.py`

## BFO + PROV-O Implementation Plan

**Objective**: Transition from JSON-based semantic events to ontology-backed database architecture using BFO for semantic change modeling and PROV-O for analytical provenance tracking.

**Key Architecture Change**: Dual ontology approach
- **BFO + Semantic Change Ontology (SCO)**: Model semantic change *phenomena* (the thing being studied)
- **PROV-O**: Track research *provenance* (who studied it, when, how)

**Reference papers**:
- "Managing Semantic Change in Research" (Rauch et al., 2024)
- "OntExtract: PROV-O Provenance Tracking for Document Analysis Workflows"

**Infrastructure**: Leverages existing OntServe deployment at `https://ontserve.ontorealm.net/`

**OntServe Details**:
- **GitHub**: https://github.com/MatLab-Research/OntServe
- **Local path**: `/home/chris/onto/OntServe`
  - MCP server: `/home/chris/onto/OntServe/servers`
  - Web server: `/home/chris/onto/OntServe/web`
- **Reference implementation**: `/home/chris/onto/proethica` (shows integration patterns)
- **Goal**: Align OntExtract's ontology integration with ProEthica approach

**Why This Approach?**
1. **Proper Ontological Modeling**: BFO's `bfo:Process` correctly models semantic change as temporal processes, not just data artifacts
2. **Reuses Existing Infrastructure**: Integrates with your BFO-based OntServe deployment
3. **Standards Compliant**: Uses W3C (PROV-O, OWL-Time, SKOS) and OBO (BFO) standards
4. **Clear Separation**: Distinguishes what's being studied (semantic change) from the research process (annotation)
5. **Queryable**: Enables SPARQL queries over temporal patterns and provenance chains
6. **Publishable**: Export as proper RDF/OWL for linked open data

### Design Principles

1. **Dual Ontology Architecture**:
   - **BFO + Semantic Change Ontology (SCO)**: Model the *phenomenon* of semantic change
     - `bfo:TemporalRegion` - time periods (1910-1920, etc.)
     - `bfo:Process` - semantic change events (inflection points, stable polysemy, etc.)
     - `skos:Concept` - terms/concepts being studied
   - **PROV-O**: Track *who studied* the phenomenon (analytical provenance)
     - `prov:Activity` - annotation activities
     - `prov:Agent` - researchers, tools
     - `prov:wasAttributedTo` - who created which annotation

2. **Separation of Concerns**:
   - **Period Cards** = temporal containers (objective facts: documents exist in time)
   - **Event Cards** = semantic change phenomena (BFO processes) + researcher annotations (PROV-O)
   - **Object of study** (BFO/SCO) ≠ **research process** (PROV-O)

3. **Ontology-Backed Types**:
   - Event types are URIs from Semantic Change Ontology
   - Enables semantic interoperability and SPARQL queries
   - Integrates with existing BFO-based infrastructure

4. **Evidence-Based Annotations**:
   - Link events to specific document segments (character-level positions)
   - Track provenance: who identified the shift, when, based on what evidence
   - Enable reproducible semantic change analysis

### Phase 1: Semantic Change Ontology + Database Foundation

**Status**: Planning
**Goal**: Create BFO-based Semantic Change Ontology in OntServe and adapt database to use ontology URIs

#### 1.1 Create Semantic Change Ontology (in OntServe)

**Ontology**: `semantic-change-ontology.ttl` (SCO)
**Namespace**: `http://ontextract.org/sco#`
**Deployed to**: `https://ontserve.ontorealm.net/`

```turtle
@prefix sco: <http://ontextract.org/sco#> .
@prefix bfo: <http://purl.obolibrary.org/obo/> .
@prefix time: <http://www.w3.org/2006/time#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix prov: <http://www.w3.org/ns/prov#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .

# Ontology metadata
sco: a owl:Ontology ;
    rdfs:label "Semantic Change Ontology" ;
    rdfs:comment "Ontology for modeling semantic change phenomena in terminology research" ;
    owl:imports <http://purl.obolibrary.org/obo/bfo.owl> ,
                <http://www.w3.org/2006/time> ,
                <http://www.w3.org/2004/02/skos/core> .

# === Semantic Change Event Classes (subclasses of bfo:Process) ===

sco:SemanticChangeEvent a owl:Class ;
    rdfs:subClassOf bfo:BFO_0000015 ;  # bfo:Process
    rdfs:label "Semantic Change Event" ;
    rdfs:comment "A process by which the meaning of a term changes over time" .

sco:InflectionPoint a owl:Class ;
    rdfs:subClassOf sco:SemanticChangeEvent ;
    rdfs:label "Inflection Point" ;
    rdfs:comment "Rapid semantic transition marking shift between distinct meanings" ;
    skos:example "agent 1995: human actor → computational system" .

sco:StablePolysemy a owl:Class ;
    rdfs:subClassOf sco:SemanticChangeEvent ;
    rdfs:label "Stable Polysemy" ;
    rdfs:comment "Multiple distinct meanings coexist without conflict across disciplines" ;
    skos:example "agent 2024: legal person AND autonomous system" .

sco:DomainNetwork a owl:Class ;
    rdfs:subClassOf sco:SemanticChangeEvent ;
    rdfs:label "Domain Network" ;
    rdfs:comment "Development of discipline-specific semantic network" ;
    skos:example "agent in AI: percept-action loop, rationality" .

sco:ConceptualBridge a owl:Class ;
    rdfs:subClassOf sco:SemanticChangeEvent ;
    rdfs:label "Conceptual Bridge" ;
    rdfs:comment "Work that mediates between different disciplinary meanings" ;
    skos:example "Anscombe 1957: legal → philosophical agency" .

sco:SemanticDrift a owl:Class ;
    rdfs:subClassOf sco:SemanticChangeEvent ;
    rdfs:label "Semantic Drift" ;
    rdfs:comment "Gradual meaning change over extended period" .

sco:Emergence a owl:Class ;
    rdfs:subClassOf sco:SemanticChangeEvent ;
    rdfs:label "Emergence" ;
    rdfs:comment "New meaning appears in discourse" .

sco:Decline a owl:Class ;
    rdfs:subClassOf sco:SemanticChangeEvent ;
    rdfs:label "Decline" ;
    rdfs:comment "Meaning becomes obsolete or rare" .

# === Properties for Semantic Change ===

sco:affectsConcept a owl:ObjectProperty ;
    rdfs:label "affects concept" ;
    rdfs:domain sco:SemanticChangeEvent ;
    rdfs:range skos:Concept ;
    rdfs:comment "The term/concept undergoing semantic change" .

sco:occursDuringInterval a owl:ObjectProperty ;
    rdfs:label "occurs during interval" ;
    rdfs:domain sco:SemanticChangeEvent ;
    rdfs:range time:Interval ;
    rdfs:comment "Temporal interval when change occurred" .

sco:hasFromMeaning a owl:ObjectProperty ;
    rdfs:label "has from meaning" ;
    rdfs:domain sco:SemanticChangeEvent ;
    rdfs:range skos:Concept ;
    rdfs:comment "Original/source meaning before change" .

sco:hasToMeaning a owl:ObjectProperty ;
    rdfs:label "has to meaning" ;
    rdfs:domain sco:SemanticChangeEvent ;
    rdfs:range skos:Concept ;
    rdfs:comment "New/target meaning after change" .

sco:evidencedBy a owl:ObjectProperty ;
    rdfs:label "evidenced by" ;
    rdfs:domain sco:SemanticChangeEvent ;
    rdfs:range bfo:BFO_0000016 ;  # bfo:InformationContentEntity (documents)
    rdfs:comment "Document that provides evidence for the semantic change" .

sco:hasConfidence a owl:DatatypeProperty ;
    rdfs:label "has confidence" ;
    rdfs:domain sco:SemanticChangeEvent ;
    rdfs:range xsd:float ;
    rdfs:comment "Researcher confidence in annotation (0.0-1.0)" .
```

**Upload to OntServe**:
```bash
# Deploy ontology to OntServe
curl -X POST https://ontserve.ontorealm.net/api/ontology/upload \
  -H "Content-Type: text/turtle" \
  -d @semantic-change-ontology.ttl
```

**Tasks**:
- [ ] Create `semantic-change-ontology.ttl` with BFO extensions
- [ ] Upload to OntServe instance
- [ ] Verify ontology loads correctly
- [ ] Test SPARQL queries against ontology

#### 1.2 MCP Integration Layer Architecture

**Design principle**: Isolate external MCP server orchestration behind a single integration layer

**Architecture**:
```
┌─────────────────────────────────────────┐
│   Application Layer (Routes/Services)  │
│   - semantic_event_service.py          │
│   - temporal_service.py                │
└──────────────┬──────────────────────────┘
               │
               ↓
┌─────────────────────────────────────────┐
│   Ontology Client (ontserve_client.py) │
│   - get_event_types()                   │
│   - query_sparql()                      │
│   - validate_uri()                      │
└──────────────┬──────────────────────────┘
               │
               ↓
┌─────────────────────────────────────────┐
│   MCP Integration Layer (mcp_client.py) │
│   - Single point for MCP communication  │
│   - Connection pooling                  │
│   - Error handling & fallback           │
└──────────────┬──────────────────────────┘
               │
               ↓
┌─────────────────────────────────────────┐
│   External MCP Server                   │
│   /home/chris/onto/OntServe/servers     │
│   OR                                    │
│   OntServe Web API (HTTP fallback)      │
│   https://ontserve.ontorealm.net/       │
└─────────────────────────────────────────┘
```

**Implementation** (`app/services/mcp_client.py`):

```python
"""
MCP Integration Layer
Single abstraction for all external MCP server communication.
"""
from typing import Dict, Any, Optional
import requests
from contextlib import contextmanager

class MCPClient:
    """
    Abstraction layer for MCP server communication.
    Provides fallback to HTTP API if MCP server unavailable.
    """

    def __init__(self, mcp_server_path: str = None, http_fallback_url: str = None):
        self.mcp_server_path = mcp_server_path or "/home/chris/onto/OntServe/servers"
        self.http_fallback_url = http_fallback_url or "https://ontserve.ontorealm.net"
        self._use_mcp = self._check_mcp_available()

    def _check_mcp_available(self) -> bool:
        """Check if MCP server is available"""
        try:
            # Check if MCP server is running
            # Implementation depends on OntServe MCP protocol
            return os.path.exists(self.mcp_server_path)
        except Exception:
            return False

    def call_mcp(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call MCP server method with fallback to HTTP API.

        Args:
            method: MCP method name (e.g., "ontology.query_sparql")
            params: Method parameters

        Returns:
            Response from MCP server or HTTP API
        """
        if self._use_mcp:
            try:
                return self._call_mcp_server(method, params)
            except Exception as e:
                # Log MCP failure, fall back to HTTP
                print(f"MCP call failed: {e}, falling back to HTTP API")
                return self._call_http_api(method, params)
        else:
            return self._call_http_api(method, params)

    def _call_mcp_server(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Direct MCP server communication"""
        # Implementation depends on OntServe MCP protocol
        # Review ProEthica for reference implementation
        raise NotImplementedError("MCP protocol implementation pending")

    def _call_http_api(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """HTTP API fallback"""
        # Map MCP method to HTTP endpoint
        endpoint_map = {
            "ontology.list_classes": "/api/ontology/classes",
            "ontology.query_sparql": "/api/sparql/query",
            "ontology.upload": "/api/ontology/upload"
        }

        endpoint = endpoint_map.get(method)
        if not endpoint:
            raise ValueError(f"Unknown MCP method: {method}")

        response = requests.post(
            f"{self.http_fallback_url}{endpoint}",
            json=params,
            timeout=30
        )
        response.raise_for_status()
        return response.json()


# Global MCP client instance
mcp_client = MCPClient()
```

**Ontology Client** (`app/services/ontserve_client.py`):

```python
"""
OntServe Client
High-level ontology operations using MCP integration layer.
"""
from typing import List, Dict, Any
from functools import lru_cache
from .mcp_client import mcp_client

class OntServeClient:
    """Client for OntServe ontology operations"""

    def __init__(self):
        self.namespace = "http://ontextract.org/sco#"

    @lru_cache(maxsize=1)
    def get_event_types(self) -> List[Dict[str, Any]]:
        """
        Fetch semantic event types from SCO ontology.
        Cached for application lifetime.

        Returns:
            List of event types with URIs, labels, colors, icons
        """
        # Use MCP layer to query ontology
        sparql = """
        PREFIX sco: <http://ontextract.org/sco#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

        SELECT ?eventType ?label ?comment ?example
        WHERE {
            ?eventType rdfs:subClassOf* sco:SemanticChangeEvent .
            ?eventType rdfs:label ?label .
            OPTIONAL { ?eventType rdfs:comment ?comment }
            OPTIONAL { ?eventType skos:example ?example }
        }
        """

        result = mcp_client.call_mcp("ontology.query_sparql", {
            "ontology": "semantic-change-ontology",
            "query": sparql
        })

        # Transform SPARQL results to UI format
        event_types = []
        for binding in result.get("results", {}).get("bindings", []):
            uri = binding["eventType"]["value"]
            event_name = uri.split("#")[-1]

            event_types.append({
                "uri": uri,
                "name": event_name,
                "label": binding["label"]["value"],
                "description": binding.get("comment", {}).get("value", ""),
                "color": self._get_color_for_type(event_name),
                "icon": self._get_icon_for_type(event_name)
            })

        return event_types

    def validate_event_uri(self, uri: str) -> bool:
        """Validate that URI exists in SCO ontology"""
        try:
            result = mcp_client.call_mcp("ontology.validate_uri", {
                "ontology": "semantic-change-ontology",
                "uri": uri
            })
            return result.get("valid", False)
        except Exception:
            return False

    def _get_color_for_type(self, event_name: str) -> str:
        """Map event type to UI color (temporary until stored in ontology)"""
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
        """Map event type to FontAwesome icon"""
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
ontserve_client = OntServeClient()
```

**Benefits of MCP Integration Layer**:
1. **Single point of control**: All MCP communication goes through one module
2. **Fallback resilience**: Automatic fallback to HTTP API if MCP unavailable
3. **Easy testing**: Mock the MCP layer instead of individual calls
4. **Protocol isolation**: Application code doesn't know about MCP details
5. **Caching**: Centralized cache management for ontology data
6. **Connection pooling**: Reuse MCP connections across requests

**Tasks**:
- [ ] Review ProEthica's MCP integration approach
- [ ] Implement `mcp_client.py` with MCP protocol support
- [ ] Implement `ontserve_client.py` with SPARQL queries
- [ ] Add startup hook to warm ontology cache
- [ ] Add health check endpoint for MCP connection status

#### 1.3 Update Database Schema for Ontology URIs

**Modified tables** (in `app/models/provenance.py`):

```python
# PROV-O tables for analytical provenance
class ProvenanceAgent(db.Model):
    """PROV-O Agent: Person or software that performs activities"""
    __tablename__ = 'provenance_agents'

    id = db.Column(db.Integer, primary_key=True)

    # Ontology-backed type (PROV-O Agent subclass)
    agent_type_uri = db.Column(db.String(500), nullable=False)
    # e.g., "http://www.w3.org/ns/prov#Person" or "http://www.w3.org/ns/prov#SoftwareAgent"

    name = db.Column(db.String(200), nullable=False)
    version = db.Column(db.String(50))  # For tools: spaCy 3.8.11

    # For human agents, link to User
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    # For software agents, store configuration
    configuration = db.Column(JSONB)


class ProvenanceActivity(db.Model):
    """PROV-O Activity: Process that generates annotations"""
    __tablename__ = 'provenance_activities'

    id = db.Column(db.Integer, primary_key=True)

    # Activity type (e.g., "annotate_semantic_event")
    activity_type = db.Column(db.String(50), nullable=False)

    # When activity occurred
    started_at = db.Column(db.DateTime, nullable=False)
    ended_at = db.Column(db.DateTime)

    # Configuration used for this activity
    parameters = db.Column(JSONB)

    # Which agent performed this activity (PROV-O: wasAssociatedWith)
    agent_id = db.Column(db.Integer, db.ForeignKey('provenance_agents.id'))
```

#### 1.3 Create Semantic Event Schema with Ontology URIs

**New tables** (in `app/models/semantic_events.py`):

```python
class SemanticEvent(db.Model):
    """
    Semantic change phenomenon (BFO process) with researcher annotation (PROV-O).
    Represents both:
    - The semantic change itself (modeled in SCO ontology)
    - The research annotation of that change (PROV-O provenance)
    """
    __tablename__ = 'semantic_events'

    id = db.Column(db.Integer, primary_key=True)

    # === Ontology URIs (BFO + SCO) ===

    # Event type from Semantic Change Ontology
    event_type_uri = db.Column(db.String(500), nullable=False)
    # e.g., "http://ontextract.org/sco#InflectionPoint"

    # Link to SKOS concept being studied
    concept_uri = db.Column(db.String(500))
    # e.g., "http://ontextract.org/terms/agent"

    # Link to BFO temporal region
    temporal_region_uri = db.Column(db.String(500))
    # e.g., "http://ontextract.org/temporal/1995-2020"

    # === Database fields for query performance ===

    # Experiment context
    experiment_id = db.Column(db.Integer,
        db.ForeignKey('experiments.id'), nullable=False)

    # Temporal scope (cached from ontology for SQL queries)
    from_period = db.Column(db.Integer, nullable=False)
    to_period = db.Column(db.Integer)  # Nullable for point events

    # Human-readable description
    description = db.Column(db.Text, nullable=False)

    # Researcher confidence (0.0-1.0)
    confidence = db.Column(db.Float)

    # === PROV-O Provenance ===

    # Link to annotation activity (PROV-O: wasGeneratedBy)
    annotation_activity_id = db.Column(db.Integer,
        db.ForeignKey('provenance_activities.id'))

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    # === Relationships ===

    evidence_links = db.relationship('SemanticEventEvidence',
        back_populates='semantic_event', cascade='all, delete-orphan')

    annotation_activity = db.relationship('ProvenanceActivity',
        foreign_keys=[annotation_activity_id])


class SemanticEventEvidence(db.Model):
    """
    Links semantic events to supporting document segments.
    Represents evidence chain: SemanticEvent --(evidencedBy)--> Document/Segment
    """
    __tablename__ = 'semantic_event_evidence'

    id = db.Column(db.Integer, primary_key=True)

    semantic_event_id = db.Column(db.Integer,
        db.ForeignKey('semantic_events.id'), nullable=False)

    # Link to document (BFO: InformationContentEntity)
    document_id = db.Column(db.Integer,
        db.ForeignKey('documents.id'), nullable=False)

    # Optional URI for document in ontology
    document_uri = db.Column(db.String(500))
    # e.g., "http://ontextract.org/document/{uuid}"

    # Optional: link to specific segment (from ProcessingArtifact)
    segment_id = db.Column(db.Integer,
        db.ForeignKey('processing_artifacts.id'))

    # Character-level position in document
    char_start = db.Column(db.Integer)
    char_end = db.Column(db.Integer)

    # Extracted text (for display)
    text_snippet = db.Column(db.Text)

    # Evidence type
    evidence_type = db.Column(db.String(50))
    # Types: 'primary', 'supporting', 'contradictory'

    # Researcher's note about this evidence
    note = db.Column(db.Text)

    # Relationships
    semantic_event = db.relationship('SemanticEvent',
        back_populates='evidence_links')
```

#### 1.3 PROV-O Relationship Mapping

**Implementation** (in `app/services/provenance_service.py`):

```python
def create_semantic_event_with_provenance(
    experiment_id: int,
    event_type: str,
    from_period: int,
    to_period: int,
    description: str,
    researcher_id: int,
    evidence_documents: List[int] = None
) -> SemanticEvent:
    """
    Create semantic event with full PROV-O provenance chain.

    PROV-O Relationships:
    - wasAttributedTo: Event attributed to researcher
    - wasGeneratedBy: Event generated by annotation activity
    - wasDerivedFrom: Event derived from document analysis
    - used: Annotation activity used source documents
    """

    # 1. Get or create researcher agent
    agent = ProvenanceAgent.query.filter_by(
        agent_type='researcher',
        user_id=researcher_id
    ).first()

    if not agent:
        agent = ProvenanceAgent(
            agent_type='researcher',
            name=User.query.get(researcher_id).username,
            user_id=researcher_id
        )
        db.session.add(agent)

    # 2. Create annotation activity
    activity = ProvenanceActivity(
        activity_type='annotate_semantic_event',
        started_at=datetime.utcnow(),
        ended_at=datetime.utcnow(),
        agent_id=agent.id,
        parameters={
            'event_type': event_type,
            'from_period': from_period,
            'to_period': to_period
        }
    )
    db.session.add(activity)
    db.session.flush()  # Get activity.id

    # 3. Create PROV-O entity for this semantic event
    entity = ProvenanceEntity(
        entity_type='semantic_event',
        generated_by_activity_id=activity.id,
        metadata={
            'event_type': event_type,
            'description': description
        }
    )
    db.session.add(entity)
    db.session.flush()  # Get entity.id

    # 4. Create semantic event record
    event = SemanticEvent(
        entity_id=entity.id,
        experiment_id=experiment_id,
        event_type=event_type,
        from_period=from_period,
        to_period=to_period,
        description=description
    )
    db.session.add(event)
    db.session.flush()

    # 5. Link evidence documents
    if evidence_documents:
        for doc_id in evidence_documents:
            evidence = SemanticEventEvidence(
                semantic_event_id=event.id,
                document_id=doc_id,
                evidence_type='primary'
            )
            db.session.add(evidence)

    db.session.commit()
    return event
```

#### 1.4 Migration Strategy

**Alembic migration** to:
1. Create new PROV-O tables
2. Migrate existing semantic events from JSON to database
3. Create provenance records for historical events
4. Add foreign key constraints

**Migration script** (`migrations/versions/xxx_add_prov_o_tables.py`):
```python
def upgrade():
    # Create PROV-O tables
    op.create_table('provenance_agents', ...)
    op.create_table('provenance_activities', ...)
    op.create_table('provenance_entities', ...)
    op.create_table('semantic_events', ...)
    op.create_table('semantic_event_evidence', ...)

    # Migrate existing data from experiment.configuration JSON
    # to semantic_events table with retroactive provenance
```

**Tasks**:
- [ ] Create `app/models/provenance.py` with PROV-O base classes
- [ ] Create `app/models/semantic_events.py` with event schema
- [ ] Create `app/services/provenance_service.py` with CRUD operations
- [ ] Write Alembic migration script
- [ ] Test migration with existing experiment data
- [ ] Update backend routes to use new models instead of JSON

### Phase 2: Enhanced Event Cards with Evidence

**Status**: Planning
**Goal**: Improve event card UI to show provenance and evidence links

#### 2.1 Event Type Vocabulary (from Research)

Based on "Managing Semantic Change in Research" and OntExtract papers:

```python
# app/utils/semantic_event_types.py

SEMANTIC_EVENT_TYPES = {
    'inflection_point': {
        'label': 'Inflection Point',
        'description': 'Major semantic shift marking transition between meanings',
        'color': '#6f42c1',  # purple
        'icon': 'fas fa-turn-up',
        'examples': [
            '"agent" 1995: human → computational',
            '"ontology" 1993: philosophy → information science'
        ]
    },
    'stable_polysemy': {
        'label': 'Stable Polysemy',
        'description': 'Multiple distinct meanings coexist without conflict',
        'color': '#20c997',  # teal
        'icon': 'fas fa-code-branch',
        'examples': [
            '"agent" 2024: legal person AND autonomous system',
            'Parallel meanings across disciplines'
        ]
    },
    'domain_network': {
        'label': 'Domain Network',
        'description': 'Domain-specific semantic network develops',
        'color': '#fd7e14',  # orange
        'icon': 'fas fa-project-diagram',
        'examples': [
            '"agent" in AI: percept-action loop, rationality',
            'Specialized terminology within field'
        ]
    },
    'conceptual_bridge': {
        'label': 'Conceptual Bridge',
        'description': 'Work mediates between different meanings',
        'color': '#17a2b8',  # cyan
        'icon': 'fas fa-link',
        'examples': [
            'Anscombe 1957: legal → philosophical agency'
        ]
    },
    'semantic_drift': {
        'label': 'Semantic Drift',
        'description': 'Gradual meaning change over extended period',
        'color': '#d63384',  # pink
        'icon': 'fas fa-water',
        'examples': []
    },
    'emergence': {
        'label': 'Emergence',
        'description': 'New meaning appears in discourse',
        'color': '#198754',  # green
        'icon': 'fas fa-seedling',
        'examples': []
    },
    'decline': {
        'label': 'Decline',
        'description': 'Meaning becomes obsolete or rare',
        'color': '#dc3545',  # red
        'icon': 'fas fa-arrow-trend-down',
        'examples': []
    }
}
```

#### 2.2 Event Card Enhancements

**Template updates** (`temporal_term_manager.html`):

```html
<!-- Event card with provenance and evidence -->
<div class="card event-card mb-3"
     style="border-left: 4px solid {{ event_color }}">

  <!-- Card Header: Event Type and Temporal Scope -->
  <div class="card-header d-flex justify-content-between align-items-center">
    <div>
      <i class="{{ event_icon }}"></i>
      <strong>{{ event_label }}</strong>
      <span class="text-muted ms-2">
        {{ event.from_period }}
        {% if event.to_period %}→ {{ event.to_period }}{% endif %}
      </span>
    </div>

    <!-- Provenance badge -->
    <div>
      <span class="badge bg-secondary"
            title="Annotated by {{ event.researcher.username }} on {{ event.created_at }}">
        <i class="fas fa-user"></i> {{ event.researcher.username }}
      </span>
      {% if event.confidence %}
      <span class="badge bg-info">
        {{ (event.confidence * 100)|int }}% confidence
      </span>
      {% endif %}
    </div>
  </div>

  <!-- Card Body: Description and Evidence -->
  <div class="card-body">
    <p class="card-text">{{ event.description }}</p>

    <!-- Evidence Section -->
    {% if event.evidence_links %}
    <div class="evidence-section mt-3">
      <h6 class="text-muted mb-2">
        <i class="fas fa-book-open"></i> Evidence ({{ event.evidence_links|length }})
      </h6>

      <div class="list-group">
        {% for evidence in event.evidence_links %}
        <a href="/document/{{ evidence.document.uuid }}"
           class="list-group-item list-group-item-action"
           target="_blank">

          <div class="d-flex justify-content-between align-items-start">
            <div>
              <div class="fw-bold">{{ evidence.document.title }}</div>

              <!-- Show text snippet if available -->
              {% if evidence.text_snippet %}
              <blockquote class="text-muted small mt-1 mb-0">
                "{{ evidence.text_snippet|truncate(120) }}"
              </blockquote>
              {% endif %}

              {% if evidence.note %}
              <small class="text-info">
                <i class="fas fa-sticky-note"></i> {{ evidence.note }}
              </small>
              {% endif %}
            </div>

            <!-- Evidence type badge -->
            <span class="badge bg-{{ evidence_type_color(evidence.evidence_type) }}">
              {{ evidence.evidence_type }}
            </span>
          </div>
        </a>
        {% endfor %}
      </div>
    </div>
    {% endif %}
  </div>

  <!-- Card Footer: Actions -->
  <div class="card-footer">
    <button class="btn btn-sm btn-outline-primary"
            onclick="editSemanticEvent('{{ event.id }}')">
      <i class="fas fa-edit"></i> Edit
    </button>
    <button class="btn btn-sm btn-outline-danger"
            onclick="removeSemanticEvent('{{ event.id }}')">
      <i class="fas fa-trash"></i> Remove
    </button>
    <button class="btn btn-sm btn-outline-secondary"
            onclick="showProvenance('{{ event.id }}')">
      <i class="fas fa-history"></i> View Provenance
    </button>
  </div>
</div>
```

#### 2.3 Provenance Viewer Modal

**New modal** for displaying complete PROV-O chain:

```html
<div class="modal fade" id="provenanceModal">
  <div class="modal-dialog modal-lg">
    <div class="modal-content">
      <div class="modal-header">
        <h5 class="modal-title">Annotation Provenance</h5>
        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
      </div>

      <div class="modal-body">
        <!-- PROV-O visualization -->
        <div class="provenance-chain">
          <div class="prov-entity">
            <h6>Entity: Semantic Event</h6>
            <dl>
              <dt>Type:</dt>
              <dd id="prov-event-type"></dd>
              <dt>Created:</dt>
              <dd id="prov-created-at"></dd>
            </dl>
          </div>

          <div class="prov-relationship">
            <i class="fas fa-arrow-down"></i>
            <span>wasGeneratedBy</span>
          </div>

          <div class="prov-activity">
            <h6>Activity: Annotation</h6>
            <dl>
              <dt>Activity Type:</dt>
              <dd>annotate_semantic_event</dd>
              <dt>Parameters:</dt>
              <dd><pre id="prov-parameters"></pre></dd>
            </dl>
          </div>

          <div class="prov-relationship">
            <i class="fas fa-arrow-down"></i>
            <span>wasAssociatedWith</span>
          </div>

          <div class="prov-agent">
            <h6>Agent: Researcher</h6>
            <dl>
              <dt>Name:</dt>
              <dd id="prov-agent-name"></dd>
              <dt>Agent Type:</dt>
              <dd>researcher</dd>
            </dl>
          </div>

          <div class="prov-relationship">
            <i class="fas fa-arrow-down"></i>
            <span>used</span>
          </div>

          <div class="prov-entities">
            <h6>Source Documents</h6>
            <ul id="prov-source-docs"></ul>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
```

**Tasks**:
- [ ] Update event card template with provenance display
- [ ] Add evidence section to event cards
- [ ] Create provenance viewer modal
- [ ] Update semantic event modal to include evidence linking
- [ ] Add confidence score input (optional slider 0-100%)
- [ ] Update JavaScript functions for new schema

### Phase 3: Segment-Level Evidence Linking

**Status**: Planning
**Goal**: Link semantic events to specific text passages, not just whole documents

#### 3.1 Text Selection Interface

**JavaScript for text selection** in document viewer:

```javascript
// When viewing a document, allow text selection for evidence
function enableEvidenceSelection(documentId) {
    const documentText = document.getElementById('document-content');

    documentText.addEventListener('mouseup', function() {
        const selection = window.getSelection();
        const selectedText = selection.toString().trim();

        if (selectedText.length > 0) {
            // Calculate character positions
            const range = selection.getRangeAt(0);
            const charStart = getCharacterOffsetWithin(range.startContainer, documentText);
            const charEnd = charStart + selectedText.length;

            // Show "Add as Evidence" button
            showEvidenceButton(documentId, selectedText, charStart, charEnd);
        }
    });
}

function showEvidenceButton(documentId, text, charStart, charEnd) {
    // Create floating button near selection
    const button = document.createElement('button');
    button.className = 'btn btn-sm btn-primary evidence-button';
    button.innerHTML = '<i class="fas fa-link"></i> Add as Evidence';
    button.onclick = () => {
        openEvidenceLinkDialog(documentId, text, charStart, charEnd);
    };

    // Position near selection
    // ... positioning logic
}
```

#### 3.2 Evidence Linking Workflow

1. **User workflow**:
   - View document in experiment
   - Select relevant text passage
   - Click "Add as Evidence"
   - Choose which semantic event this supports
   - Add optional note about why this text is evidence
   - Save link

2. **Backend storage**:
```python
evidence = SemanticEventEvidence(
    semantic_event_id=event_id,
    document_id=document_id,
    char_start=char_start,
    char_end=char_end,
    text_snippet=text[char_start:char_end],
    evidence_type='primary',
    note=user_note
)
```

3. **Display in event card**:
   - Show clickable evidence links
   - Clicking opens document and highlights the specific passage
   - Deep link format: `/document/{uuid}#evidence-{char_start}-{char_end}`

**Tasks**:
- [ ] Add text selection capability to document viewer
- [ ] Create "Add as Evidence" floating button
- [ ] Build evidence linking dialog
- [ ] Implement deep linking to document passages
- [ ] Add text highlighting for evidence segments
- [ ] Update event cards to show segment-level evidence

### Phase 4: Integration with Existing ProcessingArtifacts

**Status**: Planning
**Goal**: Connect semantic events to ProcessingArtifact segments from document analysis

#### 4.1 Leverage Existing Segmentation

The system already has:
- `ProcessingArtifact` table with character-level positions
- Paragraph and sentence segmentation
- Entity extraction with positions

**Integration approach**:
```python
def link_event_to_segments(
    event_id: int,
    segment_ids: List[int]
) -> List[SemanticEventEvidence]:
    """
    Link semantic event to existing ProcessingArtifact segments.
    Useful when event is identified through automated analysis.
    """
    evidence_links = []

    for segment_id in segment_ids:
        segment = ProcessingArtifact.query.get(segment_id)

        evidence = SemanticEventEvidence(
            semantic_event_id=event_id,
            document_id=segment.document_id,
            segment_id=segment_id,
            char_start=segment.metadata.get('char_start'),
            char_end=segment.metadata.get('char_end'),
            text_snippet=segment.content[:200],  # Truncate for display
            evidence_type='automated'
        )
        evidence_links.append(evidence)
        db.session.add(evidence)

    db.session.commit()
    return evidence_links
```

#### 4.2 Automated Event Detection (Future)

**Potential workflow**:
1. Run document processing (segmentation, extraction, embeddings)
2. Analyze ProcessingArtifacts for semantic patterns
3. Suggest potential semantic events to researcher
4. Researcher reviews and approves, creating SemanticEvent with provenance

This leverages existing infrastructure while maintaining human oversight.

**Tasks**:
- [ ] Add segment_id foreign key to SemanticEventEvidence
- [ ] Create helper functions to link events to existing segments
- [ ] Update UI to show both manual selections and automated segments
- [ ] (Future) Implement automated event suggestion based on ProcessingArtifacts

### Phase 5: RDF Export (Future Enhancement)

**Status**: Planning
**Goal**: Export temporal timeline as RDF using PROV-O, SKOS, Dublin Core

#### 5.1 Ontology Mapping

```python
# app/services/rdf_export.py

from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import RDF, RDFS, DCTERMS, XSD

# Define namespaces
PROV = Namespace("http://www.w3.org/ns/prov#")
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")
ONTEXTRACT = Namespace("http://ontextract.org/ns#")

def export_experiment_to_rdf(experiment_id: int) -> str:
    """Export experiment timeline as RDF Turtle"""
    g = Graph()
    g.bind("prov", PROV)
    g.bind("skos", SKOS)
    g.bind("dcterms", DCTERMS)
    g.bind("ontex", ONTEXTRACT)

    experiment = Experiment.query.get(experiment_id)

    # Experiment as PROV Entity
    exp_uri = URIRef(f"http://ontextract.org/experiment/{experiment_id}")
    g.add((exp_uri, RDF.type, PROV.Entity))
    g.add((exp_uri, DCTERMS.title, Literal(experiment.name)))

    # Semantic events
    events = SemanticEvent.query.filter_by(
        experiment_id=experiment_id
    ).all()

    for event in events:
        event_uri = URIRef(f"http://ontextract.org/event/{event.id}")

        # Event as PROV Entity
        g.add((event_uri, RDF.type, PROV.Entity))
        g.add((event_uri, RDF.type, ONTEXTRACT[event.event_type]))
        g.add((event_uri, RDFS.label, Literal(event.description)))

        # Temporal scope
        g.add((event_uri, ONTEXTRACT.fromPeriod,
               Literal(event.from_period, datatype=XSD.integer)))
        if event.to_period:
            g.add((event_uri, ONTEXTRACT.toPeriod,
                   Literal(event.to_period, datatype=XSD.integer)))

        # Provenance: wasAttributedTo researcher
        entity = ProvenanceEntity.query.get(event.entity_id)
        activity = entity.generated_by_activity
        agent = activity.agent

        agent_uri = URIRef(f"http://ontextract.org/agent/{agent.id}")
        g.add((event_uri, PROV.wasAttributedTo, agent_uri))

        # Evidence documents
        for evidence in event.evidence_links:
            doc_uri = URIRef(f"http://ontextract.org/document/{evidence.document.uuid}")
            g.add((event_uri, DCTERMS.references, doc_uri))

    # Serialize to Turtle
    return g.serialize(format='turtle')
```

**Tasks** (Future):
- [ ] Implement RDF export service
- [ ] Create ONTEXTRACT vocabulary for semantic event types
- [ ] Add export button to timeline interface
- [ ] Support JSON-LD format for web publishing
- [ ] Validate RDF output against PROV-O constraints

## Next Steps

### Immediate (Fix Current Bug)
1. **Debug semantic event save error**:
   - [ ] Check Flask logs for Python traceback
   - [ ] Add logging to `save_semantic_event` route
   - [ ] Verify JSON serialization of event data
   - [ ] Test with minimal payload

### Phase 1: BFO + PROV-O Foundation (Priority)
1. **Semantic Change Ontology (in OntServe)**:
   - [ ] Create `semantic-change-ontology.ttl` extending BFO
   - [ ] Upload to OntServe at https://ontserve.ontorealm.net/
   - [ ] Test SPARQL queries against ontology
   - [ ] Document event type URIs for UI integration

2. **Database Schema**:
   - [ ] Create `app/models/provenance.py` with PROV-O classes
   - [ ] Create `app/models/semantic_events.py` with ontology URI fields
   - [ ] Write Alembic migration script
   - [ ] Test migration with existing data

3. **OntServe Integration**:
   - [ ] Review ProEthica integration patterns (`/home/chris/onto/proethica`)
   - [ ] **Create MCP integration layer** (`app/services/mcp_client.py`)
     - Single abstraction for all external MCP server communication
     - Isolates OntServe MCP server calls from rest of codebase
     - Provides fallback to direct HTTP API if MCP unavailable
   - [ ] Create `app/services/ontserve_client.py` (uses MCP layer)
     - Ontology-specific operations (fetch classes, query SPARQL)
     - Caching layer for ontology data
   - [ ] Implement ontology caching (fetch event types on startup)
   - [ ] Add UI dropdowns populated from ontology
   - [ ] Align approach with ProEthica's ontology usage patterns

4. **Service Layer**:
   - [ ] Create `app/services/semantic_event_service.py`
   - [ ] Implement CRUD with BFO URIs and PROV-O provenance
   - [ ] Update backend routes to use new models

5. **Testing**:
   - [ ] Create semantic event with ontology URIs
   - [ ] Query provenance chain
   - [ ] Verify BFO and PROV-O relationships
   - [ ] Test RDF export

### Phase 2: Enhanced Event Cards
1. **UI Updates**:
   - [ ] Update event card template with provenance display
   - [ ] Add evidence section to event cards
   - [ ] Create provenance viewer modal
   - [ ] Update semantic event modal for evidence linking

2. **JavaScript**:
   - [ ] Update `saveSemanticEvent()` for new schema
   - [ ] Add provenance display functions
   - [ ] Implement evidence link management

### Phase 3: Segment-Level Evidence
1. **Text Selection**:
   - [ ] Add text selection to document viewer
   - [ ] Create "Add as Evidence" button
   - [ ] Build evidence linking dialog

2. **Deep Linking**:
   - [ ] Implement document deep links with highlighting
   - [ ] Update evidence display in event cards

### Future Enhancements
1. **Automated Analysis**:
   - Link events to ProcessingArtifacts
   - Suggest potential events based on analysis

2. **RDF Export**:
   - Export timeline as PROV-O/SKOS RDF
   - Support linked open data publishing

3. **Visualization**:
   - Add graphical timeline view (D3.js)
   - Show provenance chains visually

## Testing Checklist

- [ ] Auto-generate periods from documents
- [ ] Manual period entry (list mode)
- [ ] Manual period entry (range mode)
- [ ] Add individual period
- [ ] Remove period
- [ ] Add semantic event (FAILING - current bug)
- [ ] Edit semantic event
- [ ] Remove semantic event
- [ ] Document links work correctly
- [ ] Timeline sorts correctly by year
- [ ] Period cards display document counts
- [ ] Event cards display correct colors by type

## References

- **Experiment Type**: `temporal_evolution`
- **UI Route**: `/experiments/<id>/manage_temporal_terms`
- **Main Template**: `app/templates/experiments/temporal_term_manager.html`
- **Backend Routes**: `app/routes/experiments/temporal.py`
- **Service Layer**: `app/services/temporal_service.py`
- **Date Parser**: `app/utils/date_parser.py`
- **Models**: `app/models/temporal_experiment.py`

## Contact Points

If resuming this work, focus on:
1. Debugging the semantic event save error (check Flask logs first)
2. Consider adding database table for semantic events instead of JSON storage
3. Test all CRUD operations thoroughly
4. Consider adding event validation (e.g., from_period < to_period)
