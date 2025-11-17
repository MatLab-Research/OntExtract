# OntExtract Baseline Metrics

**Date:** 2025-11-15
**Branch:** `claude/review-refactor-branch-014RqayMhxHX6uHbcfuSNZ2i`
**Purpose:** Establish baseline metrics before refactoring initiative

---

## Executive Summary

| Metric | Current Value | Target | Status |
|--------|--------------|---------|--------|
| Total Python Files | 103 | - | 📊 Baseline |
| Test Coverage | ~0% (deps missing) | 70%+ | 🔴 Critical |
| Average File Size | ~223 lines | <250 lines | 🟡 Moderate |
| Largest File | 2,239 lines | <500 lines | 🔴 Critical |
| Type Hint Coverage | ~40% files | 100% | 🔴 Poor |
| Logging Coverage | ~35% files | 100% | 🔴 Poor |
| Test Files | 6 | 50+ | 🔴 Critical |

---

## File Statistics

### Overall Counts
- **Total Python files**: 103
  - App package (`/app`): 69 files
  - Shared services (`/shared_services`): 21 files
  - Tests (`/tests`): 6 files
  - Config/Other: 7 files

### File Size Distribution

#### Top 30 Largest Files (app/ package)
```
2,239 lines - app/routes/experiments.py          ⚠️ CRITICAL - 4.5x over limit
1,071 lines - app/routes/processing.py           ⚠️ CRITICAL - 2.1x over limit
  863 lines - app/routes/references.py           ⚠️ HIGH - 1.7x over limit
  762 lines - app/routes/terms.py                ⚠️ HIGH - 1.5x over limit
  678 lines - app/models/orchestration_feedback.py ⚠️ HIGH - 1.4x over limit
  669 lines - app/routes/text_input.py           ⚠️ HIGH - 1.3x over limit
  634 lines - app/services/oed_enrichment_service.py ⚠️ HIGH - 1.3x over limit
  591 lines - app/models/semantic_drift.py       ⚠️ MODERATE - 1.2x over limit
  568 lines - app/services/integrated_langextract_service.py ⚠️ MODERATE
  547 lines - app/services/langextract_document_analyzer.py  ⚠️ MODERATE
  534 lines - app/routes/embeddings_api.py       ⚠️ MODERATE
  521 lines - app/routes/orchestration_feedback.py ⚠️ MODERATE
  512 lines - app/services/text_processing.py    ⚠️ MODERATE
  512 lines - app/services/oed_parser_final.py   ⚠️ MODERATE
  498 lines - app/models/orchestration_logs.py   🟡 OK
  485 lines - app/services/llm_orchestration_coordinator.py 🟡 OK
  485 lines - app/models/document.py             🟡 OK
  468 lines - app/services/pipeline_status.py    🟡 OK
  456 lines - app/services/term_analysis_service.py 🟡 OK
  449 lines - app/services/adaptive_orchestration_service.py 🟡 OK
  441 lines - app/services/prov_o_tracking_service.py 🟡 OK
  435 lines - app/services/period_aware_embedding_service.py 🟡 OK
  431 lines - app/services/llm_bridge_service.py 🟡 OK
  380 lines - app/services/oed_parser_langextract.py ✅ OK
  374 lines - app/services/reference_metadata_enricher.py ✅ OK
  366 lines - app/services/enhanced_document_processor.py ✅ OK
  356 lines - app/models/term.py                 ✅ OK
  337 lines - app/models/prov_o_models.py        ✅ OK
  322 lines - app/services/oed_parser.py         ✅ OK
```

**Legend:**
- 🔴 CRITICAL: >1000 lines (needs immediate splitting)
- ⚠️ HIGH: 500-1000 lines (should be split)
- 🟡 MODERATE: 400-499 lines (monitor)
- ✅ OK: <400 lines

#### Files Requiring Immediate Attention
1. **experiments.py** (2,239 lines) - Split into 5+ modules
2. **processing.py** (1,071 lines) - Split into 3-4 modules
3. **references.py** (863 lines) - Split into 3 modules
4. **terms.py** (762 lines) - Split into 2-3 modules

---

## Code Quality Metrics

### Type Hints
- **Files with type hints**: ~43 files (42% of codebase)
- **Files without type hints**: ~60 files (58%)
- **Target**: 100% coverage on public interfaces

**Assessment**: 🔴 POOR - Needs significant improvement

### Documentation (Docstrings)
- **Estimated docstring coverage**: ~70%
- **Files with comprehensive docs**: Good coverage on services
- **Areas needing improvement**: Routes, utilities, some models

**Assessment**: 🟢 GOOD - Maintain and improve

### Logging
- **Files with logging**: ~38 files (37%)
- **Files without logging**: ~65 files (63%)
- **Logging patterns**: Inconsistent usage

**Assessment**: 🔴 POOR - Need comprehensive logging strategy

### Error Handling
- **Try/except blocks**: ~278 across 46 files
- **Proper error logging**: Sparse (~30% of error handlers)
- **Custom exceptions**: None (using generic Exception)

**Assessment**: 🟡 MODERATE - Needs structured approach

---

## Testing Metrics

### Current State
- **Test files**: 6
- **Tests per module ratio**: ~1:17 (1 test for every 17 modules)
- **Test coverage**: Unable to measure (pytest-cov not installed)
- **Test categories**:
  - Integration tests: 4
  - Unit tests: 2
  - E2E tests: 0

**Assessment**: 🔴 CRITICAL - Severely lacking

### Test Distribution
```
tests/test_historical_pipeline.py
tests/test_document_methods_api.py
tests/test_llm_config.py
tests/test_oed_multiple_terms.py
tests/test_unified_upload.py
tests/test_zotero_integration.py
```

### Missing Test Coverage
- ❌ No tests for routes (0/15 blueprints)
- ❌ No tests for most services (2/27 tested)
- ❌ No tests for models (0/18 tested)
- ❌ No tests for utilities
- ❌ No fixture infrastructure (factory-boy)

---

## Complexity Metrics

### Code Complexity (Estimated)
Based on manual analysis:

- **Cyclomatic complexity**: High in route files (experiments.py likely >50)
- **Functions with high complexity (>10)**: ~15-20 estimated
- **Deeply nested code**: Present in processing pipelines
- **Long functions (>50 lines)**: ~40+ functions

**Note**: Run `radon cc -a -nc app/` after installing dev dependencies for detailed metrics

---

## Dependency Analysis

### Production Dependencies
- **Total packages**: 69 (from requirements.txt)
- **Security vulnerabilities**: Not yet scanned
- **Outdated packages**: Not yet checked

### Development Dependencies
- **Status**: Newly defined in requirements-dev.txt
- **Coverage tools**: pytest-cov, coverage
- **Linting tools**: ruff, mypy, bandit
- **Testing tools**: pytest, factory-boy, faker

---

## Architecture Metrics

### Modules by Layer

**Models** (18 files):
- Average size: ~350 lines
- Largest: orchestration_feedback.py (678 lines)
- Concerns: Some models are too large

**Routes** (15 files):
- Average size: ~400 lines
- Largest: experiments.py (2,239 lines)
- Concerns: **CRITICAL** - Business logic in routes

**Services** (27 files):
- Average size: ~380 lines
- Largest: oed_enrichment_service.py (634 lines)
- Concerns: No repository pattern, direct DB access

**Utilities** (~8 files):
- Generally well-sized
- Concerns: Could use more helper utilities

---

## Security Baseline

### Secrets Detection
- ✅ No hardcoded secrets found (manual inspection)
- ✅ API keys properly loaded from environment
- ✅ Passwords hashed with bcrypt
- ❌ No automated secret scanning yet (will add with pre-commit)

### Security Issues
- ❌ No rate limiting
- ❌ No CSRF protection on API endpoints
- ⚠️ Input validation could be stronger
- ⚠️ No security headers (Talisman not configured)

---

## Performance Baseline

### Database Queries
- **N+1 queries**: Likely present (no eager loading detected)
- **Indexes**: Need audit
- **Query optimization**: Not measured

### API Performance
- **Response times**: Not measured (need profiling)
- **Caching**: Redis configured but usage unclear
- **Database connection pooling**: Configured (pool_size not tuned)

---

## Refactoring Priority Matrix

### Immediate (Week 1-3)
1. 🔴 Split experiments.py (2,239 → ~400 lines each, 5+ files)
2. 🔴 Split processing.py (1,071 → ~300 lines each, 3-4 files)
3. 🔴 Split references.py (863 → ~300 lines each, 3 files)
4. 🔴 Add comprehensive test suite (6 → 50+ tests, 70% coverage)

### High Priority (Week 4-6)
5. ⚠️ Implement repository pattern (remove DB logic from routes)
6. ⚠️ Add type hints (42% → 100%)
7. ⚠️ Add logging infrastructure (37% → 100%)
8. ⚠️ Create custom exception classes

### Medium Priority (Week 7-12)
9. 🟡 Add dependency injection
10. 🟡 Implement API documentation (OpenAPI/Swagger)
11. 🟡 Add performance monitoring
12. 🟡 Optimize database queries

### Low Priority (Week 13-16)
13. 🟢 Modernize Python syntax (3.10+ features)
14. 🟢 Add caching layer
15. 🟢 Security hardening (rate limiting, CSRF)
16. 🟢 Containerization (Docker)

---

## Success Criteria

### Phase 0 Completion (This Phase) ✅
- [x] pyproject.toml created
- [x] pre-commit hooks configured
- [x] Development dependencies defined
- [x] Baseline metrics documented
- [ ] CONTRIBUTING.md created
- [ ] GitHub workflows configured

### Phase 1 Targets (File Decomposition)
- [ ] No files >500 lines
- [ ] experiments.py split into 5+ modules
- [ ] processing.py split into 3+ modules
- [ ] All new modules have tests

### Phase 2 Targets (Repository Pattern)
- [ ] No `db.session` calls in routes
- [ ] All models have repository classes
- [ ] Services use repositories exclusively

### Phase 3 Targets (Testing)
- [ ] 70%+ code coverage
- [ ] All routes have integration tests
- [ ] All services have unit tests
- [ ] Factory fixtures for all models

### Final Targets (End of Refactor)
- [ ] 100% type hints on public interfaces
- [ ] 100% files with logging
- [ ] 80%+ test coverage
- [ ] Average file size <250 lines
- [ ] All complexity metrics in "good" range

---

## Tools for Ongoing Measurement

### After Installing Dev Dependencies

**Coverage Report**:
```bash
pytest --cov=app --cov=shared_services --cov-report=html --cov-report=term-missing
```

**Complexity Analysis**:
```bash
radon cc -a -nc app/
radon mi -s app/
```

**Type Checking**:
```bash
mypy app/ shared_services/
```

**Security Scan**:
```bash
bandit -r app/ shared_services/
safety check
```

**Code Quality**:
```bash
ruff check app/ shared_services/
```

---

## Next Steps

1. ✅ Complete Phase 0 (CONTRIBUTING.md, PR template, CI workflow)
2. 🔜 Install dev dependencies: `pip install -r requirements-dev.txt`
3. 🔜 Set up pre-commit: `pre-commit install`
4. 🔜 Begin Phase 1: File decomposition starting with experiments.py
5. 🔜 Run full metrics after Phase 1 completion to track progress

---

## Notes

- This baseline was established before major refactoring work
- Dependencies are not installed, so some metrics are estimates
- Coverage numbers will be measured once pytest-cov is installed
- Complexity metrics will be run after radon is installed
- This document should be updated at the end of each phase

---

**Measurement Frequency**:
- After each phase completion
- Weekly during active refactoring
- On demand using commands above
