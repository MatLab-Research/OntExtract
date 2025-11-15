# Experiments.py Split Plan - Detailed Analysis

**File:** `app/routes/experiments.py`
**Current Size:** 2,239 lines
**Target:** 5-6 modules (~300-450 lines each)
**Analysis Date:** 2025-11-15
**Session:** Phase 1a, Session 1

---

## Executive Summary

The `experiments.py` file contains **32 route endpoints** organized into **6 distinct functional areas**. This document provides a detailed plan for splitting this monolithic file into maintainable, focused modules.

### Recommended Structure

```
app/routes/experiments/
├── __init__.py              # Blueprint registration & imports (50 lines)
├── crud.py                  # Basic CRUD operations (350 lines)
├── terms.py                 # Term management (280 lines)
├── temporal.py              # Temporal term analysis (460 lines)
├── evolution.py             # Semantic evolution analysis (240 lines)
├── orchestration.py         # LLM orchestrated analysis (200 lines)
└── pipeline.py              # Document processing pipeline (600 lines)
```

**Total after split:** ~2,180 lines (distributed across 7 files)
**Largest module:** pipeline.py (600 lines) - still acceptable, focused on one concern

---

## Current Structure Analysis

### Route Distribution by Function

| Category | Routes | Lines | % of File |
|----------|--------|-------|-----------|
| CRUD Operations | 13 routes | ~355 lines | 16% |
| Term Management | 4 routes | ~280 lines | 13% |
| Temporal Terms | 4 routes | ~465 lines | 21% |
| Semantic Evolution | 2 routes | ~240 lines | 11% |
| Orchestration | 3 routes | ~200 lines | 9% |
| Document Pipeline | 6 routes | ~600 lines | 27% |
| **Overhead** | - | ~99 lines | 4% |

**Total:** 32 routes, 2,239 lines

---

## Detailed Module Breakdown

### Module 1: `crud.py` (CRUD Operations)

**Line Range:** 19-375 (approximately)
**Estimated Size:** ~350 lines
**Routes:** 13

#### Routes to Include

| Line | Route | Method | Purpose |
|------|-------|--------|---------|
| 19 | `/` | GET | List all experiments |
| 25 | `/new` | GET | New experiment form |
| 33 | `/wizard` | GET | Experiment creation wizard |
| 40 | `/create` | POST | Create experiment |
| 99 | `/sample` | POST/GET | Create sample experiment |
| 143 | `/<id>` | GET | View experiment details |
| 149 | `/<id>/edit` | GET | Edit experiment form |
| 171 | `/<id>/update` | POST | Update experiment |
| 217 | `/<id>/delete` | POST | Delete experiment |
| 282 | `/<id>/run` | POST | Run experiment |
| 334 | `/<id>/results` | GET | View experiment results |
| 363 | `/api/list` | GET | API: List experiments |
| 371 | `/api/<id>` | GET | API: Get experiment |

#### Functionality

- **Create** experiments (new, wizard, create, sample)
- **Read** experiments (index, view, api_list, api_get)
- **Update** experiments (edit, update)
- **Delete** experiments (delete)
- **Execute** experiments (run)
- **View results** (results)

#### Dependencies

```python
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import current_user
from app.utils.auth_decorators import require_login_for_write, api_require_login_for_write
from app import db
from app.models import Document, Experiment, ExperimentDocument
from datetime import datetime
import json
from typing import Optional
```

#### Key Patterns

- Standard CRUD operations
- JSON API endpoints
- Form rendering for UI
- Authentication decorators
- Database session management

---

### Module 2: `terms.py` (Term Management)

**Line Range:** 377-530 (approximately)
**Estimated Size:** ~280 lines
**Routes:** 4

#### Routes to Include

| Line | Route | Method | Purpose |
|------|-------|--------|---------|
| 377 | `/<id>/manage_terms` | GET | Term management UI |
| 402 | `/<id>/update_terms` | POST | Update terms/domains |
| 430 | `/<id>/get_terms` | GET | Get saved terms |
| 449 | `/<id>/fetch_definitions` | POST | Fetch term definitions |

#### Functionality

- Manage target terms for domain comparison experiments
- Define domains (e.g., Computer Science, Philosophy, Law)
- Fetch definitions from references and ontologies
- Store term definitions in experiment configuration

#### Dependencies

```python
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import current_user
from app.utils.auth_decorators import api_require_login_for_write
from app import db
from app.models import Experiment
from datetime import datetime
import json
from typing import Dict, List
```

#### Key Patterns

- Configuration-based storage (JSON)
- Domain-specific functionality (domain_comparison experiments)
- External data fetching (ontologies, references)

---

### Module 3: `temporal.py` (Temporal Term Management)

**Line Range:** 532-995 (approximately)
**Estimated Size:** ~460 lines
**Routes:** 4

#### Routes to Include

| Line | Route | Method | Purpose |
|------|-------|--------|---------|
| 532 | `/<id>/manage_temporal_terms` | GET | Temporal term management UI |
| 671 | `/<id>/update_temporal_terms` | POST | Update temporal terms |
| 699 | `/<id>/get_temporal_terms` | GET | Get temporal terms |
| 718 | `/<id>/fetch_temporal_data` | POST | Fetch temporal definitions |

#### Functionality

- Manage temporal terms (terms analyzed across time periods)
- Configure time periods for analysis
- Fetch temporal definitions from OED
- Store temporal configurations
- Complex term/period matrix management

#### Dependencies

```python
from flask import Blueprint, render_template, request, jsonify
from flask_login import current_user
from app.utils.auth_decorators import api_require_login_for_write
from app import db
from app.models import Experiment
from app.services.oed_enrichment_service import OEDEnrichmentService
from datetime import datetime
import json
from typing import Dict, List, Any
```

#### Key Patterns

- Period-based term analysis
- OED API integration
- Complex configuration management
- Time-series data handling

---

### Module 4: `evolution.py` (Semantic Evolution Analysis)

**Line Range:** 996-1235 (approximately)
**Estimated Size:** ~240 lines
**Routes:** 2

#### Routes to Include

| Line | Route | Method | Purpose |
|------|-------|--------|---------|
| 996 | `/<id>/semantic_evolution_visual` | GET | Evolution visualization UI |
| 1148 | `/<id>/analyze_evolution` | POST | Analyze semantic evolution |

#### Functionality

- Visualize semantic drift over time
- Analyze term evolution across periods
- Compare definitions from different time periods
- Generate evolution charts and metrics

#### Dependencies

```python
from flask import Blueprint, render_template, request, jsonify
from flask_login import current_user
from app import db
from app.models import Experiment
from app.services.term_analysis_service import TermAnalysisService
import json
from typing import Dict, List
```

#### Key Patterns

- Visualization data preparation
- Statistical analysis
- Time-series comparison
- Chart data generation

---

### Module 5: `orchestration.py` (LLM Orchestrated Analysis)

**Line Range:** 1236-1437 (approximately)
**Estimated Size:** ~200 lines
**Routes:** 3

#### Routes to Include

| Line | Route | Method | Purpose |
|------|-------|--------|---------|
| 1236 | `/<id>/orchestrated_analysis` | GET | Orchestration UI |
| 1266 | `/<id>/create_orchestration_decision` | POST | Create orchestration decision |
| 1358 | `/<id>/run_orchestrated_analysis` | POST | Run orchestrated analysis |

#### Functionality

- LLM-driven analysis workflows
- Dynamic analysis path selection
- Multi-step orchestrated operations
- Analysis decision tracking

#### Dependencies

```python
from flask import Blueprint, render_template, request, jsonify
from flask_login import current_user
from app import db
from app.models import Experiment
from app.services.llm_orchestration_coordinator import LLMOrchestrationCoordinator
from app.services.adaptive_orchestration_service import AdaptiveOrchestrationService
import json
from typing import Dict, Any
```

#### Key Patterns

- Service-driven workflows
- Complex multi-step processes
- Decision tracking and storage
- LLM integration

---

### Module 6: `pipeline.py` (Document Processing Pipeline)

**Line Range:** 1439-2239 (approximately)
**Estimated Size:** ~600 lines
**Routes:** 6

#### Routes to Include

| Line | Route | Method | Purpose |
|------|-------|--------|---------|
| 1439 | `/<id>/document_pipeline` | GET | Pipeline overview UI |
| 1493 | `/<id>/process_document/<doc_id>` | GET | Process single document |
| 1550 | `/<id>/document/<doc_id>/apply_embeddings` | POST | Apply embeddings |
| 1636 | `/api/experiment-processing/start` | POST | Start processing job |
| 2192 | `/api/experiment-document/<id>/processing-status` | GET | Get processing status |
| 2215 | `/api/processing/<uuid:id>/artifacts` | GET | Get processing artifacts |

#### Functionality

- Document processing workflow
- Embedding generation and application
- Processing status tracking
- Artifact management
- Multi-step document pipeline
- Progress monitoring

#### Dependencies

```python
from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import current_user
from sqlalchemy import text
from app import db
from app.models import Document, Experiment, ExperimentDocument
from app.models.experiment_processing import (
    ExperimentDocumentProcessing,
    ProcessingArtifact,
    DocumentProcessingIndex
)
from app.services.text_processing import TextProcessingService
from app.services.experiment_embedding_service import ExperimentEmbeddingService
from datetime import datetime
import json
import uuid
from typing import Dict, List, Any, Optional
```

#### Key Patterns

- Complex processing workflows
- Status tracking
- Progress calculation
- Artifact storage
- UUID-based processing IDs
- Raw SQL queries for performance

---

### Module 7: `__init__.py` (Blueprint Registration)

**Estimated Size:** ~50 lines

#### Purpose

- Register the experiments blueprint
- Import and register all sub-module routes
- Central configuration point

#### Structure

```python
"""
Experiments Blueprint

Handles all experiment-related routes across multiple modules:
- CRUD operations (create, read, update, delete)
- Term management
- Temporal analysis
- Semantic evolution
- LLM orchestration
- Document processing pipelines
"""

from flask import Blueprint

# Create the blueprint
experiments_bp = Blueprint('experiments', __name__, url_prefix='/experiments')

# Import route modules to register their routes
from . import crud
from . import terms
from . import temporal
from . import evolution
from . import orchestration
from . import pipeline

# All routes are registered via decorators in sub-modules
```

---

## Dependencies Analysis

### External Dependencies

All modules will need:
```python
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import current_user
from app import db
from app.models import Experiment
from app.utils.auth_decorators import require_login_for_write, api_require_login_for_write
```

### Module-Specific Dependencies

#### `crud.py`
```python
from app.models import Document, ExperimentDocument, ProcessingJob
```

#### `terms.py`
```python
# Lightweight - mostly config manipulation
```

#### `temporal.py`
```python
from app.services.oed_enrichment_service import OEDEnrichmentService
```

#### `evolution.py`
```python
from app.services.term_analysis_service import TermAnalysisService
```

#### `orchestration.py`
```python
from app.services.llm_orchestration_coordinator import LLMOrchestrationCoordinator
from app.services.adaptive_orchestration_service import AdaptiveOrchestrationService
```

#### `pipeline.py`
```python
from app.models.experiment_processing import (
    ExperimentDocumentProcessing,
    ProcessingArtifact,
    DocumentProcessingIndex
)
from app.services.text_processing import TextProcessingService
from app.services.experiment_embedding_service import ExperimentEmbeddingService
from sqlalchemy import text
import uuid
```

---

## Shared Utilities

### Helper Functions to Extract

Some functions are likely used across modules. These should be in a `helpers.py`:

```python
# app/routes/experiments/helpers.py

def get_experiment_or_404(experiment_id: int) -> Experiment:
    """Get experiment or raise 404."""
    return Experiment.query.filter_by(id=experiment_id).first_or_404()

def parse_experiment_config(experiment: Experiment) -> dict:
    """Parse and return experiment configuration."""
    return json.loads(experiment.configuration) if experiment.configuration else {}

def update_experiment_config(experiment: Experiment, updates: dict) -> None:
    """Update experiment configuration with new values."""
    config = parse_experiment_config(experiment)
    config.update(updates)
    experiment.configuration = json.dumps(config)
    experiment.updated_at = datetime.utcnow()

def check_experiment_not_running(experiment: Experiment) -> tuple[bool, str]:
    """Check if experiment is not running. Returns (can_modify, error_message)."""
    if experiment.status == 'running':
        return False, 'Cannot modify an experiment that is currently running'
    return True, ''
```

---

## Import Update Strategy

### Files That Import experiments_bp

Need to update:
```python
# OLD
from app.routes.experiments import experiments_bp

# NEW
from app.routes.experiments import experiments_bp  # Still works! No change needed
```

**Why no change needed:**
The `experiments/__init__.py` exports `experiments_bp`, so external imports remain unchanged!

### Internal Cross-References

Within experiments modules:
```python
# In evolution.py, if you need to reference a CRUD route
from flask import url_for

# This still works
url_for('experiments.view', experiment_id=123)

# Route names stay the same!
```

---

## Testing Strategy

### Test Organization

```
tests/
├── test_experiments_crud.py           # CRUD operations
├── test_experiments_terms.py          # Term management
├── test_experiments_temporal.py       # Temporal analysis
├── test_experiments_evolution.py      # Evolution analysis
├── test_experiments_orchestration.py  # Orchestration
└── test_experiments_pipeline.py       # Document pipeline
```

### Coverage Requirements

- **Per-module coverage:** 80%+
- **Critical paths:** 90%+
- **Integration tests:** Key workflows end-to-end

### Test Categories

1. **Unit Tests** - Individual route functions
2. **Integration Tests** - Database interactions
3. **E2E Tests** - Complete workflows (create → process → analyze)

---

## Migration Checklist

### Pre-Migration

- [x] Analysis complete
- [ ] Tests written for existing functionality
- [ ] Team review of split plan
- [ ] Backup branch created

### Migration Steps

1. **Create directory structure**
   ```bash
   mkdir -p app/routes/experiments
   touch app/routes/experiments/__init__.py
   ```

2. **Extract modules one at a time** (in order)
   - [ ] Create `crud.py` - extract lines 19-375
   - [ ] Create `terms.py` - extract lines 377-530
   - [ ] Create `temporal.py` - extract lines 532-995
   - [ ] Create `evolution.py` - extract lines 996-1235
   - [ ] Create `orchestration.py` - extract lines 1236-1437
   - [ ] Create `pipeline.py` - extract lines 1439-2239
   - [ ] Create `__init__.py` - blueprint registration

3. **After each module extraction:**
   - [ ] Run all tests
   - [ ] Verify app starts
   - [ ] Spot-check functionality
   - [ ] Commit working state

4. **Final cleanup**
   - [ ] Remove old `experiments.py`
   - [ ] Run full test suite
   - [ ] Update documentation
   - [ ] Create PR

### Post-Migration

- [ ] All tests passing
- [ ] Code review complete
- [ ] Performance validated (no regressions)
- [ ] Documentation updated

---

## Risk Assessment

### Low Risk ✅

- **Blueprint registration** - Well-defined pattern
- **Route naming** - Stays the same
- **External imports** - No changes needed

### Medium Risk ⚠️

- **Import cycles** - May occur if modules cross-reference
  - *Mitigation:* Use shared helpers.py
- **Template paths** - Need to verify all render_template() calls
  - *Mitigation:* Keep templates in same location

### High Risk 🔴

- **Database transactions** - Split across modules could cause issues
  - *Mitigation:* Keep transaction boundaries clear, test thoroughly
- **Shared state** - Any module-level variables could cause problems
  - *Mitigation:* Audit for global state before split

---

## Success Metrics

### Before Split

- **File size:** 2,239 lines
- **Routes:** 32 (all in one file)
- **Maintainability:** Low (cognitive load too high)
- **Test coverage:** Unknown (need to measure)

### After Split

- **Largest file:** <600 lines (pipeline.py)
- **Average file:** ~300 lines
- **Maintainability:** High (focused modules)
- **Test coverage:** 80%+ per module
- **Import complexity:** Low (clean module boundaries)

---

## Timeline Estimate

### Session-by-Session Plan

| Session | Duration | Task | Output |
|---------|----------|------|--------|
| 1 (This) | 1-2 hrs | Analysis & test writing | This document + tests |
| 2 | 1.5 hrs | Extract crud.py | Working CRUD module |
| 3 | 1 hr | Extract terms.py | Working terms module |
| 4 | 1 hr | Extract temporal.py | Working temporal module |
| 5 | 45 min | Extract evolution.py | Working evolution module |
| 6 | 45 min | Extract orchestration.py | Working orchestration module |
| 7 | 1.5 hrs | Extract pipeline.py | Working pipeline module |
| 8 | 1 hr | Create __init__.py & cleanup | Complete refactor |
| 9 | 1 hr | Final testing & docs | Ready for PR |

**Total:** ~10 hours across 9 sessions

---

## Next Steps

1. **Review this plan** - Get feedback on proposed structure
2. **Write tests** - Create test files for existing functionality
3. **Session 2** - Extract first module (crud.py)

---

## Notes

- **Line numbers are approximate** - Actual extraction will need careful verification
- **Some routes may span multiple logical areas** - Use best judgment
- **Helper functions** - May need to create shared utilities
- **Template paths** - Verify all remain correct after split
- **URL namespacing** - All routes keep `experiments.` prefix

---

**Document Status:** ✅ READY FOR REVIEW
**Next Action:** Write tests before beginning extraction
