# OntExtract Comprehensive Refactoring Plan (Updated)
**Created**: November 16, 2025
**Branch**: `claude/review-refactor-branch-014RqayMhxHX6uHbcfuSNZ2i`
**Status**: Phase 0 Complete ✅ | Phase 1a Complete ✅ | Phase 1b-5 Pending

---

## 🎯 Current State Summary

### ✅ Completed Work (Nov 15, 2025)

**Phase 0: Foundation & Tooling** - COMPLETE
- ✅ Created `pyproject.toml` with Ruff, MyPy, Pytest, Coverage, Bandit
- ✅ Set up pre-commit hooks (`.pre-commit-config.yaml`)
- ✅ Created `BASELINE_METRICS.md` documenting current state
- ✅ Created `CONTRIBUTING.md` with coding standards
- ✅ Set up CI/CD pipeline (`.github/workflows/ci.yml`)
- ✅ Created `requirements-dev.txt` for development dependencies

**Phase 1a: Split experiments.py** - COMPLETE
- ✅ **experiments.py** (2,239 lines) → **6 focused modules:**
  - `crud.py` - 405 lines (CRUD operations)
  - `terms.py` - 178 lines (Term management)
  - `temporal.py` - 515 lines (Temporal analysis)
  - `evolution.py` - 255 lines (Evolution analysis)
  - `orchestration.py` - 425 lines (Orchestration)
  - `pipeline.py` - 844 lines (Document pipeline)
- ✅ All routes working and properly registered
- ✅ Backward compatible imports maintained

### 🎯 Remaining Critical Issues

From `BASELINE_METRICS.md`, still need to address:

1. **Large Route Files**:
   - `processing.py` - 1,071 lines ⚠️ CRITICAL
   - `references.py` - 863 lines ⚠️ HIGH
   - `terms.py` - 762 lines ⚠️ HIGH
   - `text_input.py` - 669 lines ⚠️ HIGH

2. **Large Service Files**:
   - `oed_enrichment_service.py` - 634 lines ⚠️ HIGH
   - `integrated_langextract_service.py` - 568 lines ⚠️ MODERATE
   - `langextract_document_analyzer.py` - 547 lines ⚠️ MODERATE
   - `text_processing.py` - 512 lines ⚠️ MODERATE
   - `oed_parser_final.py` - 512 lines ⚠️ MODERATE

3. **Architectural Gaps**:
   - ❌ No task-specific LLM configuration
   - ❌ No repository pattern (direct DB access in routes)
   - ❌ Limited test coverage (~0%)
   - ❌ Business logic mixed with route handlers
   - ❌ Hardcoded model names in services
   - ❌ No service interfaces/protocols

---

## 📋 Comprehensive Refactoring Phases

### **Phase 1: File Decomposition** (IN PROGRESS - 25% Complete)

#### ✅ Phase 1a: Split experiments.py - COMPLETE
**Status**: ✅ Done
**Completion**: 100%

#### Phase 1b: Split processing.py
**Status**: ⏳ Not Started
**Target**: 1,071 lines → 4 focused modules
**Estimated Time**: 3-4 sessions (~5 hours)

**Target Structure**:
```
app/routes/processing/
├── __init__.py           # Blueprint registration
├── dashboard.py          # Dashboard views (~250 lines)
├── jobs.py               # Job management (~300 lines)
├── status.py             # Status endpoints (~270 lines)
└── batch.py              # Batch processing (~250 lines)
```

**Tasks**:
- [ ] Analyze processing.py structure and dependencies
- [ ] Extract dashboard views
- [ ] Extract job management routes
- [ ] Extract status endpoints
- [ ] Extract batch processing routes
- [ ] Update imports and test all routes

#### Phase 1c: Split references.py
**Status**: ⏳ Not Started
**Target**: 863 lines → 3 focused modules
**Estimated Time**: 3 sessions (~4 hours)

**Target Structure**:
```
app/routes/references/
├── __init__.py           # Blueprint registration
├── crud.py               # CRUD operations (~300 lines)
├── enrichment.py         # Metadata enrichment (~300 lines)
└── import_export.py      # Import/export functionality (~250 lines)
```

#### Phase 1d: Split terms.py
**Status**: ⏳ Not Started
**Target**: 762 lines → 2-3 focused modules
**Estimated Time**: 2-3 sessions (~3-4 hours)

**Target Structure**:
```
app/routes/terms/
├── __init__.py           # Blueprint registration
├── crud.py               # CRUD operations (~300 lines)
├── analysis.py           # Term analysis (~300 lines)
└── drift.py              # Semantic drift (~150 lines)
```

#### Phase 1e: Split text_input.py
**Status**: ⏳ Not Started
**Target**: 669 lines → 2 focused modules
**Estimated Time**: 2 sessions (~3 hours)

**Phase 1 Total Estimated Time**: 10-12 sessions (~15-17 hours)

---

### **Phase 2: Service Layer Refactoring & LLM Configuration**

#### Phase 2a: Task-Specific LLM Configuration
**Status**: ⏳ Not Started
**Priority**: HIGH (enables Phase 2b-2e)
**Estimated Time**: 1-2 sessions (~2-3 hours)

**Objective**: Create centralized, configurable LLM model selection

**Tasks**:
- [ ] Create `config/llm_config.py` with task-specific model configuration
- [ ] Add environment-based model selection:
  ```python
  LLM_EXTRACTION_MODEL = 'gemini-2.5-flash'        # Fast structured extraction
  LLM_SYNTHESIS_MODEL = 'claude-sonnet-4-5'        # Complex reasoning
  LLM_ORCHESTRATION_MODEL = 'gpt-5-mini'           # Fast routing
  LLM_OED_PARSING_MODEL = 'gemini-2.5-pro'         # Complex parsing
  LLM_LONG_CONTEXT_MODEL = 'claude-sonnet-4-5'     # 200k context
  LLM_CLASSIFICATION_MODEL = 'gemini-2.5-flash-lite' # Fast/cheap
  LLM_FALLBACK_MODEL = 'gpt-5.1'                   # Latest stable
  ```
- [ ] Create `LLMConfigManager` class with provider abstraction
- [ ] Add configuration validation with Pydantic
- [ ] Update existing services to use new configuration
- [ ] Add documentation for LLM configuration

**Deliverables**:
- `config/llm_config.py` - Configuration system
- Updated `config/__init__.py` - Integration
- `docs/LLM_CONFIGURATION.md` - Documentation

#### Phase 2b: Refactor langextract Services
**Status**: ⏳ Not Started
**Priority**: HIGH
**Estimated Time**: 2-3 sessions (~4-5 hours)

**Target Files**:
- `langextract_document_analyzer.py` (547 lines)
- `integrated_langextract_service.py` (568 lines)

**Target Structure**:
```
app/services/langextract/
├── __init__.py              # Package exports
├── analyzer.py              # Main coordinator (~150 lines)
├── extraction.py            # LangExtract operations (~250 lines)
├── text_preprocessing.py    # Text cleaning (~50 lines)
├── result_processing.py     # Result validation (~150 lines)
├── orchestration_summary.py # Guidance generation (~150 lines)
├── fallback.py              # Pattern-based fallback (~150 lines)
└── integrated_service.py    # Two-stage service (~200 lines)
```

**Benefits**:
- Single Responsibility Principle
- Easier testing (focused modules)
- Configurable model selection
- Clear separation of concerns

#### Phase 2c: Refactor OED Services
**Status**: ⏳ Not Started
**Priority**: MEDIUM
**Estimated Time**: 2-3 sessions (~4-5 hours)

**Target Files**:
- `oed_enrichment_service.py` (634 lines)
- `oed_parser_final.py` (512 lines)
- `oed_parser.py` (322 lines)
- `oed_api_client.py`, `oed_service.py`

**Target Structure**:
```
app/services/oed/
├── __init__.py           # Package exports
├── client.py             # API client (~200 lines)
├── parser.py             # Response parsing (~300 lines)
├── enrichment.py         # Data enrichment (~250 lines)
├── cache.py              # Caching layer (~150 lines)
└── types.py              # Type definitions (~50 lines)
```

#### Phase 2d: Refactor Text Processing Service
**Status**: ⏳ Not Started
**Priority**: MEDIUM
**Estimated Time**: 2 sessions (~3-4 hours)

**Target**: `text_processing.py` (512 lines)

**Target Structure**:
```
app/services/text_processing/
├── __init__.py           # Package exports
├── segmentation.py       # Text segmentation (~150 lines)
├── tokenization.py       # Tokenization (~100 lines)
├── cleaning.py           # Text cleaning (~100 lines)
├── analysis.py           # Text analysis (~150 lines)
└── utils.py              # Utilities (~50 lines)
```

#### Phase 2e: Refactor Orchestration Services
**Status**: ⏳ Not Started
**Priority**: MEDIUM
**Estimated Time**: 2-3 sessions (~4-5 hours)

**Target Files**:
- `llm_orchestration_coordinator.py` (485 lines)
- `adaptive_orchestration_service.py` (449 lines)
- `llm_bridge_service.py` (431 lines)

**Target Structure**:
```
app/services/orchestration/
├── __init__.py           # Package exports
├── coordinator.py        # Main coordinator (~200 lines)
├── adaptive.py           # Adaptive logic (~200 lines)
├── bridge.py             # LLM bridge (~200 lines)
├── feedback.py           # Feedback processing (~150 lines)
└── strategies.py         # Orchestration strategies (~150 lines)
```

**Phase 2 Total Estimated Time**: 10-14 sessions (~18-22 hours)

---

### **Phase 3: Business Logic Extraction**
**Status**: ⏳ Not Started
**Priority**: HIGH (after Phase 1 & 2)
**Estimated Time**: 8-10 sessions (~12-15 hours)

**Objective**: Move business logic from routes to services

**Current Issue**: Route handlers contain substantial business logic (database operations, complex processing, data transformations)

**Target Pattern**:
```python
# Before (in route):
@experiments_bp.route('/<id>/process', methods=['POST'])
def process(id):
    experiment = Experiment.query.get_or_404(id)
    # 50+ lines of business logic here
    db.session.commit()
    return jsonify(result)

# After (in route):
@experiments_bp.route('/<id>/process', methods=['POST'])
def process(id):
    data = ProcessRequestDTO(**request.get_json())
    result = experiment_service.process_experiment(id, data)
    return ProcessResponseDTO.from_result(result).json()

# Business logic moved to service:
# app/services/experiment_service.py
class ExperimentService:
    def process_experiment(self, id, data):
        # All business logic here
        pass
```

**Tasks**:
- [ ] Create service layer for experiments
- [ ] Create service layer for processing
- [ ] Create service layer for references
- [ ] Create service layer for terms
- [ ] Define Pydantic DTOs for request/response
- [ ] Extract all business logic to services
- [ ] Routes become thin controllers

**Benefits**:
- Testable business logic (no Flask context needed)
- Reusable logic across different interfaces (API, CLI, etc.)
- Clear separation of concerns
- Easier to add new interfaces

---

### **Phase 4: Repository Pattern**
**Status**: ⏳ Not Started
**Priority**: MEDIUM (after Phase 3)
**Estimated Time**: 6-8 sessions (~10-12 hours)

**Objective**: Centralize database access through repository pattern

**Current Issue**: Direct `db.session` and `Model.query` calls scattered throughout routes and services

**Target Structure**:
```
app/repositories/
├── __init__.py           # Repository exports
├── base.py               # BaseRepository[T]
├── document.py           # DocumentRepository
├── experiment.py         # ExperimentRepository
├── term.py               # TermRepository
├── user.py               # UserRepository
└── processing.py         # ProcessingRepository
```

**Example**:
```python
# app/repositories/base.py
class BaseRepository(Generic[T]):
    def __init__(self, model: Type[T]):
        self.model = model

    def find_by_id(self, id: int) -> Optional[T]:
        return db.session.get(self.model, id)

    def find_all(self) -> List[T]:
        return db.session.query(self.model).all()

    # ... more CRUD methods

# app/repositories/experiment.py
class ExperimentRepository(BaseRepository[Experiment]):
    def find_by_user(self, user_id: int) -> List[Experiment]:
        return self.model.query.filter_by(user_id=user_id).all()

    def find_with_documents(self, id: int) -> Optional[Experiment]:
        return self.model.query.options(
            joinedload(Experiment.documents)
        ).filter_by(id=id).first()
```

**Tasks**:
- [ ] Create `BaseRepository` with generic CRUD operations
- [ ] Implement repositories for each model
- [ ] Add complex query methods to repositories
- [ ] Update services to use repositories (no direct DB access)
- [ ] Add repository tests
- [ ] Remove all `db.session` and `Model.query` from routes

**Benefits**:
- Single place for all database queries
- Easy to mock for testing
- Database-agnostic business logic
- Query optimization in one place
- Clear data access patterns

---

### **Phase 5: Testing Infrastructure**
**Status**: ⏳ Not Started
**Priority**: HIGH (parallel with all phases)
**Estimated Time**: 10-12 sessions (~15-18 hours)

**Objective**: Achieve 75%+ test coverage with comprehensive tests

**Current State**: ~0% coverage (dependencies missing)

#### Phase 5a: Testing Foundation
**Tasks**:
- [ ] Install test dependencies (`pytest`, `pytest-cov`, `pytest-flask`, `factory-boy`)
- [ ] Create test fixtures (`conftest.py`)
- [ ] Set up test database configuration
- [ ] Create test factories for models
- [ ] Configure pytest with coverage reporting

#### Phase 5b: Unit Tests
**Target Coverage**: 80%+ for services and repositories

**Tasks**:
- [ ] Write tests for all service methods
- [ ] Write tests for all repository methods
- [ ] Write tests for utility functions
- [ ] Mock external dependencies (LLM calls, APIs)
- [ ] Test error handling and edge cases

#### Phase 5c: Integration Tests
**Target Coverage**: 70%+ for routes

**Tasks**:
- [ ] Write integration tests for all route endpoints
- [ ] Test database transactions
- [ ] Test authentication and authorization
- [ ] Test file uploads and processing
- [ ] Test experiment workflows end-to-end

#### Phase 5d: Test Utilities
**Tasks**:
- [ ] Create mock LLM response fixtures
- [ ] Create test data generators
- [ ] Add performance test helpers
- [ ] Create E2E test scenarios
- [ ] Add CI/CD test automation

**Coverage Goals**:
- **Services**: 80%+
- **Repositories**: 90%+
- **Routes**: 70%+
- **Overall**: 75%+

---

### **Phase 6: Advanced Features** (Optional/Future)
**Status**: ⏳ Not Started
**Priority**: LOW (after all core phases)

#### Phase 6a: Async Support
- [ ] Identify I/O-bound operations
- [ ] Implement async service methods for LLM calls
- [ ] Add async route handlers where beneficial
- [ ] Connection pooling for external APIs

#### Phase 6b: Caching Layer
- [ ] Redis integration
- [ ] LLM response caching
- [ ] Document processing result caching
- [ ] Semantic embedding caching

#### Phase 6c: Performance Monitoring
- [ ] Request timing middleware
- [ ] Slow query logging
- [ ] LLM call monitoring
- [ ] Performance dashboards

#### Phase 6d: API Versioning
- [ ] API versioning strategy
- [ ] OpenAPI/Swagger documentation
- [ ] Deprecation policy
- [ ] Migration guides

---

## 📊 Success Metrics

### Code Quality Targets

| Metric | Baseline | Current | Target | Status |
|--------|----------|---------|--------|--------|
| Largest file | 2,239 lines | ~844 lines | <500 lines | 🟡 In Progress |
| Files >500 lines | 14 files | ~8 files | 0 files | 🟡 In Progress |
| Test coverage | 0% | 0% | 75%+ | 🔴 Not Started |
| Type hints | 40% | 40% | 100% | 🔴 Not Started |
| Avg file size | 223 lines | ~215 lines | <250 lines | ✅ On Track |

### Architecture Quality Targets

- [ ] All routes are thin controllers (<100 lines each)
- [ ] All business logic in services
- [ ] All database access through repositories
- [ ] All services follow Single Responsibility Principle
- [ ] All public APIs have type hints
- [ ] Consistent error handling throughout
- [ ] Structured logging in all services
- [ ] Zero critical linting issues

---

## 🗓️ Estimated Timeline

### Conservative Estimate (Full-time equivalent)

| Phase | Estimated Duration | Sessions | Calendar Time (Part-time) |
|-------|-------------------|----------|--------------------------|
| Phase 0 | ✅ Complete | - | - |
| Phase 1a | ✅ Complete | - | - |
| Phase 1b-e | 10-12 sessions | 10-12 | 2-3 weeks |
| Phase 2 | 10-14 sessions | 10-14 | 2-3 weeks |
| Phase 3 | 8-10 sessions | 8-10 | 1.5-2 weeks |
| Phase 4 | 6-8 sessions | 6-8 | 1-2 weeks |
| Phase 5 | 10-12 sessions | 10-12 | 2-3 weeks |
| **Total** | **44-56 sessions** | **44-56** | **8-12 weeks** |

*Assumes 1-2 hour sessions, part-time work (4-6 hours/week)*

### Parallel Work Strategy

To reduce calendar time, some phases can run in parallel:
- **Phase 5** (Testing) can be done incrementally during Phases 2-4
- **Phase 2a** (LLM Config) can be done early to unblock service refactoring
- **Phase 1b-e** (File splitting) is independent of service refactoring

**Optimized Timeline**: 6-8 weeks with parallel work

---

## 🎯 Recommended Next Steps

Based on the current state and priorities:

### Option A: Continue File Decomposition (Lower Risk)
1. ✅ Complete Phase 1b: Split processing.py
2. Complete Phase 1c: Split references.py
3. Complete Phase 1d: Split terms.py
4. Then move to Phase 2

**Pros**: Lower risk, builds on proven pattern, immediate value
**Cons**: Doesn't address architectural issues yet

### Option B: Add LLM Configuration First (Higher Value)
1. ✅ Complete Phase 2a: LLM Configuration System
2. Complete Phase 2b: Refactor langextract services
3. Then return to Phase 1b-e

**Pros**: Enables modern patterns, higher architectural value, sets up Phase 2
**Cons**: Slightly riskier, requires more upfront design

### Option C: Hybrid Approach (Balanced)
1. ✅ Complete Phase 2a: LLM Configuration (1-2 sessions)
2. Complete Phase 1b: Split processing.py (3-4 sessions)
3. Complete Phase 2b: Refactor langextract (2-3 sessions)
4. Continue alternating between Phase 1 & Phase 2

**Pros**: Balances quick wins with architectural improvements
**Cons**: Context switching between different work types

---

## 💡 Recommendation

**Start with Option C (Hybrid Approach)**

**Immediate Next Actions**:
1. **Session 1-2**: Phase 2a - Add LLM Configuration System
   - High value, enables future work
   - Low risk, no breaking changes
   - ~2-3 hours

2. **Session 3-6**: Phase 1b - Split processing.py
   - Builds on proven pattern from Phase 1a
   - Immediate visible progress
   - ~5 hours

3. **Session 7-9**: Phase 2b - Refactor langextract services
   - Apply new LLM configuration
   - Establish service refactoring pattern
   - ~4-5 hours

This gives a good mix of architectural improvements (LLM config + service refactoring) and quick wins (file splitting), while building momentum and establishing patterns for future work.

---

## 📚 Reference Documents

- `REFACTORING_PROGRESS.md` - Detailed session-by-session progress tracker
- `BASELINE_METRICS.md` - Initial code quality measurements
- `PHASE_0_COMPLETE.md` - Phase 0 completion summary
- `EXPERIMENTS_SPLIT_PLAN.md` - Detailed plan for experiments.py split
- `CONTRIBUTING.md` - Coding standards and contribution guidelines
- `pyproject.toml` - Tool configuration (ruff, mypy, pytest, coverage)

---

**Next Review Date**: After completing next 3-5 sessions
**Last Updated**: November 16, 2025
