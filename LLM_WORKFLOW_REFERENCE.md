# LLM Workflow Reference

**Purpose:** Technical reference for the 5-stage LangGraph orchestration workflow
**Paper:** OntExtract JCDL 2025 Short Paper
**Status:** Implemented & Production Ready

---

## 5-Stage Workflow Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  START → Analyze → Recommend → Review → Execute → Synthesize │
│           (1)        (2)         (3)      (4)        (5)      │
└──────────────────────────────────────────────────────────────┘
```

### Stage 1: Analyze Experiment
**Node:** `analyze_experiment_node()` in `app/orchestration/experiment_nodes.py`

**Input:**
- Experiment configuration (name, description, type, focus term)
- Document list (titles, filenames, content previews)

**LLM Prompt:**
- "Analyze this experiment..."
- Understand research goals
- Identify key terminology

**Output:**
- `experiment_goal` - What the experiment aims to discover
- `term_context` - Semantic understanding of focus term

### Stage 2: Recommend Strategy
**Node:** `recommend_strategy_node()`

**Input:**
- experiment_goal, term_context (from Stage 1)
- Available tools list (from NLP_TOOLS registry)
- Document summaries

**LLM Prompt:**
- "Based on this goal, recommend processing tools..."
- Consider document characteristics
- Match tools to research objectives

**Output:**
- `recommended_strategy` - Dict mapping document IDs to tool lists
  ```python
  {
    "1": ["extract_entities_spacy", "extract_temporal"],
    "2": ["extract_entities_spacy", "llm_text_cleanup"]
  }
  ```
- `strategy_reasoning` - Explanation of choices
- `confidence` - 0.0 to 1.0 confidence score

### Stage 3: Review Strategy (Human-in-the-Loop)
**Node:** `review_node()` - Conditional branching

**Execution:**
- Workflow pauses
- Frontend displays strategy in modal
- User can:
  - Approve as-is
  - Modify tool selections
  - Add review notes

**Branching:**
- `should_execute()` - Returns True if approved
- `should_end()` - Returns True if rejected

### Stage 4: Execute Strategy
**Node:** `execute_tools_node()`

**Input:**
- Approved strategy (original or modified)
- Document list

**Execution:**
- For each document, run assigned tools sequentially
- Tools from `app/services/nlp_tools.py`
- Progress tracking via `processing_results`

**Output:**
- `processing_results` - Dict of results per document/tool
  ```python
  {
    "1": {
      "extract_entities_spacy": {"count": 42, "entities": [...]},
      "extract_temporal": {"count": 5, "dates": [...]}
    }
  }
  ```

### Stage 5: Synthesize Insights
**Node:** `synthesize_node()`

**Input:**
- All processing results
- Original experiment goal
- PROV-O tracking data

**LLM Prompt:**
- "Synthesize cross-document insights..."
- Identify patterns and trends
- Connect to research goal

**Output:**
- `cross_document_insights` - Markdown-formatted analysis
- `term_evolution_analysis` - Focus term usage patterns
- PROV-O provenance graph

---

## State Management

### State Schema (`app/orchestration/experiment_state.py`)

```python
class ExperimentWorkflowState(TypedDict):
    # Core identifiers
    experiment_id: int
    run_id: str
    documents: List[DocumentInfo]

    # Configuration
    nlp_tools_registry: Dict[str, Any]
    available_tools: List[str]
    review_choices: bool

    # Progressive outputs (all Optional!)
    experiment_goal: Optional[str]
    term_context: Optional[str]
    recommended_strategy: Optional[Dict[str, List[str]]]
    strategy_reasoning: Optional[str]
    confidence: Optional[float]

    # User review
    strategy_approved: Optional[bool]
    review_notes: Optional[str]
    modified_strategy: Optional[Dict[str, List[str]]]

    # Execution results
    processing_results: Optional[Dict[str, Dict[str, Any]]]
    cross_document_insights: Optional[str]
    term_evolution_analysis: Optional[str]

    # Provenance
    provenance_graph: Optional[Dict]
    execution_trace: Optional[List[Dict]]
```

### Critical Patterns

**✅ DO:**
- Initialize Optional fields to `None`
- Use `state.update()` to merge node results
- Preserve critical keys (documents, experiment_id, run_id)

**❌ DON'T:**
- Initialize Optional fields to empty strings/dicts
- Replace entire state (loses keys)
- Use `operator.add` with Optional fields

---

## Database Persistence

### ExperimentOrchestrationRun Model

```python
class ExperimentOrchestrationRun(db.Model):
    id = UUID (primary key)
    experiment_id = Integer (FK to experiments)
    user_id = Integer (FK to users)

    # Status tracking
    status = String  # analyzing, reviewing, executing, completed, failed
    current_stage = String  # analyze, recommend, review, execute, synthesize

    # Stage 1 outputs
    experiment_goal = Text
    term_context = Text

    # Stage 2 outputs
    recommended_strategy = JSONB
    strategy_reasoning = Text
    confidence = Float

    # Stage 3 inputs
    strategy_approved = Boolean
    review_notes = Text
    modified_strategy = JSONB

    # Stage 4 outputs
    processing_results = JSONB

    # Stage 5 outputs
    cross_document_insights = Text
    term_evolution_analysis = Text

    # Metadata
    execution_trace = JSONB
    error_message = Text
    created_at, started_at, completed_at = DateTime
```

---

## Tool Registry

**Location:** `app/services/nlp_tools.py`

**Available Tools:**
```python
NLP_TOOLS = {
    'extract_entities_spacy': {
        'name': 'SpaCy Named Entity Recognition',
        'description': 'Extract named entities...',
        'function': extract_entities_spacy,
        'output_type': 'entities'
    },
    'extract_temporal': {
        'name': 'Temporal Expression Extraction',
        'description': 'Extract dates, times...',
        'function': extract_temporal_expressions,
        'output_type': 'temporal'
    },
    # ... 8 total tools
}
```

---

## Error Handling

**Configuration:** `app/orchestration/config.py`
- LLM_TIMEOUT_SECONDS = 300 (5 minutes)
- LLM_MAX_RETRIES = 3
- Retry delay: 2s → 4s → 8s (exponential backoff)

**Retry Logic:** `app/orchestration/retry_utils.py`
- Automatic retry on: 429, 500-504 errors
- No retry on: 400, 401, 403 errors
- Comprehensive logging

**Frontend Detection:**
- Timeout errors → Show retry button
- Rate limit errors → Show retry button
- Server errors → Show retry button
- LLM errors → No retry button

---

## PROV-O Provenance

**Standard:** W3C PROV-O (Provenance Ontology)

**Tracked Entities:**
- Agent: User who initiated orchestration
- Activity: Each processing step
- Entity: Documents and their transformations
- Derivation: Which results came from which inputs

**Download:** `/experiments/<id>/orchestration/llm-provenance/<run_id>` → JSON-LD

---

**See Also:**
- [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - Running the app, API endpoints
- [PROGRESS.md](PROGRESS.md) - Session history and current status
