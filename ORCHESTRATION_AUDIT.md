# Orchestration Infrastructure Audit

**Created:** 2025-11-20
**Purpose:** Assess existing "Human-in-the-Loop" and "Orchestration" infrastructure
**Decision Needed:** Build on existing code vs. clean slate

---

## Summary

**GOOD NEWS:** You have **~70% of the LLM Analyze feature already implemented!**

There are TWO separate orchestration systems that need to be consolidated:
1. **`/orchestration/`** blueprint (NEW, partial LangGraph implementation) ✅ 70% complete
2. **`/experiments/<id>/orchestrated_analysis`** routes (OLD, simpler approach) ⚠️ Incomplete/unused

---

## System 1: `/orchestration/` Blueprint (PREFERRED - Build on this!)

**Location:** `app/routes/orchestration.py` + `app/orchestration/`

### ✅ What's Already Implemented

#### Backend Infrastructure (70% complete)

1. **LangGraph Workflow** ✅ COMPLETE
   - `app/orchestration/experiment_graph.py` - StateGraph with conditional branching
   - `app/orchestration/experiment_nodes.py` - All 5 stage nodes (analyze, recommend, review, execute, synthesize)
   - `app/orchestration/experiment_state.py` - TypedDict state management
   - Uses Claude Sonnet 4 API
   - Async execution with asyncio

2. **Database Model** ✅ COMPLETE
   - `ExperimentOrchestrationRun` model - Stores all 5 stages
   - Fields for each stage output
   - Status tracking (analyzing, strategy_ready, executing, completed, failed)
   - JSONB fields for recommended_strategy, processing_results, execution_trace

3. **API Endpoints** ✅ 50% COMPLETE
   - ✅ `POST /orchestration/analyze-experiment/<id>` - Start workflow (Stages 1-2)
   - ✅ `GET /orchestration/experiment/<run_id>/status` - SSE progress stream
   - ✅ `GET /orchestration/review-strategy/<run_id>` - Review page
   - ❌ `POST /orchestration/approve-strategy/<run_id>` - MISSING (needs implementation)
   - ✅ `GET /orchestration/view-results/<run_id>` - Results display

4. **Frontend Integration** ✅ 40% COMPLETE
   - ✅ Button exists in `document_pipeline.html` (line 485)
   - ✅ Click handler `startExperimentOrchestration()` (line 492-531)
   - ✅ SSE progress tracking `startExperimentProgressTracking()` (line 536)
   - ✅ Progress modal exists `experimentProgressModal`
   - ✅ Navigation to review page when strategy ready
   - ❌ Review modal/page - MISSING template `review_strategy.html`
   - ❌ Results display needs update

5. **Results Templates** ✅ COMPLETE
   - `app/templates/experiments/orchestration_results.html` - Basic view
   - `app/templates/experiments/orchestration_results_enhanced.html` - Enhanced view
   - Shows cross-document insights, confidence, processing summary
   - Download PROV-O JSON

### ❌ What's Missing (30%)

1. **Strategy Review Page** - ❌ CRITICAL MISSING
   - Template: `app/templates/orchestration/review_strategy.html` doesn't exist
   - Route exists at line 265 in orchestration.py but template missing
   - Should show:
     - Recommended tools per document
     - LLM reasoning
     - Confidence scores
     - Approve/modify buttons

2. **Approve Strategy Endpoint** - ❌ MISSING
   - Need: `POST /orchestration/approve-strategy/<run_id>`
   - Should:
     - Accept strategy_approved, modified_strategy, review_notes
     - Execute Stages 4-5 (execute + synthesize)
     - Update run status to 'executing' → 'completed'

3. **Tool Execution Integration** - ❌ MISSING
   - `execute_strategy_node()` exists but doesn't call real tools
   - Need to connect to:
     - `PipelineService._process_segmentation`
     - `PipelineService._process_entities`
     - `PipelineService._process_definitions`
     - `PipelineService._process_temporal`
     - `PipelineService._process_embeddings`

4. **Results Navigation** - ⚠️ NEEDS UPDATE
   - Results template exists but needs proper navigation from review page
   - Need redirect after approval to results page

---

## System 2: `/experiments/<id>/orchestrated_analysis` Routes (DEPRECATED - Remove?)

**Location:** `app/routes/experiments/orchestration.py`

### What Exists

1. **Routes** (Partially implemented, NOT connected)
   - `GET /<int:id>/orchestrated_analysis` - Expects missing template
   - `POST /<int:id>/create_orchestration_decision` - Creates OrchestrationDecision
   - `POST /<int:id>/run_orchestrated_analysis` - Simulated analysis
   - `GET /<int:id>/orchestration-results` - Results page (different from System 1!)
   - `GET /<int:id>/orchestration-provenance.json` - PROV-O download

2. **Database Models** (Older design)
   - `OrchestrationDecision` - Individual term-based decisions
   - `OrchestrationFeedback` - User feedback
   - `LearningPattern` - Adaptive learning

3. **Service**
   - `OrchestrationService` - Simpler orchestration logic
   - Uses `AdaptiveOrchestrationService`
   - Not integrated with LangGraph

### Problems with System 2

- **Missing Template:** `orchestrated_analysis.html` doesn't exist (500 error)
- **Incomplete:** Uses simulated analysis, not real LLM orchestration
- **Different Design:** Term-based decisions vs. experiment-level orchestration
- **Duplicate Routes:** Conflicts with System 1 orchestration blueprint
- **Not Used:** No frontend links except in old `temporal_term_manager.html`

---

## Recommendation: Consolidate on System 1

### Option A: Build on System 1 (RECOMMENDED) ✅

**Effort:** 8-10 hours
**Approach:** Complete the missing 30% of System 1, deprecate System 2

**Tasks:**
1. Create `review_strategy.html` template (3-4 hours)
   - Show recommended tools per document
   - Display LLM reasoning and confidence
   - Approve/modify interface
   - Submit to approval endpoint

2. Implement `POST /orchestration/approve-strategy/<run_id>` (2-3 hours)
   - Update ExperimentOrchestrationRun with approval
   - Execute Stages 4-5
   - Redirect to results

3. Connect `execute_strategy_node()` to real tools (2-3 hours)
   - Import PipelineService
   - Map tool names to methods
   - Execute and store results
   - Update processing_results JSONB

4. Clean up System 2 (1 hour)
   - Remove or mark deprecated:
     - `app/routes/experiments/orchestration.py`
     - `OrchestrationDecision`, `OrchestrationFeedback`, `LearningPattern` models
     - `OrchestrationService`
   - Update links in templates to point to System 1

**Pros:**
- ✅ Already 70% complete
- ✅ Uses LangGraph (aligns with paper)
- ✅ Real Claude integration
- ✅ Proper 5-stage workflow
- ✅ SSE progress tracking
- ✅ Clean architecture

**Cons:**
- ❌ Need to clean up old System 2 code

---

### Option B: Start Fresh (NOT RECOMMENDED) ❌

**Effort:** 14-18 hours (from implementation plan)
**Approach:** Ignore both systems, implement from scratch

**Cons:**
- ❌ Throws away 70% complete System 1
- ❌ Duplicate work
- ❌ More time required
- ❌ Need to understand/remove existing code anyway

---

## Detailed Status: System 1 Components

### ✅ COMPLETE - Can Use As-Is

```
app/orchestration/
├── experiment_graph.py          ✅ StateGraph workflow
├── experiment_nodes.py          ✅ All 5 stage implementations
├── experiment_state.py          ✅ State management
├── __init__.py                  ✅ Module setup
├── graph.py                     ✅ (older version, may be deprecated)
├── nodes.py                     ✅ (older version, may be deprecated)
└── state.py                     ✅ (older version, may be deprecated)

app/models/
├── experiment_orchestration_run.py  ✅ Complete schema
└── [PROV-O models]                  ✅ Already implemented

app/routes/
└── orchestration.py             ✅ 80% complete (missing approve endpoint)

app/templates/experiments/
├── orchestration_results.html           ✅ Basic results view
└── orchestration_results_enhanced.html  ✅ Enhanced results view
```

### ❌ MISSING - Need to Create

```
app/templates/orchestration/
└── review_strategy.html         ❌ CRITICAL - Strategy review interface

app/routes/orchestration.py
└── approve_strategy()           ❌ POST endpoint for approval

app/orchestration/experiment_nodes.py
└── execute_strategy_node()      ⚠️ EXISTS but needs tool integration
```

### Frontend Integration Status

```javascript
// document_pipeline.html - Line 485-533

✅ Button HTML (line 485-491)
✅ Click handler (line 492-531)
✅ Fetch to /orchestration/analyze-experiment (line 500)
✅ SSE progress tracking (line 536-570)
✅ Modal display (line 516-517)
✅ Navigation to review page (line 559-561)

❌ Review modal/page template MISSING
❌ Results navigation after approval INCOMPLETE
```

---

## Proposed Consolidation Plan

### Phase 1: Complete System 1 (8-10 hours)

#### Task 1.1: Create Review Strategy Page (3-4 hours)
**File:** `app/templates/orchestration/review_strategy.html`

```html
<!-- Strategy Review Interface -->
- Display experiment goal & term context
- Show recommended tools per document
  - Document title
  - Recommended tools (checkboxes)
  - LLM reasoning
  - Confidence bar
- Modify strategy section
  - Add/remove tools
  - Add review notes
- Approve/Reject buttons
- Submit to POST /orchestration/approve-strategy/<run_id>
```

#### Task 1.2: Implement Approval Endpoint (2-3 hours)
**File:** `app/routes/orchestration.py`

```python
@orchestration_bp.route('/approve-strategy/<run_id>', methods=['POST'])
def approve_strategy(run_id):
    # 1. Get orchestration run
    # 2. Update with approval data
    # 3. Execute Stages 4-5 in background thread
    # 4. Return success + redirect to results
```

#### Task 1.3: Connect Tools to Execution (2-3 hours)
**File:** `app/orchestration/experiment_nodes.py` (line 224-296)

```python
async def execute_strategy_node(state):
    # Current: Uses placeholder get_tool_registry()
    # Need: Import and use PipelineService

    from app.services.pipeline_service import get_pipeline_service
    pipeline_service = get_pipeline_service()

    # Map tool names to methods:
    tool_map = {
        'segment_paragraph': pipeline_service._process_segmentation,
        'extract_entities': pipeline_service._process_entities,
        ...
    }
```

#### Task 1.4: Update Navigation & Results (1 hour)
- Fix redirect from review page after approval
- Update results page to show tool execution results
- Test end-to-end flow

---

### Phase 2: Deprecate System 2 (1-2 hours)

#### Task 2.1: Mark Deprecated
**Files to deprecate:**
- `app/routes/experiments/orchestration.py` - Add deprecation notice, keep for backward compatibility
- Update `OrchestrationService` - Add deprecation warnings

#### Task 2.2: Update Template Links
- `app/templates/experiments/temporal_term_manager.html` - Update links to System 1
- `app/templates/experiments/view.html` - Ensure uses System 1 routes

#### Task 2.3: Database Cleanup (Optional)
- Keep `OrchestrationDecision` for now (may have historical data)
- Document migration path if needed

---

## Testing Checklist

After consolidation:

- [ ] Click "LLM Analyze" button on pipeline
- [ ] See progress modal with SSE updates
- [ ] Navigate to review strategy page automatically
- [ ] See recommended tools with reasoning
- [ ] Can modify tool selections
- [ ] Click "Approve Strategy"
- [ ] Execution runs in background
- [ ] Navigate to results page
- [ ] See cross-document insights
- [ ] Download PROV-O JSON
- [ ] Check database has complete record

---

## Decision Matrix

| Criteria | System 1 (Build On) | System 2 (Remove) | Start Fresh |
|----------|---------------------|-------------------|-------------|
| **Completion** | 70% ✅ | 20% ❌ | 0% ❌ |
| **Effort** | 8-10 hrs ✅ | N/A | 14-18 hrs ❌ |
| **LangGraph** | Yes ✅ | No ❌ | Would need ✅ |
| **Paper Alignment** | Yes ✅ | No ❌ | Yes ✅ |
| **Claude Integration** | Yes ✅ | Simulated ❌ | Would need ✅ |
| **5-Stage Workflow** | Yes ✅ | No ❌ | Would need ✅ |
| **SSE Progress** | Yes ✅ | No ❌ | Would need ✅ |
| **Results Display** | Yes ✅ | Partial ⚠️ | Would need ✅ |

**Winner:** System 1 (Build On It) ✅

---

## Revised Implementation Plan

**Consolidation + Completion = 9-12 hours total**

### Week 1: Core Completion (6-8 hours)
1. Create review_strategy.html template
2. Implement approve_strategy endpoint
3. Connect execute_strategy_node to real tools
4. End-to-end testing

### Week 2: Cleanup & Polish (3-4 hours)
1. Deprecate System 2 components
2. Update all template links
3. Documentation
4. Final testing

---

## Recommendation

**BUILD ON SYSTEM 1 - It's 70% complete and well-architected!**

The missing pieces are:
1. Review strategy page template (3-4 hours)
2. Approval endpoint (2-3 hours)
3. Tool integration (2-3 hours)
4. Cleanup System 2 (1-2 hours)

**Total: 8-12 hours vs. 14-18 hours for fresh implementation**

Plus you get:
- ✅ Working LangGraph workflow
- ✅ Claude API integration
- ✅ SSE real-time progress
- ✅ Complete database schema
- ✅ Results visualization
- ✅ Frontend button already wired up!

---

## Next Steps

1. **Decision:** Approve building on System 1?
2. **If Yes:** Start with Task 1.1 (review_strategy.html template)
3. **Create** tracking document for 4 tasks
4. **Execute** consolidation plan

---

**RECOMMENDATION:** ✅ Build on System 1, complete missing 30%, deprecate System 2

