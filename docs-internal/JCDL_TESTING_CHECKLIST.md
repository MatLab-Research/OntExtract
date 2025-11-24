# JCDL Demo Final Verification Checklist

**Conference**: JCDL 2025 (Dec 15-19)
**Demo Experiments**: 83 (agent), 84 (professional ethics)
**Credentials**: demo / demo123
**Last Updated**: 2025-11-23

---

## Pre-Conference Testing (1-2 days before)

### Environment Setup
- [ ] PostgreSQL running on presentation laptop
- [ ] Flask app starts without errors
- [ ] No warnings in startup logs
- [ ] Database: ontextract_db accessible
- [ ] Browser: Clear cache/cookies before testing

### Experiment 83: Agent Temporal Evolution (1910-2024)

**URL**: http://localhost:8765/experiments/83/manage_temporal_terms

- [ ] Timeline loads in < 2 seconds
- [ ] All 4 periods display with correct colors
  - Legal-Juridical Era (1910-1955) - unique color
  - Philosophical Foundations (1956-1994) - unique color
  - AI Revolution (1995-2021) - unique color
  - Contemporary Convergence (2022-2024) - unique color
- [ ] Period color coding: each period has distinct color
- [ ] Hover highlighting: hover over START → both START and END light up
- [ ] 7 document cards display (1910, 1956, 1995, 2019, 2022, 2024)
- [ ] Semantic events show proper event types and citations
- [ ] Full-page timeline view works: http://localhost:8765/experiments/83/timeline
- [ ] No JavaScript errors in browser console

### Experiment 84: Professional Ethics Evolution (1867-1947)

**URL**: http://localhost:8765/experiments/84/manage_temporal_terms

- [ ] Timeline loads in < 2 seconds
- [ ] All 4 periods display with correct colors
  - Early Foundations (1867-1905) - unique color
  - Progressive Era Standardization (1906-1919) - unique color
  - Interwar Social Responsibility (1920-1942) - unique color
  - Wartime and Post-War Accountability (1943-1947) - unique color
- [ ] 6 document cards display (1867, 1906, 1912, 1920, 1943, 1947)
- [ ] Full-page timeline view works: http://localhost:8765/experiments/84/timeline
- [ ] No JavaScript errors in browser console

### Ontology Features

- [ ] Event type dropdown populates (18 types)
- [ ] Definitions display when event type selected
- [ ] Citations appear on event cards (book icon)
- [ ] Ontology badge visible on "Event Type" label
- [ ] Ontology info page works: http://localhost:8765/experiments/ontology/info

### Key Interactions

- [ ] Create new semantic event:
  - Open modal
  - Select event type → definition displays
  - Fill in periods and description
  - Save → appears on timeline
  - Refresh page → event persists
- [ ] Edit existing event → changes save
- [ ] Delete event → card removed (trash icon works)
- [ ] Delete period boundary → START/END both removed
- [ ] Hover over period boundary → paired boundary highlights

### Browser Compatibility

Test on presentation laptop browser:
- [ ] Chrome/Edge (primary) - Version: _____
- [ ] Firefox (backup) - Version: _____
- [ ] Resolution: 1920x1080 (or presentation display)
- [ ] Text readable at projector distance

### Offline Mode

- [ ] Disconnect network
- [ ] Restart Flask app
- [ ] Ontology loads from local file
- [ ] All features work without internet

---

## Demo Day Morning (2-3 hours before)

### Startup Sequence
- [ ] Start PostgreSQL: `sudo systemctl start postgresql` (or equivalent)
- [ ] Activate venv: `source venv-ontextract/bin/activate`
- [ ] Start Flask: `python run.py` (or `flask run`)
- [ ] Verify: http://localhost:8765 loads
- [ ] Login: demo / demo123

### Quick Smoke Test (5 minutes)
- [ ] Navigate to experiment 83
- [ ] Timeline displays correctly
- [ ] Colors visible
- [ ] Hover highlighting works
- [ ] Open full-page timeline
- [ ] Navigate to experiment 84
- [ ] Timeline displays correctly
- [ ] No errors in console

### Browser Setup
- [ ] Set optimal zoom level (100% or 110%)
- [ ] Bookmark: http://localhost:8765/experiments/83/timeline
- [ ] Bookmark: http://localhost:8765/experiments/84/timeline
- [ ] Close all unnecessary tabs
- [ ] Disable notifications
- [ ] Disable system updates/alerts
- [ ] Full screen mode ready (F11)

### Backup Materials
- [ ] Screenshots of both timelines (high-res)
- [ ] PDF export of ontology info page
- [ ] Database backup: `pg_dump ontextract_db > backup.sql`
- [ ] Slides with static images (if demo fails)
- [ ] Talking points printed

---

## During Demo

### Opening (30 seconds)
- [ ] Start with overview slide
- [ ] Explain primary contribution: LLM orchestration
- [ ] Mention secondary contribution: ontology-informed design

### Live Demo - Experiment 83 (2-3 minutes)
- [ ] Navigate to timeline view
- [ ] Highlight: "114 years of 'agent' evolution"
- [ ] Point out color-coded periods
- [ ] Demonstrate hover highlighting
- [ ] Show semantic event with citation
- [ ] Explain: "Event types from validated ontology"

### Ontology Evidence (30 seconds)
- [ ] Navigate to ontology info page
- [ ] Show: "34 classes, 33 citations, Pellet validated"
- [ ] Return to timeline

### Optional: Create Event Live (1-2 minutes)
- [ ] Open "Add Semantic Event"
- [ ] Show dropdown with definitions
- [ ] Select event type → definition appears
- [ ] Explain: "Academic rigor built into UI"
- [ ] (Save or cancel - don't spend too much time)

### Closing (30 seconds)
- [ ] Summarize: LLM orchestration + ontological rigor
- [ ] Show architecture slide
- [ ] Open for questions

---

## Emergency Procedures

### If Timeline Won't Load
1. Check browser console for specific error
2. Refresh page (Ctrl+F5)
3. Restart Flask app
4. **Fallback**: Show screenshot slides

### If Hover Highlighting Fails
1. Not critical - demonstrate with mouse movements
2. Explain: "Period boundaries paired by unique colors"
3. Continue demo

### If Database Connection Lost
1. Check PostgreSQL: `sudo systemctl status postgresql`
2. Restart PostgreSQL: `sudo systemctl restart postgresql`
3. Restart Flask app
4. **Fallback**: Use backup database: `psql ontextract_db < backup.sql`

### If JavaScript Errors Appear
1. Clear browser cache
2. Refresh page
3. **Fallback**: Navigate to different experiment (83 ↔ 84)
4. **Last resort**: Use static screenshots

### If Network Required (Shouldn't Happen)
1. Ontology is local file - no network needed
2. All features work offline
3. If MW/OED lookup needed, explain: "External API, not core feature"

---

## Success Criteria

**Demo is successful if:**
- [ ] Timeline displays with color-coded periods
- [ ] At least one semantic event shows citation
- [ ] Audience sees "ontology-informed design"
- [ ] No critical errors during 5-minute demo
- [ ] Presenter remains calm and confident

**Nice to have:**
- [ ] Hover highlighting works smoothly
- [ ] Live event creation demonstrates dropdown
- [ ] Ontology info page impresses reviewers

---

## Post-Demo

- [ ] Collect feedback from attendees
- [ ] Note questions asked (for paper revision)
- [ ] Document any issues encountered
- [ ] Update paper based on reviewer comments

---

**Status**: Ready for final verification

**Estimated Testing Time**: 30-45 minutes

**Last Verification Date**: _____________

**Tester**: _____________

**Result**: PASS / FAIL / NEEDS WORK

**Notes**:
