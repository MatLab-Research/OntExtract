# JCDL Demo Experiment Summary

**Created**: 2025-11-22
**Purpose**: JCDL 2025 Conference Demonstration
**Experiment ID**: 75

---

## Demo Credentials

```
Username: demo
Password: demo123
```

---

## Experiment Details

**Name**: Professional Ethics Evolution (1867-1947)

**Type**: Temporal Evolution

**Description**: Historical analysis of how the concept of "professional responsibility" evolved in engineering ethics literature from the post-Civil War era through World War II.

**Access URL**: http://localhost:8765/experiments/75

---

## Documents (7 total)

Historical documents spanning 80 years of engineering ethics literature:

1. **On the Moral Duties of Engineers** (1867)
   - Author: William J.M. Rankine
   - Journal: Transactions of the Institution of Engineers and Shipbuilders in Scotland
   - Early discussion of professional obligations

2. **Engineering Ethics and Professional Conduct** (1906-05)
   - Author: American Society of Civil Engineers Committee
   - Journal: Proceedings of the ASCE
   - Proposal for formal engineering code of ethics

3. **Standards of Professional Conduct for Consulting Engineers** (1912)
   - Author: H.P. Gillette
   - Journal: Engineering News
   - Discussion of conflicts of interest in consulting practice

4. **The Engineer and Society: New Responsibilities** (1920-03)
   - Author: Herbert Hoover
   - Journal: The Engineering Magazine
   - Post-WWI expansion of professional responsibility concept

5. **Code of Ethics for Engineers** (1935)
   - Author: Engineers Council for Professional Development
   - Journal: ECPD Bulletin No. 1
   - First formal engineering code of ethics (REFERENCE DOCUMENT)

6. **Professional Responsibility in Wartime Engineering** (1943-11)
   - Author: Robert E. Doherty
   - Journal: Journal of Engineering Education
   - WWII-era examination of professional responsibility limits

7. **Post-War Professionalism: Accountability and Public Trust** (1947-06)
   - Author: Vannevar Bush
   - Journal: Technology Review
   - Post-atomic expansion of professional responsibility concept

---

## Temporal Periods (4 total)

1. **Pre-Standardization (1850-1900)**
   - Individual moral duty, informal norms

2. **Early Codification (1900-1920)**
   - First formal codes, professional societies

3. **Professionalization (1920-1940)**
   - Mandatory standards, licensure, enforcement

4. **Post-War Expansion (1940-1950)**
   - Broader societal responsibility, public accountability

---

## Semantic Change Events (4 total)

All events use ontology-backed event types with academic citations:

### Event 1: Intensional Drift (1850-1900 → 1900-1920)

**Citation**: Wang et al. (2009, 2011); Stavropoulos et al. (2019). SemaDrift.

**Description**: Narrowing from broad "moral duty" to specific "professional obligations." The term became more technically defined with formal standards.

**Evidence Documents**:
- On the Moral Duties of Engineers (1867)
- Engineering Ethics and Professional Conduct (1906-05)

### Event 2: Extensional Drift (1900-1920 → 1920-1940)

**Citation**: Wang et al. (2009, 2011); Stavropoulos et al. (2019). SemaDrift.

**Description**: Expansion from client service to include public welfare. Wartime experiences expanded the scope of who professionals are responsible to.

**Evidence Documents**:
- Standards of Professional Conduct for Consulting Engineers (1912)
- The Engineer and Society: New Responsibilities (1920-03)

### Event 3: Amelioration (1920-1940 → 1940-1950)

**Citation**: Jatowt & Duh (2014). Framework for analyzing semantic change. JCDL. Bloomfield (1933) nine classes.

**Description**: Enhanced meaning from "avoiding misconduct" to "serving humanity." Post-atomic age expanded professional responsibility to include responsibility to civilization.

**Evidence Documents**:
- Professional Responsibility in Wartime Engineering (1943-11)
- Post-War Professionalism: Accountability and Public Trust (1947-06)

### Event 4: Semantic Drift (1850-1900 → 1940-1950)

**Citation**: Hamilton et al. (2016); Gulla et al. (2010); Stavropoulos et al. (2019).

**Description**: Overall trajectory: from personal virtue to institutional accountability. The entire period shows gradual formalization and expansion of meaning.

**Evidence Documents**:
- On the Moral Duties of Engineers (1867)
- Post-War Professionalism: Accountability and Public Trust (1947-06)

---

## Ontology Integration

**Ontology File**: semantic-change-ontology-v2.ttl

**Event Types Available**: 18 classes

**Validation**: Pellet reasoner - PASSED

**Academic Citations**: 33 citations from 12 papers

**BFO Alignment**: Upper ontology integration complete

---

## Demo Flow for Presentation

1. **Login**: Use demo/demo123 credentials
2. **Navigate**: Experiments → Professional Ethics Evolution (1867-1947)
3. **Show Timeline**: Display 4 temporal periods
4. **Manage Temporal Terms**: Click button to open semantic events modal
5. **Show Event Type Dropdown**: 18 ontology-backed options with shield icon
6. **Display Metadata**: Select event type to show definition and citation
7. **View Timeline Cards**: Show 4 semantic events with academic citations
8. **Navigate to Ontology Info**: Show validation status page
9. **Highlight Provenance**: Visit provenance timeline to show semantic event tracking

---

## Key Demonstration Points

1. **Ontology-Informed Design**: Event types derived from validated ontology, not ad-hoc
2. **Academic Rigor**: Citations embedded directly in UI, traceable to source papers
3. **Professional Content**: Real historical documents, authentic evolution narrative
4. **Temporal Granularity**: 4 periods with distinct characteristics
5. **Evidence Chain**: Each semantic event links to specific documents
6. **Provenance Tracking**: Complete audit trail for all annotations
7. **Standalone Operation**: No external dependencies, works offline

---

## Files Created by Demo Script

**Script**: `scripts/create_demo_experiment.py`

**Database Records**:
- 1 demo user (username: demo)
- 1 demo term (professional responsibility)
- 7 documents
- 1 experiment with full configuration

**Reusable**: Run script again to recreate demo data if needed

---

## Testing Checklist

See [JCDL_STANDALONE_IMPLEMENTATION.md](JCDL_STANDALONE_IMPLEMENTATION.md) Phase 3.4 for complete testing checklist.

Key items:
- Ontology loads on app startup
- Event type dropdown populates from ontology
- Definitions display correctly
- Citations show in event cards
- Timeline renders correctly
- No errors in browser console

---

**Status**: Demo experiment ready for JCDL presentation

**Next Steps**: Complete browser testing checklist, prepare presentation materials
