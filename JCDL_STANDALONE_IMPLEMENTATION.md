# OntExtract Standalone Implementation for JCDL 2025

**Conference**: JCDL (Joint Conference on Digital Libraries)
**Dates**: December 15-19, 2025
**Paper**: "LLM-Orchestrated Document Processing: Intelligent Tool Selection for Historical Text Analysis"
**Status**: REVISED - Standalone Architecture
**Date**: 2025-11-22

---

## Strategic Decision: Standalone for JCDL, OntServe for Post-Conference

**Why Standalone?**
- ✓ Simpler demo setup (no multi-service dependencies)
- ✓ More reliable (fewer moving parts)
- ✓ Faster development (no OntServe integration complexity)
- ✓ Still demonstrates ontology-informed design
- ✓ Focus on paper topic (LLM orchestration, not semantic web)

**Post-Conference**: Full OntServe integration for journal paper and long-term infrastructure

---

## Implementation Plan: 2-Week Sprint

### Phase 1: Local Ontology Metadata (Week 1 - Days 1-3)

**Goal**: Display ontology-backed event types in UI without OntServe dependency

**Estimated Time**: 4-6 hours

#### 1.1 Create Local Ontology Service (2 hours)

```python
# app/services/local_ontology_service.py
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
        query = """
        PREFIX sco: <http://ontorealm.net/sco#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        PREFIX dcterms: <http://purl.org/dc/terms/>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>

        SELECT ?uri ?label ?definition ?example ?citation ?parent
        WHERE {
            ?uri a owl:Class ;
                 rdfs:subClassOf ?parent ;
                 rdfs:label ?label ;
                 skos:definition ?definition .

            # Only get direct subclasses of SemanticChangeEvent
            FILTER(?parent = sco:SemanticChangeEvent)

            OPTIONAL { ?uri skos:example ?example }
            OPTIONAL { ?uri dcterms:bibliographicCitation ?citation }
        }
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
```

**Test**:
```python
# Quick test
from app.services.local_ontology_service import get_ontology_service

ontology = get_ontology_service()
event_types = ontology.get_semantic_change_event_types()
print(f"Found {len(event_types)} event types")

for et in event_types[:3]:
    print(f"\n{et.label}:")
    print(f"  Definition: {et.definition[:80]}...")
    print(f"  Citation: {et.citation}")
```

#### 1.2 Update Temporal Routes (1 hour)

```python
# app/routes/experiments/temporal.py (add endpoint)

from app.services.local_ontology_service import get_ontology_service

@experiments_bp.route('/<int:experiment_id>/semantic_event_types', methods=['GET'])
@api_require_login_for_write
def get_semantic_event_types(experiment_id):
    """
    Get semantic change event types from ontology for dropdown.

    Returns event types with definitions and citations for UI display.
    """
    try:
        ontology = get_ontology_service()
        event_types = ontology.get_all_for_dropdown()

        return jsonify({
            'success': True,
            'event_types': event_types,
            'count': len(event_types),
            'source': 'semantic-change-ontology-v2.ttl'
        }), 200

    except Exception as e:
        logger.error(f"Failed to load event types: {e}", exc_info=True)

        # Fallback to hardcoded types if ontology load fails
        fallback_types = [
            {
                'value': 'pejoration',
                'label': 'Pejoration',
                'definition': 'Negative shift in word meaning or connotation',
                'citation': 'Jatowt & Duh 2014'
            },
            {
                'value': 'amelioration',
                'label': 'Amelioration',
                'definition': 'Positive shift in word meaning or connotation',
                'citation': 'Jatowt & Duh 2014'
            },
            # ... other fallbacks
        ]

        return jsonify({
            'success': True,
            'event_types': fallback_types,
            'count': len(fallback_types),
            'source': 'fallback (ontology load failed)',
            'error': str(e)
        }), 200
```

#### 1.3 Update Frontend UI (2 hours)

```javascript
// static/js/temporal_timeline.js

// Load event types from ontology on page load
async function loadEventTypes() {
    try {
        const response = await fetch(`/experiments/${experimentId}/semantic_event_types`);
        const data = await response.json();

        if (!data.success) {
            console.error('Failed to load event types:', data.error);
            return;
        }

        console.log(`Loaded ${data.count} event types from ${data.source}`);

        // Populate dropdown
        const select = document.getElementById('event-type-select');
        select.innerHTML = '<option value="">-- Select semantic change type --</option>';

        data.event_types.forEach(type => {
            const option = document.createElement('option');
            option.value = type.value;
            option.textContent = type.label;

            // Store metadata as data attributes
            option.dataset.definition = type.definition;
            option.dataset.citation = type.citation || '';
            option.dataset.example = type.example || '';
            option.dataset.uri = type.uri || '';

            select.appendChild(option);
        });

    } catch (error) {
        console.error('Error loading event types:', error);
        showError('Failed to load event types from ontology');
    }
}

// Show definition tooltip when user selects event type
function showEventTypeMetadata(selectElement) {
    const selectedOption = selectElement.options[selectElement.selectedIndex];

    if (!selectedOption || !selectedOption.value) {
        document.getElementById('event-type-metadata').innerHTML = '';
        return;
    }

    const definition = selectedOption.dataset.definition;
    const citation = selectedOption.dataset.citation;
    const example = selectedOption.dataset.example;

    let html = `
        <div class="alert alert-info mt-2">
            <strong>Definition:</strong> ${definition}
    `;

    if (citation) {
        html += `<br><small><strong>Citation:</strong> ${citation}</small>`;
    }

    if (example) {
        html += `<br><small><strong>Example:</strong> ${example}</small>`;
    }

    html += '</div>';

    document.getElementById('event-type-metadata').innerHTML = html;
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    loadEventTypes();

    document.getElementById('event-type-select').addEventListener('change', (e) => {
        showEventTypeMetadata(e.target);
    });
});
```

**Update Template**:
```html
<!-- templates/experiments/temporal_term_manager.html -->

<div class="card">
    <div class="card-header">Create Semantic Event</div>
    <div class="card-body">
        <form id="create-semantic-event-form">
            <div class="mb-3">
                <label for="event-type-select" class="form-label">
                    Event Type
                    <span class="badge bg-success">Ontology-Backed</span>
                </label>
                <select id="event-type-select" name="event_type" class="form-select" required>
                    <option value="">Loading from ontology...</option>
                </select>

                <!-- Metadata display area -->
                <div id="event-type-metadata"></div>
            </div>

            <!-- Rest of form: periods, description, etc. -->
        </form>
    </div>
</div>

<!-- Footer note for academic rigor -->
<div class="text-muted small mt-3">
    Event types derived from validated ontology (34 classes, 33 citations).
    See <a href="/ontology/info">ontology documentation</a> for details.
</div>
```

#### 1.4 Add Ontology Info Page (1 hour)

Create simple page showing ontology validation results:

```python
# app/routes/experiments/temporal.py

@experiments_bp.route('/ontology/info', methods=['GET'])
def ontology_info():
    """Display ontology validation information"""
    try:
        ontology = get_ontology_service()
        event_types = ontology.get_semantic_change_event_types()

        # Read validation results if available
        validation_file = Path('VALIDATION_GUIDE.md')
        validation_summary = None
        if validation_file.exists():
            with open(validation_file) as f:
                content = f.read()
                # Extract validation results section
                # (simple parsing or just link to file)

        return render_template(
            'experiments/ontology_info.html',
            event_types=event_types,
            ontology_path='ontologies/semantic-change-ontology-v2.ttl',
            validation_summary=validation_summary
        )

    except Exception as e:
        logger.error(f"Error displaying ontology info: {e}")
        return render_template('error.html', error=str(e)), 500
```

**Template**: Simple page showing:
- Ontology file location
- Validation status (PASSED)
- Class count, property count
- List of event types with definitions
- Link to ontology file and validation output

---

### Phase 2: Enhanced UI for JCDL Demo (Week 1 - Days 4-5)

**Goal**: Polish UI to highlight ontology-informed design

**Estimated Time**: 3-4 hours

#### 2.1 Visual Indicators

Add badges/icons showing "Ontology-Backed" features:

```html
<!-- Semantic event cards on timeline -->
<div class="timeline-event-card">
    <span class="badge bg-success">
        <i class="bi bi-diagram-3"></i> Ontology-Backed
    </span>
    <h5>Pejoration: 1850-1900</h5>
    <p class="text-muted small">
        <i class="bi bi-book"></i> Jatowt & Duh 2014
    </p>
    <p>{{ event.description }}</p>
</div>
```

#### 2.2 Ontology Metadata Panel

Add collapsible panel showing ontology info:

```html
<div class="accordion mb-3">
    <div class="accordion-item">
        <h2 class="accordion-header">
            <button class="accordion-button collapsed"
                    data-bs-toggle="collapse"
                    data-bs-target="#ontology-info">
                <i class="bi bi-diagram-3"></i> Ontology Information
            </button>
        </h2>
        <div id="ontology-info" class="accordion-collapse collapse">
            <div class="accordion-body">
                <p>
                    Event types derived from validated semantic change ontology:
                </p>
                <ul>
                    <li>34 classes (expanded from 8 in v1.0)</li>
                    <li>33 academic citations</li>
                    <li>Consistency verified with Pellet reasoner</li>
                    <li>BFO-aligned upper ontology</li>
                </ul>
                <a href="/ontology/info" class="btn btn-sm btn-outline-primary">
                    View Full Ontology Documentation
                </a>
            </div>
        </div>
    </div>
</div>
```

#### 2.3 Citation Display

When user creates event, show citation in card:

```html
<div class="semantic-event-card">
    <div class="card-header">
        <h6>{{ event.type_label }}</h6>
        <small class="text-muted">
            <i class="bi bi-book"></i> {{ event.citation }}
        </small>
    </div>
    <div class="card-body">
        {{ event.description }}
    </div>
</div>
```

---

### Phase 3: JCDL Demo Preparation (Week 2)

**Goal**: Ensure reliable demo, prepare presentation materials

**Estimated Time**: 4-6 hours

#### 3.1 Demo Data Setup

Create sample temporal experiment with:
- 5-10 documents spanning 1850-1950
- 3-4 semantic events using ontology types
- Period cards showing evolution
- Professional descriptions

```python
# scripts/create_demo_experiment.py
"""Create demo experiment for JCDL presentation"""

def create_jcdl_demo():
    """Create professional ethics temporal evolution demo"""

    # Create experiment
    experiment = Experiment(
        name="Professional Ethics Concept Evolution (1850-1950)",
        type="temporal_evolution",
        description="Analysis of how professional ethics concepts evolved in engineering literature"
    )

    # Add documents
    docs = [
        {
            'title': 'Engineering Standards Committee Report',
            'publication_date': '1905-03-15',
            'content': '...'
        },
        # ... more docs
    ]

    # Add periods
    periods = [
        {'label': 'Pre-Standardization Era', 'start': 1850, 'end': 1900},
        {'label': 'Early Codes Formation', 'start': 1900, 'end': 1925},
        {'label': 'Professionalization', 'start': 1925, 'end': 1950}
    ]

    # Add semantic events (using ontology)
    ontology = get_ontology_service()
    pejoration = ontology.get_event_type_by_label('Pejoration')

    events = [
        {
            'type': 'pejoration',
            'type_label': pejoration.label,
            'definition': pejoration.definition,
            'citation': pejoration.citation,
            'from_period': periods[0],
            'to_period': periods[1],
            'description': 'Term "professional" narrowed from general expertise to licensed practice'
        }
    ]

    # Save to database
    # ...
```

#### 3.2 Documentation for Paper

Update README for conference submission:

```markdown
## Ontology-Informed Design

OntExtract's semantic change event types are derived from a formally
validated ontology (semantic-change-ontology-v2.ttl):

- **34 event type classes** derived from literature review
- **33 academic citations** embedded in ontology
- **Pellet reasoner validation** ensures logical consistency
- **BFO alignment** for upper-level ontology integration

Event types include:
- Pejoration/Amelioration (Jatowt & Duh 2014)
- Linguistic Drift (Kutuzov et al. 2018)
- Intension/Extension Drift (Stavropoulos et al. 2019)
- Lexical Emergence/Obsolescence (Tahmasebi et al. 2021)

Users select event types from ontology-backed dropdown with
academic definitions and citations displayed.

**Validation Results**: See [VALIDATION_GUIDE.md](VALIDATION_GUIDE.md)

**Ontology File**: [ontologies/semantic-change-ontology-v2.ttl](ontologies/semantic-change-ontology-v2.ttl)
```

#### 3.3 Presentation Materials

Prepare slides showing:

1. **Ontology-Informed UI**
   - Screenshot of dropdown with definitions
   - Highlight citations in cards
   - Show "Ontology-Backed" badges

2. **Validation Evidence**
   - Pellet reasoner output showing consistency
   - Class hierarchy visualization
   - Academic citations list

3. **Demo Flow**
   - Create temporal experiment
   - Select ontology-backed event type
   - View definition and citation
   - Create semantic event
   - Timeline displays with metadata

#### 3.4 Testing Checklist

- [ ] Ontology loads on app startup
- [ ] Event type dropdown populates from ontology
- [ ] Definitions display correctly
- [ ] Citations show in event cards
- [ ] Works without internet connection (local file)
- [ ] Fallback to hardcoded types if ontology fails
- [ ] Demo experiment created and accessible
- [ ] Timeline renders correctly
- [ ] No errors in browser console
- [ ] Works on presentation laptop

---

## Database Schema (No Changes Required!)

**Current JSON Storage**: Keep using `experiment.configuration` for JCDL demo

```json
{
    "semantic_events": [
        {
            "type": "pejoration",
            "type_label": "Pejoration",
            "type_uri": "http://ontorealm.net/sco#Pejoration",
            "definition": "Negative shift in connotation...",
            "citation": "Jatowt & Duh 2014",
            "from_period": "period_1",
            "to_period": "period_2",
            "description": "User description here",
            "created_by": 1,
            "created_at": "2025-11-22T10:30:00"
        }
    ]
}
```

**Post-Conference**: Migrate to table-based storage with full URI support

---

## Dependencies

**New Dependency**: Only rdflib for parsing .ttl file

```bash
# Already in requirements.txt, but ensure it's there:
pip install rdflib

# Verify
python -c "import rdflib; print(rdflib.__version__)"
```

**No other changes needed!**

---

## Paper Narrative Strategy

### Focus on LLM Orchestration (Your Paper Topic)

**Primary Contribution**:
- LLM-mediated tool selection
- Automated strategy recommendation
- Human-in-the-loop validation
- Cross-document synthesis

**Secondary Contribution** (Ontology):
- "Event types informed by validated ontology"
- Show dropdown screenshot with definitions
- Mention in limitations: "Future work: full semantic web integration"

### Framing in Paper

**In Methods Section**:
> "To ensure scholarly rigor, semantic change event types are derived
> from a formally validated ontology (34 classes, 33 citations). The
> ontology was validated using the Pellet reasoner and aligns with the
> Basic Formal Ontology (BFO) upper ontology. Event type metadata is
> displayed in the user interface, providing researchers with academic
> definitions and citations during annotation."

**In Implementation Section**:
> "The system reads event type metadata from a local ontology file
> (semantic-change-ontology-v2.ttl) using rdflib, eliminating runtime
> dependencies while maintaining ontological rigor. This design prioritizes
> deployment simplicity for the conference demonstration while enabling
> future integration with semantic web infrastructure."

**In Future Work**:
> "Future work includes full semantic web integration via SPARQL endpoints,
> enabling cross-experiment queries and RDF export for linked open data."

---

## Post-Conference Migration Path

**After JCDL** (January 2026+), implement full OntServe integration:

1. **Week 1**: Database migration (semantic_events table)
2. **Week 2**: OntServe MCP client (replace LocalOntologyService)
3. **Week 3**: SPARQL query interface
4. **Week 4**: RDF export, cross-experiment queries

**Migration will be smooth** because:
- LocalOntologyService has same interface as future OntServeClient
- JSON already includes URIs for future use
- UI doesn't change (just data source)
- All user data preserved

---

## Success Metrics

**For JCDL Demo**:
- [ ] App starts without OntServe dependency
- [ ] Event types load from ontology file
- [ ] Definitions display correctly in UI
- [ ] Citations appear in timeline cards
- [ ] Demo runs reliably on presentation laptop
- [ ] Reviewers see "ontology-informed design"
- [ ] Paper clearly explains validation process

**Post-Conference**:
- [ ] Full OntServe integration operational
- [ ] SPARQL queries working
- [ ] RDF export functional
- [ ] Journal paper includes semantic web contribution

---

## Timeline

**Week 1** (Nov 23-29):
- Days 1-3: Implement LocalOntologyService
- Days 4-5: Update UI with ontology metadata

**Week 2** (Nov 30-Dec 6):
- Days 1-2: Create demo experiment
- Days 3-4: Prepare presentation materials
- Day 5: Testing and polish

**Conference** (Dec 15-19):
- Demonstrate ontology-informed design
- Highlight LLM orchestration (primary contribution)
- Mention validation process

**Post-Conference** (Jan 2026+):
- Full OntServe integration
- Journal paper submission
- Long-term research infrastructure

---

## Files to Create/Modify

### New Files
- [x] `app/services/local_ontology_service.py` - Ontology parsing
- [x] `scripts/create_demo_experiment.py` - Demo data
- [x] `templates/experiments/ontology_info.html` - Info page

### Modified Files
- [x] `app/routes/experiments/temporal.py` - Added event types endpoint + ontology info page + provenance tracking
- [x] `templates/experiments/temporal_term_manager.html` - Shows metadata (citations, type_label) on timeline cards
- [x] `README.md` - Updated with ontology section (done in Session 18)
- [x] `requirements.txt` - rdflib already present (v7.0.0)
- [x] `app/routes/provenance_visualization.py` - Added semantic event activity types

### Documentation Files
- [x] `USER_AGENCY_ARCHITECTURE.md` - Already created
- [x] `BFO_IMPLEMENTATION_PLAN_REVISED.md` - Superseded by this file
- [x] `STANDALONE_MODE_TEST_RESULTS.md` - Already created
- [x] `JCDL_STANDALONE_IMPLEMENTATION.md` - This file

---

## Risk Mitigation

**Risk 1**: Ontology file fails to load during demo
- **Mitigation**: Fallback to hardcoded event types
- **Test**: Verify fallback works before conference

**Risk 2**: UI doesn't display metadata correctly
- **Mitigation**: Multiple browser testing, screenshots in slides
- **Test**: Full demo run-through on presentation laptop

**Risk 3**: Reviewers question lack of semantic web integration
- **Response**: "Prioritized deployment simplicity; full integration planned for journal version"
- **Evidence**: Show validated ontology file and validation output

**Risk 4**: Performance issues loading large ontology
- **Mitigation**: Cache event types after first load (singleton pattern)
- **Test**: Measure load time (should be <100ms)

---

## Estimated Total Time

**Development**: 10-12 hours
**Testing/Polish**: 4-6 hours
**Demo Prep**: 2-3 hours

**Total**: 16-21 hours over 2 weeks

**Deliverables**:
- Working standalone system
- Demo-ready experiment
- Presentation materials
- Clear path to post-conference integration

---

**Status**: Phase 1 COMPLETE, Phase 2 COMPLETE, Phase 3 Enhanced

**Next Action**: Phase 3 Testing (JCDL_TESTING_CHECKLIST.md) - 1-2 hours

**Session 20 Complete (2025-11-22):**
- Demo experiment created (Experiment ID: 75)
- 7 documents (1867-1947), 4 periods, 4 semantic events
- Full-page timeline visualization implemented
- Provenance tracking fixed
- UI polish complete

**Session 21 Complete (2025-11-22):**
- Experiment creation workflow streamlined for JCDL demo
- Quick Add Reference feature: Dictionary lookup (MW/OED) from experiment creation page
- Focus Term selection: Required for temporal evolution experiments
- Auto-fill: Description field populates when Temporal Evolution selected
- Auto-fill: Experiment name from selected term (e.g., "agent Temporal Evolution")
- UI reorganization: Focus Term moved to top of form for better workflow
- Domain Comparison temporarily disabled (post-JCDL)

**Session 22 Complete (2025-11-22):**
- Temporal Evolution Experiment Creation Agent (repeatable workflow)
- Agent location: [.claude/agents/temporal-evolution-experiment.md](.claude/agents/temporal-evolution-experiment.md)
- 8-phase workflow: Document Analysis → Term Creation → Experiment Setup → Document Upload → Period Design → Event Creation → Timeline Visualization → Provenance Export
- Handles large PDFs (1000+ pages), multi-session processing, error recovery
- JCDL presentation checklist with demo credentials and backup plans
- Technical documentation: 10+ database tables, 15+ API endpoints, ontology integration
- Enables rapid experiment recreation for JCDL preparation and testing

**Demo Access:**
- Management: http://localhost:8765/experiments/75/manage_temporal_terms
- Timeline: http://localhost:8765/experiments/75/timeline
- Create Experiment: http://localhost:8765/experiments/new
- Credentials: demo/demo123

**Documentation:**
- [SESSION_20_SUMMARY.md](SESSION_20_SUMMARY.md) - Phase 2 complete
- [SESSION_20_TIMELINE_VIEW_FINAL.md](SESSION_20_TIMELINE_VIEW_FINAL.md) - Timeline implementation
- [DEMO_EXPERIMENT_SUMMARY.md](DEMO_EXPERIMENT_SUMMARY.md) - Demo data reference
