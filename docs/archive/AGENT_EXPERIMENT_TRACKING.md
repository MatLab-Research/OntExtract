# Agent Semantic Evolution Experiment - Tracking Document

**Created**: 2025-11-16
**Purpose**: Track recreation of the "Agent Semantic Evolution (1910-2024)" experiment from the OntExtract paper
**Paper Reference**: `/home/chris/OntExtract/paper/OntExtract_Short_Paper__CR_.pdf`

---

## Experiment Overview (From Paper)

### **Target Metrics**
- **Documents**: 7 sources (law, philosophy, AI)
- **Time Span**: 114 years (1910-2024)
- **Focus Term**: "agent"
- **Expected Processing**:
  - ~247 segments
  - ~279 entities
  - 23 processing operations
  - 3m 29s processing time
  - 92% LLM confidence

### **Document List (From Paper)**
1. **Black's Law Dictionary 1910** - Legal definition of "agent"
2. **Anscombe (1957)** - "Intention" (philosophical work on intentional action)
3. **Wooldridge & Jennings (1995)** - AI agent foundations
4. **Black's Law Dictionary 2019** - Updated legal definition
5. **Russell & Norvig (2020)** - "Artificial Intelligence: A Modern Approach"
6. **Black's Law Dictionary 2024** - Most recent legal definition
7. **OED 2024** - Oxford English Dictionary entry for "agent"

### **Expected Semantic Shifts (From Paper - Figure 2)**
1. Conceptual continuity across domains
2. Domain-specific semantic networks
3. 1995 inflection point (human → computational)
4. Legal language stability despite tech change
5. Anscombe (1957) as philosophical bridge
6. Stable polysemy by 2024

### **LLM Orchestration Strategy (From Paper)**
- **Stage 1**: Analyze experiment and documents
- **Stage 2**: Recommend processing strategy (92% confidence)
  - Paragraph segmentation for all documents
  - Entity extraction for all documents
  - Definition extraction for all documents
  - Temporal extraction for 2 most comprehensive sources
- **Stage 3**: Human review and approval
- **Stage 4**: Execute 23 tool operations
- **Stage 5**: Generate cross-document synthesis

---

## Current Session Progress

### ✅ **Completed Steps**

#### 1. Database Preparation
- **Date**: 2025-11-16 14:41
- **Action**: Created full database backup
- **Location**: `/home/chris/OntExtract/backups/ontextract_backup_20251116_144044.sql` (705KB)
- **Status**: ✅ Complete

#### 2. Database Reset
- **Date**: 2025-11-16
- **Actions**:
  - Restored backup
  - Cleared all experiments and documents (keeping users)
  - Cleared all term-related data (cascade cleared everything for fresh start)
- **Status**: ✅ Complete
- **Result**: Clean database, users preserved

#### 3. Code Fixes
- **Date**: 2025-11-16
- **Actions**:
  - Restored missing orchestration models:
    - `app/models/orchestration_logs.py`
    - `app/models/orchestration_feedback.py`
  - Updated `app/models/__init__.py` to import orchestration models
  - Fixed template URL building errors (document_uuid → document_id)
  - Fixed document list template (added latest_version attribute)
  - Re-enabled "Temporal Evolution" experiment type in UI
- **Status**: ✅ Complete
- **Files Modified**:
  - `app/models/__init__.py`
  - `app/templates/experiments/new.html`
  - Multiple template files (experiments/results.html, etc.)

#### 4. Application Status
- **Status**: ✅ Running at http://localhost:8765
- **Branch**: `development`
- **Refactoring**: Phase 3 complete (Services + DTOs)

#### 5. Term Creation
- **Date**: 2025-11-16
- **Term Text**: `agent`
- **Term ID**: `07210ad1-20c1-4a13-8694-fc45b0396963`
- **Domain**: `Interdisciplinary`
- **Status**: ✅ Created and confirmed

#### 6. CrossRef Fix
- **Date**: 2025-11-16
- **Issue**: CrossRef auto-extraction giving incorrect metadata (thermodynamic study for Black's 1910, 2016 reprint for Anscombe 1957)
- **Root Cause**: CrossRef title matching was blindly accepting first result without checking match quality
- **Fix Applied**:
  - ✅ Added minimum match score threshold (25.0) in `app/services/crossref_metadata.py` (line 121-129)
  - ✅ Low-confidence matches are now rejected to prevent false positives
  - ✅ Automatic PDF extraction remains enabled for high-quality matches
  - ✅ Added temporal metadata save to `document_temporal_metadata` table in `app/routes/upload.py` (line 486-497)
  - ✅ Added logging to track accepted/rejected matches with scores
- **Status**: ✅ Fixed - automatic extraction now rejects low-confidence matches

#### 7. Document Upload (Programmatic - Complete)
- **Date**: 2025-11-16
- **Method**: Programmatic upload via `upload_agent_documents.py` script
- **Status**: ✅ Complete - All 6 documents uploaded successfully
- **Reason for Programmatic Approach**: PDF title extraction unreliable for historical documents; CrossRef scoring inconsistent
- **Documents Uploaded**:
  - **ID 191**: Black's Law Dictionary 1910 - Agent (1910) - 11.6K chars extracted
  - **ID 192**: Anscombe - Intention (1957) - 25K chars extracted
  - **ID 193**: Wooldridge & Jennings - Intelligent Agents (1995) - 163K chars extracted
  - **ID 194**: Russell & Norvig - AI: A Modern Approach (2020) - Agents Chapter - 84K chars extracted
  - **ID 195**: Black's Law Dictionary 2024 - Agent (2024) - 18.5K chars extracted
  - **ID 196**: Oxford English Dictionary 2024 - Agent (2024) - 44.5K chars extracted
- **Document IDs**: `191, 192, 193, 194, 195, 196`

---

## Next Steps

### 🔄 **Immediate Next Steps**

#### Step 6: Record Term ID
- [ ] Confirm term ID from creation
- [ ] Record domain used
- [ ] Verify term appears in /terms/ list

#### Step 7: Create Experiment
- [ ] Navigate to http://localhost:8765/experiments/new
- [ ] Select "Temporal Evolution" type
- [ ] Configure experiment:
  ```json
  {
    "name": "Agent Semantic Evolution (1910-2024)",
    "type": "temporal_evolution",
    "description": "Semantic analysis of 'agent' across seven documents (1910-2024) spanning law, philosophy, and AI. Tracking conceptual migration from legal representation through philosophical agency to computational autonomy.",
    "configuration": {
      "target_terms": ["agent"],
      "focus_term_id": [TERM_ID_FROM_STEP_6],
      "start_year": 1910,
      "end_year": 2024,
      "domains": ["law", "philosophy", "artificial_intelligence"]
    }
  }
  ```
- [ ] Record experiment ID

#### Step 8: Upload Documents (7 total)
For each document, record:
- [ ] Document name
- [ ] Upload timestamp
- [ ] Document ID
- [ ] File size
- [ ] Year/metadata

**Document Upload Checklist**:
- [ ] 1. Black's Law Dictionary 1910
- [ ] 2. Anscombe - Intention (1957)
- [ ] 3. Wooldridge & Jennings (1995)
- [ ] 4. Black's Law Dictionary 2019
- [ ] 5. Russell & Norvig (2020)
- [ ] 6. Black's Law Dictionary 2024
- [ ] 7. OED 2024 - "agent" entry

#### Step 9: Configure Temporal Analysis
- [ ] Navigate to experiment's temporal analysis page
- [ ] Configure time periods (1910-2024)
- [ ] Set target term to "agent"
- [ ] Enable OED integration if available

#### Step 10: Run LLM Orchestration
- [ ] Start 5-stage orchestration workflow
- [ ] Record Stage 1 (Analysis) output
- [ ] Record Stage 2 (Strategy) recommendations and confidence
- [ ] Review and approve Stage 3 (Human Review)
- [ ] Monitor Stage 4 (Execution) - record operation count and time
- [ ] Review Stage 5 (Synthesis) - semantic shifts identified

---

## Metrics to Track

### **Processing Metrics**
| Metric | Expected (Paper) | Actual | Match? |
|--------|------------------|--------|--------|
| Total Documents | 7 | [TBD] | |
| Segments Created | ~247 | [TBD] | |
| Entities Extracted | ~279 | [TBD] | |
| Processing Operations | 23 | [TBD] | |
| Processing Time | 3m 29s | [TBD] | |
| LLM Confidence | 92% | [TBD] | |

### **Semantic Shifts Identified**
| Shift Pattern | Expected (Paper) | Found? | Notes |
|---------------|------------------|--------|-------|
| 1. Conceptual continuity | ✓ | [TBD] | |
| 2. Domain-specific networks | ✓ | [TBD] | |
| 3. 1995 inflection point | ✓ | [TBD] | |
| 4. Legal stability | ✓ | [TBD] | |
| 5. Anscombe as bridge | ✓ | [TBD] | |
| 6. Stable polysemy by 2024 | ✓ | [TBD] | |

---

## Issues & Resolutions

### Issue 1: Missing Orchestration Models
- **Error**: `ModuleNotFoundError: No module named 'app.models.orchestration_logs'`
- **Cause**: Models deleted in commit 53eeb72 but still referenced by services
- **Resolution**: Restored from git history
- **Status**: ✅ Resolved

### Issue 2: URL Building Errors
- **Error**: `BuildError: Could not build url for endpoint 'text_input.document_detail' with values ['document_uuid']`
- **Cause**: Templates using document_uuid instead of document_id
- **Resolution**: Updated all templates to use document_id
- **Status**: ✅ Resolved

### Issue 3: Document List Template Error
- **Error**: `'dict object' has no attribute 'latest_version'`
- **Cause**: Route not setting latest_version in document groups
- **Resolution**: Added latest_version assignment in crud.py
- **Status**: ✅ Resolved

### Issue 4: Temporal Evolution Hidden
- **Error**: Type not available in UI
- **Cause**: Commented out in template
- **Resolution**: Uncommented in app/templates/experiments/new.html
- **Status**: ✅ Resolved

### Issue 5: Term Deletion Constraint
- **Error**: `null value in column "term_id" of relation "oed_timeline_markers"`
- **Cause**: Foreign key constraints on term deletion
- **Resolution**: Truncated all term tables via SQL
- **Status**: ✅ Resolved

---

## Configuration Settings

### **Database**
- **Type**: PostgreSQL
- **Database**: `ontextract_db`
- **User**: `ontextract_user`
- **Backup**: `/home/chris/OntExtract/backups/ontextract_backup_20251116_144044.sql`

### **Application**
- **URL**: http://localhost:8765
- **Branch**: development
- **Python**: .venv/bin/python (3.12)
- **Flask Debug**: ON

### **LLM Configuration**
- **Provider**: [TBD - likely Claude]
- **Model**: [TBD]
- **Orchestration**: Enabled
- **Expected Confidence**: 92%

---

## Paper Compliance Checklist

### **Architecture & Design**
- [x] PROV-O provenance tracking enabled
- [x] Document versioning implemented
- [x] 5-stage LLM orchestration workflow
- [ ] All 7 documents from paper included
- [ ] Temporal span: 1910-2024
- [ ] Focus term: "agent"

### **Processing Strategy (Figure 2)**
- [ ] Paragraph segmentation (all docs)
- [ ] Entity extraction (all docs)
- [ ] Definition extraction (all docs)
- [ ] Temporal extraction (2 comprehensive docs)
- [ ] ~92% strategy confidence

### **Expected Outputs (Figure 2)**
- [ ] 6 semantic shifts identified
- [ ] 114 years analyzed
- [ ] 7 documents processed
- [ ] Cross-document synthesis generated
- [ ] PROV-O provenance captured

---

## Session Notes

### Session 1 (2025-11-16)
**Goal**: Recreate Agent Semantic Evolution experiment from paper

**Progress**:
1. ✅ Backed up database
2. ✅ Reset database to clean state
3. ✅ Fixed missing orchestration models
4. ✅ Fixed template URL errors
5. ✅ Re-enabled Temporal Evolution type
6. ✅ Created "agent" term
7. 🔄 **PAUSED**: Recording term ID and preparing to create experiment

**Next Session Start Point**:
- Confirm term ID and record in this document
- Proceed with Step 7: Create Experiment

**Time Spent**: ~2 hours

---

## Resumption Checklist (For Next Session)

When resuming this experiment recreation:

1. [ ] Check application is running: http://localhost:8765
2. [ ] Verify database is in correct state:
   ```bash
   PGPASSWORD="PASS" psql -h localhost -U ontextract_user -d ontextract_db -c "SELECT COUNT(*) FROM experiments;"
   # Should return 0 if not yet created, or 1 if experiment created
   ```
3. [ ] Review this tracking document for current status
4. [ ] Continue from "Next Steps" section above
5. [ ] Update metrics as you progress

---

## Quick Reference Commands

### **Database Backup**
```bash
PGPASSWORD="PASS" pg_dump -h localhost -U ontextract_user -d ontextract_db > /home/chris/OntExtract/backups/ontextract_backup_$(date +%Y%m%d_%H%M%S).sql
```

### **Database Restore**
```bash
PGPASSWORD="PASS" psql -h localhost -U ontextract_user -d ontextract_db < /home/chris/OntExtract/backups/ontextract_backup_20251116_144044.sql
```

### **Start Application**
```bash
cd /home/chris/OntExtract
.venv/bin/python run.py
```

### **Check Application Status**
```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8765
# Should return 200 if running
```

---

## Future Improvements

### LLM Text Cleanup Integration
- **Priority**: Medium
- **Description**: Integrate LLM text cleanup into the automated orchestration workflow
- **Current State**: LLM cleanup exists as separate manual button ("Clean Text with LLM")
- **Desired State**: Orchestration workflow should automatically recommend/run text cleanup when needed
- **Implementation Notes**:
  - Add cleanup as a recommended processing step in Stage 2 (Strategy)
  - Allow LLM to detect when documents need cleanup (OCR errors, formatting issues)
  - Include cleanup results in Stage 4 (Execution)
  - Track cleanup provenance in PROV-O chain

---

**Last Updated**: 2025-11-16 21:15 EST
**Status**: ✅ Experiment Created - Ready for LLM Orchestration
**Next Action**: Run 5-stage LLM orchestration workflow
