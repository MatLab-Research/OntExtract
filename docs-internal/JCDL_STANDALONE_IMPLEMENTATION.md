# OntExtract JCDL 2025 Conference Demo

**Conference**: JCDL (Joint Conference on Digital Libraries)
**Dates**: December 15-19, 2025
**Paper**: "LLM-Orchestrated Document Processing: Intelligent Tool Selection for Historical Text Analysis"
**Status**: DEMO-READY - Presentation Enhancements Phase
**Last Updated**: 2025-11-23 (Session 25)

---

## Current Status: Core Implementation Complete

### Implemented Features

**Phase 1 & 2: Ontology-Informed UI** ✅ COMPLETE
- LocalOntologyService reads semantic-change-ontology-v2.ttl (34 classes, 33 citations)
- Event type dropdown populated from validated ontology
- Definitions and citations displayed in UI
- Ontology metadata shown on timeline cards
- Pellet reasoner validation verified
- Fallback to hardcoded types if ontology fails

**LLM Orchestration Pipeline** ✅ COMPLETE
- 5-stage LangGraph workflow with PROV-O provenance
- Strategy recommendation and human review
- Cross-document synthesis
- Error handling with retry and timeout

**Temporal Analysis System** ✅ COMPLETE
- Period boundaries with START/END markers
- Semantic change events with ontology types
- Full-page timeline visualization
- Document-based period generation
- Period color coding (unique colors per period)
- Hover highlighting for paired boundaries

**UI Polish** ✅ COMPLETE
- Streamlined experiment creation workflow
- Quick Add Reference (MW/OED dictionary lookup)
- Auto-fill features for temporal evolution
- Icon-only trash buttons
- Select All/Deselect All for documents

**Demo Data** ✅ COMPLETE
- Experiment 83: "agent Temporal Evolution" (1910-2024)
  - 7 documents, 4 periods, ontology-backed events
  - Legal → Philosophical → AI → Contemporary evolution
- Experiment 84: "Professional Ethics Evolution" (1867-1947)
  - 6 documents, 4 periods
  - Early Foundations → Progressive Era → Interwar → Wartime
- Demo credentials: demo/demo123

**Recent Enhancements (Session 25)** ✅ COMPLETE
- Fixed trash can button errors (period/event removal)
- Period color coding: unique colors for boundary pairs
- Hover highlighting: paired boundaries light up together
- Created meaningful historical periods for demos

---

## Presentation Enhancements (Pre-Conference)

### Priority 1: Visual Polish (Estimated: 2-3 hours)

**1.1 Timeline Export/Screenshots** (1 hour)
- [ ] Add "Export Timeline as PNG" button
- [ ] Prepare high-quality screenshots for slides
- [ ] Test timeline rendering at different resolutions
- [ ] Create print-friendly CSS (optional)

**1.2 Ontology Badge Enhancement** (30 min)
- [ ] Make ontology badges more prominent/professional
- [ ] Add tooltip showing ontology validation status
- [ ] Consider: Shield icon → academic citation icon

**1.3 Period Visual Improvements** (30 min)
- [ ] Test color coding with 5+ overlapping periods
- [ ] Ensure colors are distinguishable (accessibility check)
- [ ] Add optional period labels to timeline axis
- [ ] Consider: Timeline zoom/pan controls (optional)

**1.4 Event Type Filtering** (1 hour - optional)
- [ ] Add filter to show/hide events by type
- [ ] Color legend for semantic event types
- [ ] Quick toggle: show all / hide all events

### Priority 2: Demo Flow Polish (Estimated: 2 hours)

**2.1 Demo Experiment Refinement** (1 hour)
- [ ] Review experiment 83 event descriptions (make them compelling)
- [ ] Review experiment 84 event descriptions
- [ ] Add 1-2 more semantic events if timeline looks sparse
- [ ] Verify all events have proper citations

**2.2 Walkthrough Script** (1 hour)
- [ ] Document demo flow (step-by-step)
- [ ] Prepare talking points for each screen
- [ ] Create backup demo plan (if primary fails)
- [ ] Test complete workflow 2-3 times

### Priority 3: Presentation Materials (Estimated: 3-4 hours)

**3.1 Slides Preparation** (2 hours)
- [ ] Screenshot: Ontology dropdown with definitions
- [ ] Screenshot: Timeline with color-coded periods
- [ ] Screenshot: Event card with citation
- [ ] Screenshot: LLM orchestration progress modal
- [ ] Diagram: System architecture (standalone mode)
- [ ] Diagram: Event type ontology hierarchy

**3.2 Demo Video (Optional)** (1-2 hours)
- [ ] Record 2-minute demo walkthrough
- [ ] Backup in case live demo fails
- [ ] Can be shared with reviewers

**3.3 Handout/Poster** (30 min - if required)
- [ ] QR code to demo site (if hosting online)
- [ ] Key features list
- [ ] Architecture diagram
- [ ] Contact information

### Priority 4: Testing & Verification (Estimated: 2-3 hours)

**4.1 Browser Testing** (1 hour)
- [ ] Chrome/Edge (primary)
- [ ] Firefox (secondary)
- [ ] Safari (if Mac available)
- [ ] Test on presentation laptop
- [ ] Test without internet (offline mode)

**4.2 Performance Testing** (30 min)
- [ ] Load time for experiment 83/84
- [ ] Ontology load time (<100ms)
- [ ] Timeline rendering with 10+ events
- [ ] Browser console: no errors

**4.3 End-to-End Testing** (1 hour)
- [ ] Complete workflow: Create → Upload → Periods → Events → Timeline
- [ ] Quick Add Reference (MW/OED)
- [ ] Period color coding works correctly
- [ ] Hover highlighting works
- [ ] Event editing/deletion works
- [ ] Full-page timeline view

**4.4 Failure Mode Testing** (30 min)
- [ ] Ontology file missing → fallback works
- [ ] Invalid document upload → error handling
- [ ] Network timeout → graceful degradation
- [ ] Large document (500+ pages) → progress indicator

---

## Conference Day Checklist

### Pre-Demo Setup (Day Before)
- [ ] Install app on presentation laptop
- [ ] Verify PostgreSQL running
- [ ] Create fresh demo experiments 83 & 84
- [ ] Test complete demo flow 2x
- [ ] Clear browser cache/cookies
- [ ] Set browser zoom to optimal level
- [ ] Close unnecessary tabs/windows
- [ ] Disable notifications/popups
- [ ] Have backup screenshots ready

### Demo Day Morning
- [ ] Start PostgreSQL
- [ ] Start Flask app (check logs for errors)
- [ ] Login as demo/demo123
- [ ] Navigate to experiment 83
- [ ] Quick sanity check (timeline loads, colors work)
- [ ] Have backup USB drive with slides/video

### During Presentation
- [ ] Start with overview slide
- [ ] Live demo: Show experiment 83 timeline
- [ ] Highlight ontology-backed event types
- [ ] Show period color coding
- [ ] Demonstrate hover highlighting
- [ ] Show citation on event card
- [ ] (Optional) Create new event live
- [ ] End with architecture slide

### Talking Points
1. **Primary Contribution**: LLM orchestration for document processing
   - "System recommends analysis strategies based on document characteristics"
   - "Human-in-the-loop validation ensures quality"
   - "Cross-document synthesis provides holistic analysis"

2. **Ontology-Informed Design**:
   - "Event types derived from validated ontology (34 classes, 33 citations)"
   - "Pellet reasoner verified logical consistency"
   - "Academic rigor: definitions and citations shown in UI"

3. **Temporal Analysis**:
   - "Color-coded period boundaries make nested periods clear"
   - "Hover highlighting helps identify paired boundaries"
   - "Full-page timeline optimized for presentation"

4. **Demo Highlights**:
   - "114-year evolution of 'agent' concept"
   - "Legal → Philosophical → AI → Contemporary"
   - "Documents from Black's Law Dictionary, Anscombe, Wooldridge, Russell & Norvig"

---

## Known Limitations (For Q&A)

**Limitation 1**: Standalone mode (no SPARQL endpoint)
- **Response**: "Prioritized deployment simplicity for demo; full semantic web integration planned for journal version"
- **Evidence**: Show validated ontology file

**Limitation 2**: Manual period creation
- **Response**: "Future work: LLM-powered period detection from document clustering"

**Limitation 3**: Single-user demo
- **Response**: "Multi-user collaboration features planned for production deployment"

**Limitation 4**: No automatic event detection
- **Response**: "System provides scaffolding; expert knowledge required for event identification (by design)"

---

## Post-Conference TODO

### Immediate (Dec 20-31, 2025)
- [ ] Collect feedback from conference attendees
- [ ] Document suggested improvements
- [ ] Update paper based on reviewer questions

### Short-Term (Jan 2026)
- [ ] Full OntServe integration (replace LocalOntologyService)
- [ ] SPARQL query interface
- [ ] RDF export for linked open data
- [ ] Database migration (semantic_events table)

### Long-Term (Feb-Mar 2026)
- [ ] Journal paper submission
- [ ] Multi-user support
- [ ] LLM-powered period detection
- [ ] Automatic event suggestion
- [ ] Timeline export formats (PDF, SVG, JSON)

---

## Resources

### Demo URLs
- **Experiment 83 Management**: http://localhost:8765/experiments/83/manage_temporal_terms
- **Experiment 83 Timeline**: http://localhost:8765/experiments/83/timeline
- **Experiment 84 Management**: http://localhost:8765/experiments/84/manage_temporal_terms
- **Experiment 84 Timeline**: http://localhost:8765/experiments/84/timeline
- **Create New Experiment**: http://localhost:8765/experiments/new
- **Credentials**: demo / demo123

### Documentation
- **Demo Data Summary**: [DEMO_EXPERIMENT_SUMMARY.md](DEMO_EXPERIMENT_SUMMARY.md)
- **Testing Checklist**: [JCDL_TESTING_CHECKLIST.md](JCDL_TESTING_CHECKLIST.md)
- **Ontology Validation**: [VALIDATION_GUIDE.md](VALIDATION_GUIDE.md)
- **Ontology File**: [ontologies/semantic-change-ontology-v2.ttl](ontologies/semantic-change-ontology-v2.ttl)
- **Architecture**: [LLM_WORKFLOW_REFERENCE.md](LLM_WORKFLOW_REFERENCE.md)
- **Session Summaries**: [SESSION_20_SUMMARY.md](SESSION_20_SUMMARY.md)

### Scripts
- **Create Demo Experiment**: `scripts/create_demo_experiment.py`
- **Add Periods (Exp 83)**: `scripts/create_periods_experiment_83.py`
- **Add Periods (Exp 84)**: `scripts/create_periods_experiment_84.py`

---

## Estimated Time to Conference Ready

**Current Status**: 85% ready

**Remaining Work**:
- Visual polish: 2-3 hours
- Demo refinement: 2 hours
- Presentation materials: 3-4 hours
- Testing: 2-3 hours

**Total**: 9-12 hours over 1-2 weeks

**Recommended Schedule**:
- **Week of Dec 1-7**: Visual polish, demo refinement
- **Week of Dec 8-14**: Presentation materials, final testing
- **Dec 15**: Conference demo

---

## Success Criteria

**Demo Day Success** = All checkboxes YES:
- [ ] App starts without errors on presentation laptop
- [ ] Timeline loads in <2 seconds
- [ ] Period color coding displays correctly
- [ ] Hover highlighting works smoothly
- [ ] Ontology metadata visible in UI
- [ ] Citations appear on event cards
- [ ] No JavaScript errors in console
- [ ] Backup screenshots/video ready
- [ ] Presenter confident in demo flow

**Paper Success** = Reviewers understand:
- [ ] Primary contribution: LLM orchestration
- [ ] Secondary contribution: Ontology-informed design
- [ ] System demonstrates scholarly rigor
- [ ] Clear path to full semantic web integration

---

**Last Updated**: 2025-11-23 (Session 25)
**Status**: DEMO-READY - Enhancements Phase
**Next Action**: Visual polish and presentation materials (9-12 hours)
