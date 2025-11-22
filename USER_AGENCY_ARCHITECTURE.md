# OntExtract User Agency Architecture

**Date**: 2025-11-22
**Status**: ARCHITECTURAL REVIEW
**Purpose**: Ensure OntExtract remains a user-empowered tool with optional LLM enhancement, not an LLM-dependent system

---

## Core Principle

**User-First Design**: All core functionality must work without an Anthropic API key. LLM features are enhancements, not requirements.

---

## Current Implementation Audit

### Features That Work WITHOUT LLM (Standalone Mode)

#### Document Management
- Upload documents (PDF, TXT, DOCX)
- Manual metadata entry (title, publication date, author)
- Document organization by experiment
- File storage and retrieval

#### Temporal Timeline (Fully User-Driven)
- **Manual Period Creation**: User defines time periods with start/end years
- **OED Period Import**: Auto-generated periods from OED data (no LLM)
- **Semantic Event Annotation**: User creates event cards with:
  - Event type selection (from dropdown)
  - Period range selection
  - Document linking
  - Description text
- **Timeline Visualization**: Interactive chronological display
- **Period-Document Linking**: Manual association of documents to periods

#### NLP Tool Execution (Manual Mode)
- Named Entity Recognition (spaCy)
- Temporal Expression Extraction
- Definition Extraction
- Text Segmentation
- Embedding Generation
- Sentiment Analysis
- Keyword Extraction
- User selects tools manually through UI
- Results displayed immediately

#### Data Management
- Export experiment data (JSON)
- View processing results
- Download extracted entities/definitions
- Database backup/restore

### Features That REQUIRE LLM (API-Enhanced Mode)

#### LLM Orchestration Workflow (Optional)
- Stage 1: Analyze - LLM examines experiment goals
- Stage 2: Recommend - LLM suggests tool strategies
- Stage 3: Review - Human approves LLM recommendations
- Stage 4: Execute - Same tools as standalone mode
- Stage 5: Synthesize - LLM generates cross-document insights

**Status**: Clearly marked as optional enhancement

#### Context Anchor Enhancement
- Basic extraction: User-driven (regex patterns)
- LLM enhancement: Optional semantic analysis

---

## BFO + PROV-O Plan Review

### SAFE: Features That Should Stay User-Driven

#### Event Type Selection
**Current Plan**: Fetch event types from OntServe ontology
**Correct**: Event types displayed in dropdown for USER selection
**AVOID**: LLM auto-selecting event types

**Implementation**:
```python
# GOOD: User-driven UI
@app.route('/experiments/<id>/semantic_events/types')
def get_event_types(experiment_id):
    """Fetch event types from ontology for user selection"""
    event_types = ontserve_client.get_semantic_change_classes()
    return jsonify([{
        'uri': t.uri,
        'label': t.label,
        'definition': t.definition,
        'citation': t.citation
    } for t in event_types])

# Frontend: User selects from dropdown
<select name="event_type_uri">
  <option value="sco:Pejoration">Pejoration (negative shift)</option>
  <option value="sco:Amelioration">Amelioration (positive shift)</option>
  ...
</select>
```

#### Semantic Event Creation
**Current Plan**: Manual annotation with ontology backing
**Correct**: User creates events, ontology provides metadata
**AVOID**: LLM auto-detecting semantic changes

**Implementation**:
```python
# User-initiated event creation
@app.route('/experiments/<id>/semantic_events', methods=['POST'])
def create_semantic_event(experiment_id):
    """User creates semantic event by selecting type and periods"""
    data = request.get_json()

    # Get ontology metadata for selected type
    event_type_metadata = ontserve_client.get_class_metadata(
        data['event_type_uri']
    )

    # Store user-created event with ontology URI
    event = SemanticEvent(
        experiment_id=experiment_id,
        event_type_uri=data['event_type_uri'],
        event_type_label=event_type_metadata['label'],
        from_period_id=data['from_period'],
        to_period_id=data['to_period'],
        description=data['description'],  # User-written
        created_by=current_user.id
    )
    db.session.add(event)
    db.session.commit()
```

#### Period Definition
**Current Plan**: Manual and OED-generated periods
**Correct**: User defines periods or imports from OED
**AVOID**: LLM auto-generating period boundaries

**Status**: Already correctly implemented

### ENHANCEMENT: Optional LLM Features

#### Semantic Event Suggestions (Optional)
**If LLM available**: Suggest potential semantic changes based on analysis
**If no LLM**: User identifies events manually
**Implementation**: Feature flag, graceful degradation

```python
# Optional LLM enhancement
if current_app.config.get('ANTHROPIC_API_KEY'):
    suggestions = llm_service.suggest_semantic_events(
        experiment_id,
        documents
    )
    # Display as suggestions, not auto-created
    return render_template('...',
        suggestions=suggestions,
        mode='llm_enhanced'
    )
else:
    # Standalone mode: user-driven only
    return render_template('...',
        suggestions=[],
        mode='standalone'
    )
```

#### Cross-Period Analysis (Optional)
**If LLM available**: Generate insights across periods
**If no LLM**: Display data visualizations, user interprets

---

## Database Schema Requirements

### Current JSON-Based Storage
```python
experiment.configuration = {
    'semantic_events': [
        {
            'type': 'pejoration',  # String
            'from_period': 'period_1',
            'to_period': 'period_3',
            'description': 'User text'
        }
    ]
}
```

**Problem**: No ontology URIs, no semantic queries

### Proposed Table-Based Storage (User-Driven)
```sql
CREATE TABLE semantic_events (
    id SERIAL PRIMARY KEY,
    experiment_id INTEGER REFERENCES experiments(id),

    -- Ontology integration (from OntServe)
    event_type_uri VARCHAR(255) NOT NULL,  -- 'http://ontorealm.net/sco#Pejoration'
    event_type_label VARCHAR(255),         -- 'Pejoration' (cached from ontology)

    -- User-defined properties
    from_period_id INTEGER REFERENCES periods(id),
    to_period_id INTEGER REFERENCES periods(id),
    description TEXT,  -- User-written description

    -- Provenance
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Optional LLM analysis (NULL if standalone mode)
    llm_confidence FLOAT,  -- Only if LLM suggested
    llm_evidence TEXT      -- Only if LLM analyzed
);
```

**Key Points**:
- `event_type_uri`: From OntServe, but USER selects
- `description`: User-written, not LLM-generated
- `llm_*` fields: Optional, NULL in standalone mode

### Period Table (Already User-Driven)
```sql
CREATE TABLE periods (
    id SERIAL PRIMARY KEY,
    experiment_id INTEGER REFERENCES experiments(id),

    -- User-defined or OED-imported
    label VARCHAR(255) NOT NULL,
    start_year INTEGER,
    end_year INTEGER,
    source VARCHAR(50),  -- 'manual' | 'oed' | 'auto'

    -- User can override OED
    notes TEXT
);
```

---

## MCP Integration Strategy

### CORRECT: Metadata Provider (Not Decision Maker)

**OntServe Role**: Provide ontology metadata to users
**NOT**: Make decisions about which events occurred

```python
# GOOD: OntServe provides choices
class OntServeClient:
    def get_semantic_change_event_types(self):
        """Fetch available event types for user selection"""
        sparql = """
        PREFIX sco: <http://ontorealm.net/sco#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

        SELECT ?uri ?label ?definition ?example
        WHERE {
            ?uri a owl:Class ;
                 rdfs:subClassOf sco:SemanticChangeEvent ;
                 rdfs:label ?label ;
                 skos:definition ?definition .
            OPTIONAL { ?uri skos:example ?example }
        }
        """
        results = self.query(sparql)
        return [EventTypeMetadata(**r) for r in results]

    def get_event_type_metadata(self, uri):
        """Get full metadata for a specific event type"""
        # Returns: label, definition, examples, citations
        # USER decides if it applies to their data
```

### AVOID: Auto-Classification

```python
# BAD: System decides what happened
class LLMService:
    def auto_classify_semantic_change(self, text):
        """AVOID: Removes user agency"""
        # LLM picks event type without user input
        # Should be: suggest for user review, not auto-apply
```

---

## UI Design Principles

### 1. Ontology as Reference, Not Prescription

**Semantic Event Creation Form**:
```html
<form id="create-semantic-event">
  <label>Event Type</label>
  <select name="event_type_uri" onchange="showDefinition(this.value)">
    <option value="">-- Select semantic change type --</option>
    <option value="sco:Pejoration"
            data-definition="Negative shift in connotation (Jatowt 2014)">
      Pejoration
    </option>
    <option value="sco:Amelioration"
            data-definition="Positive shift in connotation (Jatowt 2014)">
      Amelioration
    </option>
  </select>

  <!-- Show definition when user selects -->
  <div id="definition-help" class="form-text"></div>

  <label>From Period</label>
  <select name="from_period">
    <!-- User's defined periods -->
  </select>

  <label>To Period</label>
  <select name="to_period">
    <!-- User's defined periods -->
  </select>

  <label>Your Description</label>
  <textarea name="description"
            placeholder="Describe the semantic change you observed...">
  </textarea>

  <!-- Optional: LLM enhancement -->
  {% if llm_available %}
  <button type="button" onclick="getLLMSuggestions()">
    Get LLM Suggestions (Optional)
  </button>
  {% endif %}

  <button type="submit">Create Event</button>
</form>
```

**Key Points**:
- User selects event type from ontology-backed dropdown
- Ontology provides definition as reference
- User writes description in their own words
- LLM suggestions clearly marked as optional

### 2. Progressive Enhancement

**Standalone Mode UI**:
```html
<div class="alert alert-info">
  <strong>Manual Mode:</strong> Define semantic events based on your analysis.
  Ontology definitions provide guidance.
</div>
```

**LLM-Enhanced Mode UI**:
```html
<div class="alert alert-success">
  <strong>LLM-Enhanced Mode:</strong> Get suggestions from AI analysis.
  You can accept, modify, or ignore suggestions.
</div>
```

---

## Feature Implementation Checklist

### Phase 1: Database Migration (User-Driven Foundation)

**Goal**: Store semantic events with ontology URIs, no LLM required

- [ ] Create `semantic_events` table
- [ ] Migrate JSON data to table
- [ ] Add `event_type_uri` field
- [ ] Update UI to use dropdown (populated from OntServe)
- [ ] User creates events manually
- [ ] Timeline displays events with ontology metadata

**LLM Dependency**: NONE

### Phase 2: OntServe Integration (Metadata Provider)

**Goal**: Fetch event type metadata from ontology

- [ ] Implement `OntServeClient.get_semantic_change_event_types()`
- [ ] Implement `OntServeClient.get_event_type_metadata(uri)`
- [ ] Cache ontology metadata in database
- [ ] Display definitions/examples in UI
- [ ] Link to academic citations

**LLM Dependency**: NONE

### Phase 3: SPARQL Query Interface (Advanced Users)

**Goal**: Let users query their own data semantically

- [ ] Build query builder UI
- [ ] Example queries: "All pejoration events across experiments"
- [ ] Export results as RDF
- [ ] Cross-experiment pattern discovery

**LLM Dependency**: NONE

### Phase 4: Optional LLM Enhancements

**Goal**: Add AI suggestions without removing user control

- [ ] LLM suggests potential semantic events (user reviews)
- [ ] LLM analyzes cross-period patterns (user interprets)
- [ ] LLM provides evidence snippets (user decides)
- [ ] All LLM outputs clearly marked as suggestions

**LLM Dependency**: OPTIONAL (feature flag)

---

## Configuration Management

### Environment Variables

```bash
# REQUIRED: Database connection
DATABASE_URL=postgresql://postgres:PASS@localhost/ontextract_db

# REQUIRED: OntServe for ontology metadata
ONTSERVE_MCP_URL=http://localhost:8082

# OPTIONAL: LLM enhancements
ANTHROPIC_API_KEY=sk-ant-xxx  # If not set, standalone mode

# OPTIONAL: Enable LLM features even if key present
ENABLE_LLM_SUGGESTIONS=false  # Default: true if key present
```

### Feature Flags

```python
# config.py
class Config:
    # Core features (always available)
    ENABLE_TEMPORAL_TIMELINE = True
    ENABLE_ONTOLOGY_INTEGRATION = True
    ENABLE_MANUAL_ANNOTATION = True

    # LLM features (optional)
    @property
    def ENABLE_LLM_ORCHESTRATION(self):
        return bool(self.ANTHROPIC_API_KEY) and \
               self.get('ENABLE_LLM_SUGGESTIONS', True)

    @property
    def ENABLE_LLM_EVENT_SUGGESTIONS(self):
        return self.ENABLE_LLM_ORCHESTRATION
```

---

## Documentation Updates Required

### README.md

Update "Operational Modes" section:

```markdown
## Operational Modes

### Standalone Mode (No API Key Required) - PRIMARY MODE
All document processing and temporal analysis capabilities:
- Manual tool selection through interface
- Same NLP libraries (spaCy, NLTK, sentence-transformers)
- **Temporal timeline with ontology-backed event types**
- **Manual semantic event annotation**
- **Period-aware document linking**
- **OED integration for historical definitions**
- Full PROV-O provenance tracking
- **SPARQL queries over semantic events**

### API-Enhanced Mode (Requires Anthropic API Key) - OPTIONAL
Additional LLM orchestration features:
- Automated tool selection and strategy recommendation
- Cross-document synthesis with pattern identification
- **LLM suggestions for semantic events (user reviews)**
- Enhanced context anchor extraction

**Key Point**: All core features work without an API key. LLM features
provide suggestions and insights, but users remain in control.
```

### TEMPORAL_TIMELINE_PROGRESS.md

Add section:

```markdown
## User Agency Principles

**Core Design**: Temporal timeline is user-driven with ontology support

**User Controls**:
- Period definition (manual or OED-imported)
- Semantic event type selection (from ontology)
- Event annotation (user-written descriptions)
- Document-period linking (manual assignment)
- Timeline visualization (user exploration)

**Ontology Role**: Provides metadata, definitions, citations
- Event type taxonomy from literature
- Academic definitions (Jatowt 2014, Kutuzov 2018, etc.)
- Examples and detection methods
- NOT decision-maker about what occurred

**LLM Role (Optional)**: Suggests patterns for user review
- Potential semantic events (user accepts/rejects)
- Evidence snippets (user validates)
- Cross-document patterns (user interprets)
- NOT auto-annotator
```

---

## Testing Strategy

### Standalone Mode Tests (High Priority)

```python
class TestStandaloneModeFeatures:
    """Test all features work without ANTHROPIC_API_KEY"""

    def setup_method(self):
        # Ensure no API key
        os.environ.pop('ANTHROPIC_API_KEY', None)
        app.config['ANTHROPIC_API_KEY'] = None

    def test_create_semantic_event_without_llm(self):
        """User can create semantic events manually"""
        response = client.post('/experiments/1/semantic_events', json={
            'event_type_uri': 'http://ontorealm.net/sco#Pejoration',
            'from_period_id': 1,
            'to_period_id': 3,
            'description': 'User observed negative shift'
        })
        assert response.status_code == 201
        assert 'llm_confidence' not in response.json

    def test_fetch_event_types_from_ontology(self):
        """Event types fetched from OntServe, not hardcoded"""
        response = client.get('/experiments/1/semantic_events/types')
        assert response.status_code == 200
        assert len(response.json) > 0
        assert 'uri' in response.json[0]
        assert 'definition' in response.json[0]

    def test_timeline_renders_without_llm(self):
        """Timeline displays without LLM suggestions"""
        response = client.get('/experiments/1/timeline')
        assert response.status_code == 200
        assert b'Standalone Mode' in response.data or \
               b'Create Semantic Event' in response.data
```

### LLM Enhancement Tests (Optional)

```python
class TestLLMEnhancementFeatures:
    """Test LLM features enhance but don't replace user control"""

    def setup_method(self):
        os.environ['ANTHROPIC_API_KEY'] = 'test-key'

    def test_llm_suggests_events_for_review(self):
        """LLM suggestions require user review"""
        response = client.post('/experiments/1/llm_suggest_events')
        assert response.status_code == 200
        suggestions = response.json['suggestions']

        # Suggestions not auto-created
        events = SemanticEvent.query.filter_by(experiment_id=1).all()
        assert len(events) == 0

        # User must explicitly accept
        response = client.post('/experiments/1/semantic_events', json={
            **suggestions[0],  # Take LLM suggestion
            'user_approved': True  # Explicit approval
        })
        assert response.status_code == 201
```

---

## Migration Path

### Current State
- Semantic events stored in JSON
- Event types hardcoded strings
- No ontology integration
- Works without API key

### Target State
- Semantic events in database table
- Event types from OntServe ontology
- Full ontology integration
- Still works without API key
- Optional LLM enhancements

### Migration Steps

**Step 1: Database Schema (Week 1)**
- Create tables
- Migrate JSON to tables
- No feature changes (maintain current UI)

**Step 2: OntServe Integration (Week 2)**
- Replace hardcoded dropdown with OntServe query
- Show ontology definitions
- User experience unchanged (still manual)

**Step 3: Enhanced UI (Week 3)**
- Display academic citations
- Show event type examples
- Add SPARQL query interface

**Step 4: Optional LLM (Week 4)**
- Add "Get Suggestions" button
- LLM analysis displayed as suggestions
- User controls remain primary

---

## Success Criteria

### Must Preserve
- All temporal timeline features work without API key
- Users create all semantic events manually
- Ontology provides guidance, not automation
- PROV-O tracks user actions, not just LLM outputs

### Can Enhance
- LLM suggests patterns for user review
- AI provides evidence snippets for user validation
- Automated analysis as opt-in feature
- Cross-document insights generated but not auto-applied

### Red Flags to Avoid
- "Auto-detect semantic changes" (removes user expertise)
- "AI-generated timeline" (removes user control)
- "Suggested events automatically created" (bypasses review)
- Any feature that requires API key for core functionality

---

## Conclusion

**Architectural Commitment**: OntExtract is a user-empowered digital humanities tool with optional AI enhancements, not an AI-dependent system.

**Implementation Principle**: Ontology provides scholarly metadata. LLM provides computational suggestions. User provides expertise and final decisions.

**Next Steps**: Review BFO + PROV-O implementation plan against this architecture. Ensure all database schema changes support standalone mode first, LLM enhancements second.
