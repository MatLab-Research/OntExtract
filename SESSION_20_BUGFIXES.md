# Session 20 Bugfixes

**Date**: 2025-11-22
**Context**: Browser testing revealed two issues when accessing demo experiment

---

## Bug 1: Provenance Service Error

**Error**:
```
'ProvenanceService' object has no attribute 'record_activity'
```

**Location**: `app/routes/experiments/temporal.py` (lines 465-494, 531-547)

**Root Cause**:
Code added in Session 19 had two problems:
1. Wrong import: `from app.services.provenance_service import provenance_service` (instance instead of class)
2. Non-existent method: Called `record_activity()` which doesn't exist

**Fix**:

1. **Added new method** to `app/services/provenance_service.py` (lines 1400-1497):
   - `ProvenanceService.track_semantic_event()`
   - Follows existing pattern of `track_term_creation()`, `track_document_upload()`, etc.
   - Creates proper PROV-O activities and entities
   - Links to related documents via "used" relationships
   - Handles creation, update, and deletion

2. **Updated temporal.py** (2 locations):
   ```python
   # Before (INCORRECT)
   from app.services.provenance_service import provenance_service
   provenance_service.record_activity(...)

   # After (CORRECT)
   from app.services.provenance_service import ProvenanceService
   ProvenanceService.track_semantic_event(
       event_type=event_type,
       experiment=experiment,
       user=current_user,
       event_metadata=event_obj,
       related_documents=related_documents,
       is_update=is_update  # or is_deletion=True
   )
   ```

**Result**: Semantic events now properly tracked in provenance timeline

---

## Bug 2: Timeline Sorting Error

**Error**:
```jinja
File "temporal_term_manager.html", line 675
{% set sorted_timeline = timeline_items|sort(attribute='sort_key') %}
```

**Root Cause**:
Template tried to sort semantic events by `sort_key`, but events used period IDs like "period_1" instead of numeric years. The demo experiment configuration lacked `period_metadata` mapping period IDs to years.

**Fix**:

1. **Added period_metadata** to demo experiment configuration:
   ```python
   period_metadata = {
       'period_1': {
           'year': 1850,
           'source': 'manual',
           'label': 'Pre-Standardization (1850-1900)',
           'start_year': 1850,
           'end_year': 1900
       },
       # ... for all 4 periods
   }
   ```

2. **Updated template** (`app/templates/experiments/temporal_term_manager.html`, lines 662-676):
   ```jinja
   {# Before (INCORRECT) #}
   {% set _ = timeline_items.append({
       'type': 'event',
       'year': event.from_period,  {# 'period_1' not a year! #}
       'sort_key': event.from_period,
       'event': event
   }) %}

   {# After (CORRECT) #}
   {% set from_period_meta = period_metadata.get(event.from_period|string, {}) %}
   {% set event_year = from_period_meta.get('year', from_period_meta.get('start_year', 0)) %}
   {% set _ = timeline_items.append({
       'type': 'event',
       'year': event_year,  {# Actual year: 1850, 1900, etc. #}
       'sort_key': event_year,
       'event': event,
       'from_period': event.from_period,
       'to_period': event.to_period
   }) %}
   ```

3. **Updated demo script** (`scripts/create_demo_experiment.py`, lines 461-471):
   - Now automatically creates period_metadata when building configuration
   - Future demo creations will have proper metadata

**Result**: Timeline sorts correctly by year, semantic events display in chronological order

---

## Testing

Both fixes verified:
- ✓ Semantic events can be created/updated/deleted without errors
- ✓ Timeline displays with proper chronological sorting
- ✓ Provenance tracking works (check `/provenance/timeline`)
- ✓ Demo experiment accessible at http://localhost:8765/experiments/75

---

## Files Modified

1. `app/services/provenance_service.py`
   - Added `track_semantic_event()` method (lines 1400-1497)

2. `app/routes/experiments/temporal.py`
   - Fixed `save_semantic_event()` provenance call (line 465-474)
   - Fixed `remove_semantic_event()` provenance call (line 531-540)

3. `app/templates/experiments/temporal_term_manager.html`
   - Updated semantic event timeline sorting (lines 665-666)

4. `scripts/create_demo_experiment.py`
   - Added period_metadata generation (lines 461-471)

5. Demo experiment (ID 75)
   - Manually added period_metadata to configuration

---

**Status**: Both bugs fixed, demo experiment fully functional
