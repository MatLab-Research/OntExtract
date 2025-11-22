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

## Next Steps

### Immediate
1. **Fix semantic event save bug**: Debug HTML response issue
   - Check Flask logs for error traceback
   - Add logging to `save_semantic_event` route
   - Verify JSON serialization of event data

### Future Enhancements
1. **Timeline Visualization**: Add graphical timeline view (vis.js or D3.js)
2. **Batch Operations**: Add/edit multiple events at once
3. **Export Timeline**: Generate PDF/PNG of timeline
4. **Event Templates**: Pre-defined event types with descriptions
5. **Period Suggestions**: ML-based period detection from document analysis
6. **Event Connections**: Link semantic events to specific term definitions

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
