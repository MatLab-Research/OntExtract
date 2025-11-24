# BFO + PROV-O Implementation Plan (User-Agency Focused)

**Date**: 2025-11-22
**Status**: REVISED - Prioritizing Standalone Mode
**Based On**: USER_AGENCY_ARCHITECTURE.md principles

---

## Core Principle

**User-first development**: Implement all features for standalone mode first, add optional LLM enhancements second.

---

## Phase 1: User-Driven Database Schema (Week 1)

**Goal**: Move semantic events from JSON to database table, preserving manual workflow

**No LLM Required**: All features work without API key

### 1.1 Database Migration

Create tables for user-driven semantic event annotation:

```sql
-- Semantic events table (user creates these)
CREATE TABLE semantic_events (
    id SERIAL PRIMARY KEY,
    experiment_id INTEGER REFERENCES experiments(id) NOT NULL,

    -- Ontology integration (user selects from OntServe metadata)
    event_type_uri VARCHAR(255) NOT NULL,
    event_type_label VARCHAR(255) NOT NULL,

    -- User-defined temporal scope
    from_period_id INTEGER REFERENCES periods(id),
    to_period_id INTEGER REFERENCES periods(id),

    -- User-written content
    description TEXT NOT NULL,
    evidence_notes TEXT,

    -- User provenance
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Optional LLM fields (NULL in standalone mode)
    llm_suggested BOOLEAN DEFAULT FALSE,
    llm_confidence FLOAT,
    llm_evidence TEXT,

    CONSTRAINT valid_period_range CHECK (from_period_id != to_period_id)
);

-- Document-event linking (user assigns documents as evidence)
CREATE TABLE semantic_event_documents (
    id SERIAL PRIMARY KEY,
    semantic_event_id INTEGER REFERENCES semantic_events(id) ON DELETE CASCADE,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    relevance_note TEXT,  -- User explains why this document is relevant
    added_by INTEGER REFERENCES users(id),
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(semantic_event_id, document_id)
);

-- Periods table (already exists, verify structure)
-- User creates manually or imports from OED

-- Index for querying
CREATE INDEX idx_semantic_events_experiment ON semantic_events(experiment_id);
CREATE INDEX idx_semantic_events_type ON semantic_events(event_type_uri);
CREATE INDEX idx_semantic_events_created_by ON semantic_events(created_by);
```

**Implementation**:
```bash
# Create migration file
cd /home/chris/onto/OntExtract
vim app/migrations/015_create_semantic_events_tables.sql

# Apply migration
PGPASSWORD=PASS psql -h localhost -U postgres ontextract_db -f app/migrations/015_create_semantic_events_tables.sql
```

### 1.2 Data Migration Script

Migrate existing JSON events to table:

```python
# scripts/migrate_semantic_events_to_table.py
"""
Migrate semantic events from experiment.configuration JSON to database table.

Preserves all user-created events, maps event types to ontology URIs.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app, db
from app.models import Experiment, Period
from sqlalchemy import text

# Event type mapping (string -> URI)
EVENT_TYPE_MAPPING = {
    'pejoration': 'http://ontorealm.net/sco#Pejoration',
    'amelioration': 'http://ontorealm.net/sco#Amelioration',
    'inflection_point': 'http://ontorealm.net/sco#InflectionPoint',
    'stable_polysemy': 'http://ontorealm.net/sco#StablePolysemy',
    'broadening': 'http://ontorealm.net/sco#SemanticBroadening',
    'narrowing': 'http://ontorealm.net/sco#SemanticNarrowing'
}

LABEL_MAPPING = {
    'pejoration': 'Pejoration',
    'amelioration': 'Amelioration',
    'inflection_point': 'Inflection Point',
    'stable_polysemy': 'Stable Polysemy',
    'broadening': 'Semantic Broadening',
    'narrowing': 'Semantic Narrowing'
}

def migrate():
    app = create_app()
    with app.app_context():
        experiments = Experiment.query.filter_by(type='temporal_evolution').all()

        for exp in experiments:
            config = exp.configuration or {}
            events = config.get('semantic_events', [])

            print(f"\nExperiment {exp.id}: {exp.name}")
            print(f"  Found {len(events)} events to migrate")

            for event_data in events:
                # Get period IDs
                from_period = Period.query.filter_by(
                    experiment_id=exp.id,
                    label=event_data.get('from_period')
                ).first()

                to_period = Period.query.filter_by(
                    experiment_id=exp.id,
                    label=event_data.get('to_period')
                ).first()

                if not from_period or not to_period:
                    print(f"  WARNING: Could not find periods for event")
                    continue

                # Map event type
                event_type = event_data.get('type', 'pejoration')
                event_type_uri = EVENT_TYPE_MAPPING.get(event_type, EVENT_TYPE_MAPPING['pejoration'])
                event_type_label = LABEL_MAPPING.get(event_type, 'Pejoration')

                # Insert into table
                db.session.execute(text("""
                    INSERT INTO semantic_events
                    (experiment_id, event_type_uri, event_type_label,
                     from_period_id, to_period_id, description,
                     created_by, llm_suggested)
                    VALUES
                    (:exp_id, :uri, :label, :from_id, :to_id, :desc, :user_id, false)
                """), {
                    'exp_id': exp.id,
                    'uri': event_type_uri,
                    'label': event_type_label,
                    'from_id': from_period.id,
                    'to_id': to_period.id,
                    'desc': event_data.get('description', ''),
                    'user_id': exp.user_id
                })

                print(f"  ✓ Migrated: {event_type_label} ({from_period.label} → {to_period.label})")

            db.session.commit()

        print(f"\n✓ Migration complete")

if __name__ == '__main__':
    migrate()
```

**Run Migration**:
```bash
python scripts/migrate_semantic_events_to_table.py
```

### 1.3 Update Models

```python
# app/models/semantic_event.py
"""Semantic event model for temporal evolution experiments"""
from app import db
from datetime import datetime

class SemanticEvent(db.Model):
    __tablename__ = 'semantic_events'

    id = db.Column(db.Integer, primary_key=True)
    experiment_id = db.Column(db.Integer, db.ForeignKey('experiments.id'), nullable=False)

    # Ontology integration
    event_type_uri = db.Column(db.String(255), nullable=False)
    event_type_label = db.Column(db.String(255), nullable=False)

    # Temporal scope
    from_period_id = db.Column(db.Integer, db.ForeignKey('periods.id'))
    to_period_id = db.Column(db.Integer, db.ForeignKey('periods.id'))

    # User content
    description = db.Column(db.Text, nullable=False)
    evidence_notes = db.Column(db.Text)

    # Provenance
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Optional LLM fields
    llm_suggested = db.Column(db.Boolean, default=False)
    llm_confidence = db.Column(db.Float)
    llm_evidence = db.Column(db.Text)

    # Relationships
    experiment = db.relationship('Experiment', backref='semantic_events')
    from_period = db.relationship('Period', foreign_keys=[from_period_id], backref='events_from')
    to_period = db.relationship('Period', foreign_keys=[to_period_id], backref='events_to')
    created_by_user = db.relationship('User', backref='created_semantic_events')
    document_links = db.relationship('SemanticEventDocument', back_populates='semantic_event',
                                     cascade='all, delete-orphan')

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'event_type_uri': self.event_type_uri,
            'event_type_label': self.event_type_label,
            'from_period': self.from_period.to_dict() if self.from_period else None,
            'to_period': self.to_period.to_dict() if self.to_period else None,
            'description': self.description,
            'evidence_notes': self.evidence_notes,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'llm_suggested': self.llm_suggested,
            'llm_confidence': self.llm_confidence,
            'documents': [link.to_dict() for link in self.document_links]
        }


class SemanticEventDocument(db.Model):
    __tablename__ = 'semantic_event_documents'

    id = db.Column(db.Integer, primary_key=True)
    semantic_event_id = db.Column(db.Integer, db.ForeignKey('semantic_events.id'), nullable=False)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=False)
    relevance_note = db.Column(db.Text)
    added_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    semantic_event = db.relationship('SemanticEvent', back_populates='document_links')
    document = db.relationship('Document')
    added_by_user = db.relationship('User')

    def to_dict(self):
        return {
            'id': self.id,
            'document_id': self.document_id,
            'document_title': self.document.title if self.document else None,
            'relevance_note': self.relevance_note,
            'added_by': self.added_by,
            'added_at': self.added_at.isoformat()
        }
```

**Test**: Verify migration preserved all events

---

## Phase 2: OntServe Integration (Week 2)

**Goal**: Fetch event type metadata from ontology, display to users

**No LLM Required**: OntServe provides metadata, user makes decisions

### 2.1 OntServe Client

```python
# app/services/ontserve_client.py
"""Client for querying OntServe MCP server for ontology metadata"""
import requests
from typing import List, Optional, Dict
from dataclasses import dataclass

@dataclass
class EventTypeMetadata:
    """Metadata for a semantic change event type from ontology"""
    uri: str
    label: str
    definition: str
    example: Optional[str] = None
    citation: Optional[str] = None
    detection_methods: List[str] = None

class OntServeClient:
    """Query OntServe for semantic change ontology metadata"""

    def __init__(self, base_url='http://localhost:8082'):
        self.base_url = base_url
        self.ontology_id = 'semantic-change-v2'

    def get_semantic_change_event_types(self) -> List[EventTypeMetadata]:
        """
        Fetch all semantic change event types for user selection.

        Returns list of event types with metadata for UI display.
        """
        # SPARQL query for event types
        sparql = """
        PREFIX sco: <http://ontorealm.net/sco#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        PREFIX dcterms: <http://purl.org/dc/terms/>

        SELECT ?uri ?label ?definition ?example ?citation
        WHERE {
            ?uri a owl:Class ;
                 rdfs:subClassOf sco:SemanticChangeEvent ;
                 rdfs:label ?label ;
                 skos:definition ?definition .
            OPTIONAL { ?uri skos:example ?example }
            OPTIONAL { ?uri dcterms:bibliographicCitation ?citation }
        }
        ORDER BY ?label
        """

        response = requests.post(
            f'{self.base_url}/query',
            json={
                'ontology_id': self.ontology_id,
                'query': sparql,
                'format': 'json'
            }
        )

        if response.status_code != 200:
            raise Exception(f"OntServe query failed: {response.text}")

        results = response.json()['results']['bindings']

        return [
            EventTypeMetadata(
                uri=r['uri']['value'],
                label=r['label']['value'],
                definition=r['definition']['value'],
                example=r.get('example', {}).get('value'),
                citation=r.get('citation', {}).get('value')
            )
            for r in results
        ]

    def get_event_type_metadata(self, uri: str) -> EventTypeMetadata:
        """
        Get full metadata for a specific event type.

        User selects URI from dropdown, this fetches details.
        """
        sparql = f"""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        PREFIX dcterms: <http://purl.org/dc/terms/>

        SELECT ?label ?definition ?example ?citation
        WHERE {{
            <{uri}> rdfs:label ?label ;
                   skos:definition ?definition .
            OPTIONAL {{ <{uri}> skos:example ?example }}
            OPTIONAL {{ <{uri}> dcterms:bibliographicCitation ?citation }}
        }}
        """

        response = requests.post(
            f'{self.base_url}/query',
            json={
                'ontology_id': self.ontology_id,
                'query': sparql,
                'format': 'json'
            }
        )

        if response.status_code != 200:
            raise Exception(f"OntServe query failed: {response.text}")

        results = response.json()['results']['bindings']
        if not results:
            raise ValueError(f"Event type not found: {uri}")

        r = results[0]
        return EventTypeMetadata(
            uri=uri,
            label=r['label']['value'],
            definition=r['definition']['value'],
            example=r.get('example', {}).get('value'),
            citation=r.get('citation', {}).get('value')
        )
```

### 2.2 API Routes (User-Driven)

```python
# app/routes/experiments/semantic_events.py
"""User-driven semantic event management with ontology support"""
from flask import jsonify, request
from flask_login import current_user, login_required
from app.services.ontserve_client import OntServeClient
from app.models import SemanticEvent, SemanticEventDocument, Experiment, Period
from app import db

from . import experiments_bp

ontserve = OntServeClient()


@experiments_bp.route('/<int:experiment_id>/semantic_events/types', methods=['GET'])
@login_required
def get_event_types(experiment_id):
    """
    Fetch semantic change event types from ontology for user selection.

    Returns: List of event types with metadata for dropdown display
    """
    try:
        event_types = ontserve.get_semantic_change_event_types()

        return jsonify([
            {
                'uri': et.uri,
                'label': et.label,
                'definition': et.definition,
                'example': et.example,
                'citation': et.citation
            }
            for et in event_types
        ]), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@experiments_bp.route('/<int:experiment_id>/semantic_events', methods=['POST'])
@login_required
def create_semantic_event(experiment_id):
    """
    User creates semantic event by selecting type and defining scope.

    Request Body:
    {
        "event_type_uri": "http://ontorealm.net/sco#Pejoration",
        "from_period_id": 1,
        "to_period_id": 3,
        "description": "User observed negative shift in usage...",
        "evidence_notes": "Optional notes about evidence",
        "document_ids": [1, 2, 3]  # Optional document links
    }
    """
    data = request.get_json()

    # Verify experiment exists and user has access
    experiment = Experiment.query.get_or_404(experiment_id)
    if experiment.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    # Get event type metadata from ontology
    try:
        metadata = ontserve.get_event_type_metadata(data['event_type_uri'])
    except Exception as e:
        return jsonify({'error': f'Invalid event type: {e}'}), 400

    # Verify periods exist
    from_period = Period.query.get(data['from_period_id'])
    to_period = Period.query.get(data['to_period_id'])

    if not from_period or not to_period:
        return jsonify({'error': 'Invalid period IDs'}), 400

    if from_period.experiment_id != experiment_id or to_period.experiment_id != experiment_id:
        return jsonify({'error': 'Periods must belong to this experiment'}), 400

    # Create event (user-driven, not LLM)
    event = SemanticEvent(
        experiment_id=experiment_id,
        event_type_uri=data['event_type_uri'],
        event_type_label=metadata.label,
        from_period_id=data['from_period_id'],
        to_period_id=data['to_period_id'],
        description=data['description'],
        evidence_notes=data.get('evidence_notes'),
        created_by=current_user.id,
        llm_suggested=False  # User created, not LLM
    )
    db.session.add(event)
    db.session.flush()

    # Link documents if provided
    for doc_id in data.get('document_ids', []):
        link = SemanticEventDocument(
            semantic_event_id=event.id,
            document_id=doc_id,
            added_by=current_user.id
        )
        db.session.add(link)

    db.session.commit()

    return jsonify({
        'success': True,
        'event': event.to_dict()
    }), 201


@experiments_bp.route('/<int:experiment_id>/semantic_events', methods=['GET'])
@login_required
def list_semantic_events(experiment_id):
    """Get all semantic events for timeline display"""
    events = SemanticEvent.query.filter_by(experiment_id=experiment_id).all()

    return jsonify([e.to_dict() for e in events]), 200


@experiments_bp.route('/<int:experiment_id>/semantic_events/<int:event_id>', methods=['PUT'])
@login_required
def update_semantic_event(experiment_id, event_id):
    """User updates semantic event"""
    event = SemanticEvent.query.get_or_404(event_id)

    if event.experiment.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json()

    # Update fields
    if 'description' in data:
        event.description = data['description']
    if 'evidence_notes' in data:
        event.evidence_notes = data['evidence_notes']
    if 'event_type_uri' in data:
        metadata = ontserve.get_event_type_metadata(data['event_type_uri'])
        event.event_type_uri = data['event_type_uri']
        event.event_type_label = metadata.label

    db.session.commit()

    return jsonify({
        'success': True,
        'event': event.to_dict()
    }), 200


@experiments_bp.route('/<int:experiment_id>/semantic_events/<int:event_id>', methods=['DELETE'])
@login_required
def delete_semantic_event(experiment_id, event_id):
    """User deletes semantic event"""
    event = SemanticEvent.query.get_or_404(event_id)

    if event.experiment.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    db.session.delete(event)
    db.session.commit()

    return jsonify({'success': True}), 200
```

### 2.3 Frontend UI (User-Driven)

Update timeline template to use API:

```javascript
// static/js/temporal_timeline.js (updated)

// Fetch event types from ontology for dropdown
async function loadEventTypes() {
    const response = await fetch(`/experiments/${experimentId}/semantic_events/types`);
    const eventTypes = await response.json();

    const select = document.getElementById('event-type-select');
    select.innerHTML = '<option value="">-- Select semantic change type --</option>';

    eventTypes.forEach(type => {
        const option = document.createElement('option');
        option.value = type.uri;
        option.textContent = type.label;
        option.dataset.definition = type.definition;
        option.dataset.example = type.example || '';
        option.dataset.citation = type.citation || '';
        select.appendChild(option);
    });
}

// Show event type definition when user selects
function showEventTypeHelp(uri) {
    const option = document.querySelector(`option[value="${uri}"]`);
    if (!option) return;

    const helpDiv = document.getElementById('event-type-help');
    helpDiv.innerHTML = `
        <div class="alert alert-info">
            <strong>Definition:</strong> ${option.dataset.definition}
            ${option.dataset.example ? `<br><strong>Example:</strong> ${option.dataset.example}` : ''}
            ${option.dataset.citation ? `<br><small><strong>Citation:</strong> ${option.dataset.citation}</small>` : ''}
        </div>
    `;
}

// User creates semantic event
async function createSemanticEvent(eventData) {
    const response = await fetch(`/experiments/${experimentId}/semantic_events`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(eventData)
    });

    if (response.ok) {
        const result = await response.json();
        showSuccess('Semantic event created successfully');
        refreshTimeline();  // Reload timeline display
    } else {
        const error = await response.json();
        showError(`Failed to create event: ${error.error}`);
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    loadEventTypes();

    document.getElementById('event-type-select').addEventListener('change', (e) => {
        showEventTypeHelp(e.target.value);
    });

    document.getElementById('create-event-form').addEventListener('submit', (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        createSemanticEvent({
            event_type_uri: formData.get('event_type_uri'),
            from_period_id: parseInt(formData.get('from_period_id')),
            to_period_id: parseInt(formData.get('to_period_id')),
            description: formData.get('description'),
            evidence_notes: formData.get('evidence_notes'),
            document_ids: Array.from(formData.getAll('document_ids')).map(Number)
        });
    });
});
```

**Test**: Create semantic event without API key, verify ontology metadata displayed

---

## Phase 3: Optional LLM Enhancements (Week 3)

**Goal**: Add LLM suggestions WITHOUT removing user control

**LLM Required**: Only for suggestion features

### 3.1 LLM Suggestion Service

```python
# app/services/llm_semantic_event_suggester.py
"""Optional LLM service for suggesting semantic events (user reviews)"""
from typing import List, Dict, Optional
from app.services.ontserve_client import OntServeClient
from app.models import Experiment, Document, Period
import anthropic
import os

class LLMSemanticEventSuggester:
    """Suggests potential semantic events for user review"""

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        self.ontserve = OntServeClient()
        self.enabled = bool(os.getenv('ANTHROPIC_API_KEY'))

    def suggest_events(self, experiment_id: int) -> List[Dict]:
        """
        Analyze documents and suggest potential semantic events.

        Returns: List of suggestions for USER review
        NOT auto-created - user must approve each
        """
        if not self.enabled:
            return []

        experiment = Experiment.query.get(experiment_id)
        documents = Document.query.filter_by(experiment_id=experiment_id).all()
        periods = Period.query.filter_by(experiment_id=experiment_id).all()

        # Get event types from ontology
        event_types = self.ontserve.get_semantic_change_event_types()

        # Build prompt with event type definitions
        event_type_descriptions = "\n".join([
            f"- {et.label} ({et.uri}): {et.definition}"
            for et in event_types
        ])

        prompt = f"""Analyze these historical documents and suggest potential semantic changes.

Experiment Goal: {experiment.description}

Available Semantic Change Types:
{event_type_descriptions}

Documents and Periods:
{self._format_documents_and_periods(documents, periods)}

Suggest potential semantic events based on the evidence in these documents.
For each suggestion, provide:
1. Event type URI (from the list above)
2. From period and to period
3. Evidence from documents supporting this claim
4. Confidence level (0.0-1.0)

Return as JSON array of suggestions. These are SUGGESTIONS - the user will review and decide.
"""

        response = self.client.messages.create(
            model='claude-sonnet-4-20250514',
            max_tokens=4000,
            messages=[{'role': 'user', 'content': prompt}]
        )

        suggestions = self._parse_llm_response(response.content[0].text)

        # Mark all as LLM suggestions (not user-created)
        for s in suggestions:
            s['llm_suggested'] = True
            s['requires_user_review'] = True

        return suggestions

    def _format_documents_and_periods(self, documents, periods):
        """Format documents and periods for LLM prompt"""
        # Implementation: format document excerpts, period info
        pass

    def _parse_llm_response(self, text):
        """Parse LLM JSON response into suggestions"""
        import json
        # Extract JSON from response, handle errors
        pass
```

### 3.2 LLM Suggestion Routes (Optional)

```python
# app/routes/experiments/semantic_events.py (additional routes)

@experiments_bp.route('/<int:experiment_id>/semantic_events/suggest', methods=['POST'])
@login_required
def suggest_semantic_events(experiment_id):
    """
    Get LLM suggestions for semantic events.

    Returns suggestions for USER review - does NOT auto-create events.
    """
    if not app.config.get('ANTHROPIC_API_KEY'):
        return jsonify({
            'error': 'LLM suggestions require API key',
            'mode': 'standalone'
        }), 400

    try:
        suggester = LLMSemanticEventSuggester()
        suggestions = suggester.suggest_events(experiment_id)

        return jsonify({
            'suggestions': suggestions,
            'note': 'Review and approve suggestions to create events'
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@experiments_bp.route('/<int:experiment_id>/semantic_events/approve_suggestion', methods=['POST'])
@login_required
def approve_llm_suggestion(experiment_id):
    """
    User approves LLM suggestion and creates event.

    Request body: LLM suggestion data + user modifications
    """
    data = request.get_json()

    # User can modify LLM suggestion before approving
    event = SemanticEvent(
        experiment_id=experiment_id,
        event_type_uri=data['event_type_uri'],
        event_type_label=data['event_type_label'],
        from_period_id=data['from_period_id'],
        to_period_id=data['to_period_id'],
        description=data['description'],  # User can edit
        evidence_notes=data.get('evidence_notes'),
        created_by=current_user.id,
        llm_suggested=True,  # Mark as LLM-suggested
        llm_confidence=data.get('llm_confidence'),
        llm_evidence=data.get('llm_evidence')
    )
    db.session.add(event)
    db.session.commit()

    return jsonify({
        'success': True,
        'event': event.to_dict()
    }), 201
```

### 3.3 UI for LLM Suggestions (Optional)

```html
<!-- templates/experiments/timeline.html (updated) -->

<!-- Manual event creation (always available) -->
<div class="card mb-3">
    <div class="card-header">Create Semantic Event</div>
    <div class="card-body">
        <form id="create-event-form">
            <!-- Event type dropdown, period selectors, description textarea -->
            <button type="submit" class="btn btn-primary">Create Event</button>
        </form>
    </div>
</div>

<!-- LLM suggestions (only if API key available) -->
{% if llm_enabled %}
<div class="card mb-3">
    <div class="card-header">
        <i class="bi bi-robot"></i> LLM Suggestions (Optional)
    </div>
    <div class="card-body">
        <p class="text-muted">
            Get AI suggestions for potential semantic events based on document analysis.
            You can review, modify, or ignore all suggestions.
        </p>
        <button id="get-llm-suggestions" class="btn btn-outline-primary">
            Get Suggestions
        </button>

        <!-- Suggestions displayed here for review -->
        <div id="llm-suggestions-list" class="mt-3"></div>
    </div>
</div>
{% endif %}

<!-- Timeline display (shows all events: manual + approved suggestions) -->
<div id="timeline-container"></div>
```

```javascript
// Handle LLM suggestions
document.getElementById('get-llm-suggestions').addEventListener('click', async () => {
    showLoading('Analyzing documents...');

    const response = await fetch(`/experiments/${experimentId}/semantic_events/suggest`, {
        method: 'POST'
    });

    const data = await response.json();
    hideLoading();

    if (data.suggestions) {
        displaySuggestions(data.suggestions);
    } else {
        showInfo(data.error || 'No suggestions available');
    }
});

function displaySuggestions(suggestions) {
    const container = document.getElementById('llm-suggestions-list');
    container.innerHTML = suggestions.map((s, i) => `
        <div class="card mb-2">
            <div class="card-body">
                <h6>${s.event_type_label}</h6>
                <p><strong>Periods:</strong> ${s.from_period} → ${s.to_period}</p>
                <p>${s.description}</p>
                <small class="text-muted">
                    Confidence: ${(s.llm_confidence * 100).toFixed(0)}% |
                    Evidence: ${s.llm_evidence}
                </small>
                <div class="mt-2">
                    <button class="btn btn-sm btn-success"
                            onclick="approveSuggestion(${i})">
                        Accept
                    </button>
                    <button class="btn btn-sm btn-warning"
                            onclick="editSuggestion(${i})">
                        Edit & Accept
                    </button>
                    <button class="btn btn-sm btn-outline-secondary"
                            onclick="ignoreSuggestion(${i})">
                        Ignore
                    </button>
                </div>
            </div>
        </div>
    `).join('');
}

async function approveSuggestion(index) {
    const suggestion = suggestions[index];

    const response = await fetch(`/experiments/${experimentId}/semantic_events/approve_suggestion`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(suggestion)
    });

    if (response.ok) {
        showSuccess('Event created from suggestion');
        refreshTimeline();
        removeSuggestion(index);
    }
}
```

**Test**: Verify suggestions require user approval, not auto-created

---

## Phase 4: PROV-O Provenance (Week 4)

**Goal**: Track user actions and LLM suggestions with W3C PROV-O

**Implementation**: See existing PROV-O system, extend for semantic events

```sql
-- Provenance entities
CREATE TABLE provenance_entities (
    -- Existing table, add semantic_event support
    entity_type VARCHAR(50),  -- Add: 'semantic_event'
    entity_id INTEGER
);

-- Track who created what
INSERT INTO provenance_entities (entity_type, entity_id)
SELECT 'semantic_event', id FROM semantic_events;

-- Provenance activities
INSERT INTO provenance_activities (activity_type, started_at, ended_at)
VALUES ('semantic_event_annotation', NOW(), NOW());

-- Attribution (user created event)
INSERT INTO provenance_attributions (entity_id, agent_id, agent_type)
SELECT se.id, se.created_by, 'user'
FROM semantic_events se;

-- If LLM suggested, track that too
INSERT INTO provenance_attributions (entity_id, agent_id, agent_type)
SELECT id, 'claude-sonnet-4', 'llm'
FROM semantic_events
WHERE llm_suggested = true;
```

---

## Success Metrics

### Standalone Mode Must Work (100%)
- [  ] User creates semantic events without API key
- [  ] Event types fetched from OntServe
- [  ] Timeline displays events correctly
- [  ] All CRUD operations functional
- [  ] PROV-O tracks user actions

### LLM Enhancements Optional (Nice-to-Have)
- [ ] LLM suggestions displayedfor review
- [ ] User can accept/reject/modify
- [ ] Approved suggestions marked as such
- [ ] System works perfectly if API key removed

---

## Testing Plan

```bash
# Test 1: Standalone mode (no API key)
unset ANTHROPIC_API_KEY

# Create experiment
# Create periods
# Create semantic events
# Verify timeline displays

# Test 2: LLM mode (with API key)
export ANTHROPIC_API_KEY=sk-ant-xxx

# Get LLM suggestions
# Review and approve
# Verify event marked as LLM-suggested

# Test 3: Fallback (remove API key mid-session)
# Verify existing events still work
# Verify manual creation still works
```

---

## Documentation Updates

- [  ] README.md - Emphasize standalone mode
- [  ] USER_AGENCY_ARCHITECTURE.md - Complete
- [  ] TEMPORAL_TIMELINE_PROGRESS.md - Add user-driven section
- [  ] API docs - Document all endpoints

---

## Next Session: Start Phase 1

**Immediate Tasks**:
1. Create database migration (semantic_events table)
2. Run migration script
3. Update models
4. Test with existing temporal experiments

**Estimated Time**: 2-3 hours for Phase 1
