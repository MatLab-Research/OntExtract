# JCDL Demo Testing Checklist

**Date**: 2025-11-22
**Demo Experiment ID**: 75
**Status**: Testing in progress

---

## Pre-Testing Setup

- [x] Demo experiment created (Experiment ID: 75)
- [x] Demo user credentials verified (demo/demo123)
- [x] 7 documents uploaded (1867-1947)
- [x] 4 temporal periods configured
- [x] 4 semantic events with ontology citations
- [ ] Flask app running at localhost:8765
- [ ] Browser opened to demo experiment

---

## Phase 3.4: Browser Testing Checklist

### 1. Ontology Service Tests

- [ ] **Ontology loads on app startup**
  - Start Flask app
  - Check console for "Loading ontology from..." message
  - Verify no errors loading semantic-change-ontology-v2.ttl
  - Expected: "Loaded ontology: ~X triples" message

- [ ] **Event type dropdown populates from ontology**
  - Navigate to Experiment 75
  - Click "Manage Temporal Terms"
  - Click "+ Add Semantic Event"
  - Check event type dropdown
  - Expected: 18 event types displayed
  - Verify shield icon badge appears on "Event Type" label

- [ ] **Definitions display correctly**
  - Select each event type from dropdown
  - Verify definition panel appears below dropdown
  - Check that definition text is academic and professional
  - Verify citation appears (format: "Author et al. (year)")
  - Check that example appears (if available for that event type)

### 2. Timeline Display Tests

- [ ] **Timeline renders correctly**
  - View temporal timeline page
  - Verify 4 periods display in chronological order
  - Check period colors are distinct and readable
  - Confirm period labels and descriptions display

- [ ] **Semantic event cards render**
  - Verify 4 semantic event cards appear on timeline
  - Check cards positioned between correct periods
  - Confirm card headers show event type labels (not snake_case)
  - Example: "Intensional Drift" not "intensional_drift"

- [ ] **Citations show in timeline cards**
  - Check each semantic event card
  - Verify book icon appears with citation
  - Expected format: "📚 Author et al. (year)"
  - Confirm citation matches ontology metadata
  - All 4 events should show academic citations

### 3. User Interface Tests

- [ ] **No errors in browser console**
  - Open browser DevTools (F12)
  - Navigate through all demo pages
  - Check Console tab for errors
  - Expected: No red error messages
  - Warnings acceptable if non-blocking

- [ ] **Ontology info page accessible**
  - Navigate to: http://localhost:8765/experiments/ontology/info
  - Verify page loads without errors
  - Check ontology metadata displays:
    - File path: semantic-change-ontology-v2.ttl
    - Event count: 18 classes
    - Validation status: PASSED (green badge)
    - Academic citations: 33 citations from 12 papers
  - Verify event types table displays all 18 types
  - Check research foundation sidebar shows key papers

- [ ] **Modal interactions work**
  - Click "Manage Temporal Terms" button
  - Modal should open smoothly
  - Close modal with X button
  - Re-open modal
  - Test creating new semantic event:
    - Select event type
    - Fill in description
    - Select from/to periods
    - Link related documents (optional)
    - Save event
    - Verify event appears on timeline

### 4. Data Integrity Tests

- [ ] **Event metadata persists**
  - Create new semantic event
  - Save and close modal
  - Refresh page
  - Verify event still appears with all metadata
  - Check citation is preserved
  - Confirm type_label displays correctly

- [ ] **Document links work**
  - Open semantic event card
  - Check "Related Documents" section
  - Verify document titles are clickable links
  - Click link, should open document view
  - Return to experiment timeline

### 5. Provenance Timeline Tests

- [ ] **Semantic events appear in provenance timeline**
  - Navigate to: http://localhost:8765/provenance/timeline
  - Filter by activity type: "semantic_event_creation"
  - Verify activities appear for semantic events
  - Check activity metadata includes:
    - event_type
    - type_uri
    - type_label
    - from_period / to_period
  - Verify links to related documents

- [ ] **Provenance metadata completeness**
  - Select a semantic_event_creation activity
  - Verify wasAssociatedWith shows user (demo)
  - Check generatedAtTime timestamp
  - Confirm activity_parameters include ontology URIs
  - Verify "used" entities link to document UUIDs

### 6. Offline / Standalone Tests

- [ ] **Works without internet connection**
  - Disable network connection
  - Restart Flask app
  - Navigate to experiment
  - Verify ontology still loads (from local file)
  - Create new semantic event
  - Confirm all features work offline

- [ ] **Fallback to hardcoded types if ontology fails**
  - Temporarily rename ontology file
  - Restart Flask app
  - Navigate to "Add Semantic Event"
  - Verify dropdown still populates with fallback types
  - Check console for fallback message
  - Restore ontology file name

### 7. Demo Flow Tests

- [ ] **Full demo walkthrough**
  - Login as demo user
  - Navigate to experiment
  - Show temporal timeline
  - Open "Manage Temporal Terms" modal
  - Display event type dropdown with shield icon
  - Select event type to show definition
  - View timeline cards with citations
  - Navigate to ontology info page
  - Return to experiment
  - Complete flow without errors

- [ ] **Presentation laptop compatibility**
  - Test on presentation laptop (if different from dev machine)
  - Verify database connection works
  - Check all fonts/styles render correctly
  - Confirm no display issues at presentation resolution
  - Test with projector if available

### 8. Performance Tests

- [ ] **Page load times acceptable**
  - Experiment page loads in < 3 seconds
  - Ontology info page loads in < 2 seconds
  - Modal opens instantly
  - Timeline renders smoothly

- [ ] **No memory leaks**
  - Open/close modal 10 times
  - Navigate between pages multiple times
  - Check browser memory usage (DevTools → Memory)
  - Expected: No significant memory growth

---

## Known Issues / Notes

### Issues Found
(Document any issues discovered during testing)

### Workarounds
(Document any workarounds needed for demo)

### Browser Compatibility
- Tested on: (Chrome/Firefox/Safari version)
- Status:
- Issues:

---

## Testing Results Summary

**Total Tests**: 30+
**Passed**:
**Failed**:
**Skipped**:

**Overall Status**:

**Ready for Presentation**: YES / NO

**Tester**:
**Date Completed**:

---

## Pre-Demo Checklist

Day before presentation:
- [ ] Run full testing checklist again
- [ ] Verify demo data still intact
- [ ] Check database connection
- [ ] Test on presentation laptop
- [ ] Prepare backup plan if network issues

Morning of presentation:
- [ ] Start Flask app
- [ ] Verify demo experiment loads
- [ ] Quick smoke test of all features
- [ ] Open presentation materials
- [ ] Bookmark demo URL

---

## Emergency Procedures

If ontology fails to load:
1. Check console for specific error
2. Verify semantic-change-ontology-v2.ttl exists
3. Fallback dropdown should still work
4. Explain this demonstrates graceful degradation

If database connection fails:
1. Check PostgreSQL service status
2. Verify connection string in config
3. Restart Flask app
4. Use backup database dump if needed

If timeline doesn't render:
1. Check browser console for JavaScript errors
2. Verify experiment configuration JSON is valid
3. Refresh page
4. Use ontology info page as backup demo

---

**Status**: Testing checklist ready

**Next Action**: Execute browser testing, update checklist with results
