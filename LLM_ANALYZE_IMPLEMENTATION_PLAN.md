# LLM Analyze Feature - Implementation Plan

**Created:** 2025-11-20
**Status:** PLANNING
**Priority:** HIGH
**Paper Reference:** OntExtract_Short_Paper__CR_.pdf

---

## Executive Summary

Implement the "LLM Analyze" button on the document pipeline page (http://localhost:8765/experiments/65/document_pipeline) to execute the complete 5-stage LangGraph orchestration workflow described in the JCDL paper.

This feature will transform the current manual processing workflow into an intelligent, LLM-orchestrated analysis system that:
1. Analyzes experiment goals and document characteristics
2. Recommends optimal processing tools per document
3. Provides human review interface for approval/modification
4. Executes approved strategy across all documents
5. Synthesizes cross-document insights with PROV-O tracking

---

## System Architecture Overview (from Paper)

### Current State
- ✅ **Infrastructure Exists**: LangGraph workflow, state management, nodes
- ✅ **Database Schema**: ExperimentOrchestrationRun model
- ✅ **PROV-O Tracking**: Provenance models and services
- ✅ **Tool Registry**: NLP tools (spaCy, NLTK, sentence-transformers)
- ❌ **Integration Missing**: Frontend button → Backend orchestration → Results display

### 5-Stage Workflow (from Paper, Section II.B)

```
┌──────────────────────────────────────────────────────────────┐
│  START → Analyze → Recommend → Review → Execute → Synthesize │
│           (1)        (2)         (3)      (4)        (5)      │
└──────────────────────────────────────────────────────────────┘

Stage 1: ANALYZE EXPERIMENT
- Input: Experiment goals, documents, focus term
- LLM analyzes: "What is this experiment trying to discover?"
- Output: experiment_goal, term_context

Stage 2: RECOMMEND STRATEGY
- Input: Experiment goal, document characteristics
- LLM recommends: Tools per document with reasoning & confidence
- Output: recommended_strategy {doc_id: [tools]}, confidence (0.0-1.0)

Stage 3: HUMAN REVIEW (Optional)
- User sees: Recommended tools, reasoning, confidence scores
- User can: Approve, modify tool selections, add notes
- Output: strategy_approved, modified_strategy, review_notes

Stage 4: EXECUTE STRATEGY
- Process all documents in parallel using approved tools
- Track execution provenance (PROV-O compliant)
- Output: processing_results {doc_id: {tool: result}}

Stage 5: SYNTHESIZE EXPERIMENT
- Cross-document analysis and insights
- For term evolution: Semantic shift patterns across corpus
- Output: cross_document_insights, term_evolution_analysis
```

---

## Existing Infrastructure

### ✅ Already Implemented

1. **LangGraph Workflow** (`app/orchestration/`)
   - `experiment_graph.py` - Graph structure with conditional branching
   - `experiment_nodes.py` - All 5 stage nodes implemented
   - `experiment_state.py` - TypedDict state management

2. **Database Models**
   - `ExperimentOrchestrationRun` - Stores workflow state
   - `OrchestrationDecision` - Individual tool selection decisions
   - `OrchestrationFeedback` - User feedback tracking
   - `LearningPattern` - Adaptive learning from user choices

3. **Services**
   - `OrchestrationService` - Business logic layer
   - PROV-O tracking infrastructure
   - Tool registry with descriptions

4. **Routes** (`app/routes/experiments/orchestration.py`)
   - Partial implementation, needs completion

### ❌ Missing Components

1. **Frontend Integration**
   - Button click handler on pipeline page
   - Real-time progress tracking UI
   - Strategy review modal with tool selection interface
   - Results visualization

2. **Backend API Endpoints**
   - `POST /orchestration/analyze-experiment/<experiment_id>`
   - `POST /orchestration/approve-strategy/<run_id>`
   - `GET /orchestration/status/<run_id>` (polling)
   - `GET /orchestration/results/<run_id>`

3. **Workflow Execution**
   - Async task runner for LangGraph execution
   - Progress broadcasting (SSE or WebSocket)
   - Error handling and retry logic
   - PROV-O provenance capture

4. **UI Components**
   - Progress modal with stage indicators
   - Strategy review interface
   - Results display with insights visualization
   - Confidence score indicators

---

## Implementation Phases

### Phase 1: Backend API Foundation (3-4 hours)

**Goal:** Create API endpoints to trigger and monitor orchestration

#### Tasks:

1. **Create Orchestration Execution Route**
   - File: `app/routes/experiments/orchestration.py`
   - Add: `POST /experiments/<id>/orchestration/analyze`
   - Logic:
     1. Create `ExperimentOrchestrationRun` record (status='analyzing')
     2. Initialize LangGraph with experiment data
     3. Execute Stages 1-2 (analyze + recommend)
     4. Save recommendations to database
     5. Return run_id + recommended strategy

2. **Create Status Polling Endpoint**
   - Add: `GET /orchestration/status/<run_id>`
   - Returns: Current stage, progress %, status, errors

3. **Create Approval Endpoint**
   - Add: `POST /orchestration/approve-strategy/<run_id>`
   - Input: strategy_approved, modified_strategy, review_notes
   - Logic:
     1. Update ExperimentOrchestrationRun
     2. Execute Stages 4-5 (execute + synthesize)
     3. Save results and insights

4. **Create Results Endpoint**
   - Add: `GET /experiments/<id>/orchestration/results/<run_id>`
   - Returns: Full results with cross-document insights

#### Files to Modify:
- `app/routes/experiments/orchestration.py` - Add 4 new endpoints
- `app/services/orchestration_service.py` - Add execution logic

#### Success Criteria:
- [ ] Can trigger orchestration via POST
- [ ] Can poll status during execution
- [ ] Can approve/modify strategy
- [ ] Can retrieve results with insights

---

### Phase 2: LangGraph Integration (4-5 hours)

**Goal:** Wire up existing LangGraph nodes to database and services

#### Tasks:

1. **Workflow Executor Service**
   - File: `app/services/workflow_executor.py` (NEW)
   - Class: `WorkflowExecutor`
   - Methods:
     - `execute_recommendation_phase(run_id)` - Runs Stages 1-2
     - `execute_processing_phase(run_id)` - Runs Stages 4-5
     - `_update_run_status(run_id, stage, data)` - Updates database
     - `_build_graph_state(experiment)` - Prepares input state

2. **Document Preparation**
   - Extract documents from experiment
   - Build document list with metadata:
     ```python
     {
       'id': doc.id,
       'uuid': doc.uuid,
       'title': doc.title,
       'content': doc.content,
       'metadata': {
         'publication_year': ...,
         'discipline': ...,
       }
     }
     ```

3. **Tool Registry Integration**
   - File: `app/services/tool_registry.py` (if doesn't exist, create)
   - Map tool names to actual implementations
   - Tools from paper:
     - `segment_paragraph` → PipelineService._process_segmentation
     - `segment_sentence` → PipelineService._process_segmentation
     - `extract_entities` → PipelineService._process_entities
     - `extract_definitions` → PipelineService._process_definitions
     - `extract_temporal` → PipelineService._process_temporal
     - `generate_embeddings` → PipelineService._process_embeddings

4. **Results Storage**
   - Map tool execution results to `processing_results` JSONB
   - Format: `{doc_id: {tool_name: result_data}}`
   - Save to ExperimentOrchestrationRun.processing_results

5. **PROV-O Integration**
   - Capture execution trace during Stage 4
   - Store in ExperimentOrchestrationRun.execution_trace
   - Include: tool used, document processed, timestamp, status

#### Files to Create/Modify:
- `app/services/workflow_executor.py` (NEW)
- `app/services/tool_registry.py` (NEW or UPDATE)
- `app/orchestration/experiment_nodes.py` - Connect to real tools

#### Success Criteria:
- [ ] Can execute full 5-stage workflow
- [ ] Results stored in database correctly
- [ ] PROV-O trace captured
- [ ] Error handling works

---

### Phase 3: Frontend UI (5-6 hours)

**Goal:** Add button, progress modal, review interface, results display

#### Tasks:

1. **Add "LLM Analyze" Button to Pipeline**
   - File: `app/templates/experiments/document_pipeline.html`
   - Location: Near "Run All Tools" button
   - Styling: Primary button with robot icon
   - Click handler: `startLLMAnalysis(experimentId)`

2. **Create Progress Modal**
   - Template: `app/templates/experiments/llm_progress_modal.html`
   - Features:
     - 5-stage progress indicator
     - Current stage highlighting
     - Progress percentage bar
     - Status messages
     - Cancel button (optional)

   ```html
   Stages: [✓ Analyze] [⟳ Recommend] [ Review] [ Execute] [ Synthesize]
   Progress: ████████████░░░░░░░░ 40%
   Status: "Analyzing document characteristics..."
   ```

3. **Create Strategy Review Modal**
   - Template: `app/templates/experiments/strategy_review_modal.html`
   - Shows:
     - Recommended tools per document
     - Confidence score (0-100%)
     - LLM reasoning
     - Tool descriptions
     - Modify/approve buttons

   ```html
   Document: "Black's Law Dictionary 1910"
   Recommended Tools:
   ☑ Extract Entities (spaCy) - "Historical document with many proper nouns"
   ☑ Extract Definitions - "Legal dictionary format"
   ☐ Temporal Extraction (optional)

   Confidence: 92% ████████████████████░

   [Modify Strategy] [Approve & Continue]
   ```

4. **Create Results Display**
   - Template: `app/templates/experiments/llm_results.html`
   - Sections:
     - Processing Summary (23 operations in 3m 29s)
     - Cross-Document Insights (LLM synthesis)
     - Per-Document Results (expandable)
     - Term Evolution Analysis (if focus term)
     - PROV-O Download Link

5. **JavaScript Implementation**
   - File: `app/static/js/llm_orchestration.js` (NEW)
   - Functions:
     - `startLLMAnalysis(experimentId)` - Trigger workflow
     - `pollOrchestrationStatus(runId)` - Status updates (1s interval)
     - `showStrategyReview(strategy, reasoning, confidence)` - Display modal
     - `approveStrategy(runId, modifications)` - Submit approval
     - `showResults(runId)` - Navigate to results

#### Files to Create/Modify:
- `app/templates/experiments/document_pipeline.html` - Add button
- `app/templates/experiments/llm_progress_modal.html` (NEW)
- `app/templates/experiments/strategy_review_modal.html` (NEW)
- `app/templates/experiments/llm_results.html` (NEW)
- `app/static/js/llm_orchestration.js` (NEW)

#### Success Criteria:
- [ ] Button appears on pipeline page
- [ ] Clicking starts orchestration
- [ ] Progress modal shows real-time updates
- [ ] Review modal displays recommendations
- [ ] Results page shows synthesis

---

### Phase 4: Testing & Polish (2-3 hours)

#### Tasks:

1. **End-to-End Testing**
   - Create test experiment with 3-5 documents
   - Run full workflow with actual LLM
   - Verify all stages execute correctly
   - Check PROV-O provenance is complete

2. **Error Handling**
   - Test LLM API failures
   - Test tool execution errors
   - Test user cancellation
   - Add retry logic

3. **UI Polish**
   - Loading states
   - Error messages
   - Success confirmations
   - Responsive design

4. **Documentation**
   - Update PROGRESS.md
   - Add inline code comments
   - Create user guide section

#### Success Criteria:
- [ ] Full workflow tested
- [ ] All error cases handled
- [ ] UI polished and responsive
- [ ] Documentation updated

---

## API Specification

### 1. Start Orchestration

```http
POST /experiments/<experiment_id>/orchestration/analyze
Content-Type: application/json

{
  "user_preferences": {
    "review_choices": true,
    "auto_approve_high_confidence": false,
    "confidence_threshold": 0.85
  }
}
```

**Response:**
```json
{
  "success": true,
  "run_id": "uuid-here",
  "status": "analyzing",
  "current_stage": "analyzing",
  "message": "Orchestration started - analyzing experiment"
}
```

### 2. Poll Status

```http
GET /orchestration/status/<run_id>
```

**Response (Analyzing):**
```json
{
  "run_id": "uuid",
  "status": "analyzing",
  "current_stage": "analyzing",
  "progress_percentage": 20,
  "stage_completed": {
    "analyze_experiment": false,
    "recommend_strategy": false,
    "execute_strategy": false,
    "synthesize_experiment": false
  }
}
```

**Response (Waiting for Review):**
```json
{
  "run_id": "uuid",
  "status": "reviewing",
  "current_stage": "reviewing",
  "progress_percentage": 40,
  "recommended_strategy": {
    "217": ["extract_entities", "extract_definitions"],
    "218": ["extract_entities", "extract_temporal"],
    "219": ["segment_paragraph", "extract_entities"]
  },
  "strategy_reasoning": "Based on legal and historical documents...",
  "confidence": 0.92,
  "awaiting_user_approval": true
}
```

### 3. Approve Strategy

```http
POST /orchestration/approve-strategy/<run_id>
Content-Type: application/json

{
  "strategy_approved": true,
  "modified_strategy": {
    "217": ["extract_entities", "extract_definitions", "extract_temporal"]
  },
  "review_notes": "Added temporal extraction to first document"
}
```

**Response:**
```json
{
  "success": true,
  "status": "executing",
  "message": "Strategy approved - beginning execution"
}
```

### 4. Get Results

```http
GET /experiments/<experiment_id>/orchestration/results/<run_id>
```

**Returns:** HTML page with full results display

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│  FRONTEND (document_pipeline.html)                                  │
│  ┌───────────────┐                                                  │
│  │ [LLM Analyze] │ ← User clicks button                            │
│  └───────┬───────┘                                                  │
│          │                                                           │
│          ▼                                                           │
│  ┌───────────────────────┐                                          │
│  │ startLLMAnalysis()    │ ← JavaScript function                   │
│  │ - POST /orchestration/│                                          │
│  │   analyze             │                                          │
│  │ - Start polling       │                                          │
│  └───────┬───────────────┘                                          │
└──────────┼───────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  BACKEND (orchestration routes + services)                          │
│                                                                      │
│  POST /orchestration/analyze                                        │
│  ├─ Create ExperimentOrchestrationRun (status='analyzing')         │
│  ├─ Call WorkflowExecutor.execute_recommendation_phase()           │
│  └─ Return run_id                                                   │
│                                                                      │
│  WorkflowExecutor.execute_recommendation_phase()                    │
│  ├─ Build state from experiment + documents                         │
│  ├─ Execute LangGraph (Stages 1-2)                                  │
│  │   ├─ analyze_experiment_node → experiment_goal                   │
│  │   └─ recommend_strategy_node → recommended_strategy              │
│  ├─ Save to database (status='reviewing')                           │
│  └─ Return                                                           │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
           │
           │ (User approves strategy)
           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  POST /orchestration/approve-strategy                                │
│  ├─ Update OrchestrationRun with approval                           │
│  ├─ Call WorkflowExecutor.execute_processing_phase()               │
│  └─ Return success                                                   │
│                                                                      │
│  WorkflowExecutor.execute_processing_phase()                        │
│  ├─ Execute LangGraph (Stages 4-5)                                  │
│  │   ├─ execute_strategy_node → processing_results                  │
│  │   └─ synthesize_experiment_node → cross_document_insights        │
│  ├─ Save results + PROV-O trace to database                         │
│  └─ Update status='completed'                                       │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  FRONTEND - Results Display                                         │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │ Cross-Document Insights:                                        ││
│  │ • Conceptual continuity across domains                          ││
│  │ • Domain-specific semantic networks                             ││
│  │ • 1995 inflection point (human → computational)                 ││
│  │                                                                  ││
│  │ Processing Summary: 23 operations in 3m 29s                     ││
│  │                                                                  ││
│  │ [Download PROV-O JSON]                                          ││
│  └─────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

---

## Database Schema Changes

### No Schema Changes Needed!

The `ExperimentOrchestrationRun` model already has all required fields:

```python
# Stage 1-2 (Recommendation Phase)
experiment_goal: Text
term_context: String(200)
recommended_strategy: JSONB  # {doc_id: [tools]}
strategy_reasoning: Text
confidence: Float

# Stage 3 (Human Review)
strategy_approved: Boolean
modified_strategy: JSONB
review_notes: Text
reviewed_by: Integer (FK)
reviewed_at: DateTime

# Stage 4 (Execution)
processing_results: JSONB  # {doc_id: {tool: result}}
execution_trace: JSONB  # PROV-O

# Stage 5 (Synthesis)
cross_document_insights: Text
term_evolution_analysis: Text
comparative_summary: Text

# Status Tracking
status: String(50)  # analyzing, recommending, reviewing, executing, synthesizing, completed, failed
current_stage: String(50)
```

---

## Configuration

### Environment Variables

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-...  # Already configured
ORCHESTRATION_TIMEOUT_SECONDS=300  # 5 minutes max
ORCHESTRATION_POLL_INTERVAL_MS=1000  # Frontend polling
```

### LLM Settings

```python
# app/orchestration/experiment_nodes.py (already configured)
ChatAnthropic(
    model="claude-sonnet-4-20250514",
    temperature=0.2,  # Low for consistency
    max_tokens=4096
)
```

---

## Testing Plan

### Unit Tests

1. **Workflow Executor**
   - Test state building
   - Test stage execution
   - Test error handling

2. **API Endpoints**
   - Test start orchestration
   - Test status polling
   - Test approval flow
   - Test results retrieval

### Integration Tests

1. **Full Workflow**
   - Create experiment with 3 documents
   - Execute all 5 stages
   - Verify results stored correctly
   - Verify PROV-O trace complete

2. **User Modification**
   - Test modifying recommended strategy
   - Verify modified strategy used in execution

### Manual Testing Checklist

- [ ] Button appears on pipeline page
- [ ] Clicking button starts orchestration
- [ ] Progress modal shows correct stages
- [ ] Status polling updates in real-time
- [ ] Strategy review modal displays recommendations
- [ ] Can approve strategy and continue
- [ ] Can modify strategy before approval
- [ ] Execution completes successfully
- [ ] Results page shows cross-document insights
- [ ] PROV-O JSON downloads correctly
- [ ] Error states handled gracefully

---

## Timeline Estimate

| Phase | Tasks | Estimated Time |
|-------|-------|----------------|
| Phase 1: Backend API | 4 endpoints + service logic | 3-4 hours |
| Phase 2: LangGraph Integration | Workflow executor + tool registry | 4-5 hours |
| Phase 3: Frontend UI | Button + modals + results | 5-6 hours |
| Phase 4: Testing & Polish | E2E tests + error handling | 2-3 hours |
| **TOTAL** | | **14-18 hours** |

**Recommended Schedule:**
- Day 1: Phase 1 + start Phase 2 (6-8 hours)
- Day 2: Complete Phase 2 + Phase 3 (8-10 hours)
- Day 3: Phase 4 + buffer (2-4 hours)

---

## Risks & Mitigation

### Risk 1: LLM API Timeouts
**Mitigation:**
- Set reasonable timeouts (5 minutes)
- Add retry logic with exponential backoff
- Provide manual tool selection fallback

### Risk 2: Tool Execution Failures
**Mitigation:**
- Graceful error handling per tool
- Continue with other tools if one fails
- Display partial results

### Risk 3: Long Processing Times
**Mitigation:**
- Use async execution
- Real-time progress updates
- Allow background processing

### Risk 4: Complex State Management
**Mitigation:**
- Use ExperimentOrchestrationRun as single source of truth
- Atomic database updates
- Clear state transitions

---

## Success Metrics

### Functional
- [ ] All 5 stages execute successfully
- [ ] User can review and modify strategy
- [ ] Results display cross-document insights
- [ ] PROV-O provenance complete

### Performance
- [ ] Recommendation phase < 30 seconds (Stages 1-2)
- [ ] Execution phase < 5 minutes for 7 documents
- [ ] Frontend polling < 100ms overhead

### User Experience
- [ ] Clear progress indication
- [ ] Intuitive review interface
- [ ] Helpful error messages
- [ ] Results easy to understand

---

## References

1. **Paper:** OntExtract_Short_Paper__CR_.pdf
   - Section II.B: LLM Orchestration Mechanism (pages 2-3)
   - Figure 2: 5-stage workflow results (page 4)
   - Section II.F: Case Study - Agent Evolution (page 3-4)

2. **Existing Code:**
   - `app/orchestration/experiment_graph.py` - Workflow structure
   - `app/orchestration/experiment_nodes.py` - Stage implementations
   - `app/models/experiment_orchestration_run.py` - Database schema
   - `app/services/orchestration_service.py` - Service layer

3. **PROV-O Standard:**
   - W3C PROV-O: The PROV Ontology
   - Implemented in `app/models/provenance.py`

---

## Next Steps

1. **Review this plan** with user for approval
2. **Create tracking document** for implementation progress
3. **Begin Phase 1** - Backend API endpoints
4. **Test incrementally** after each phase

---

**STATUS:** ✅ Planning Complete - Ready for Implementation

