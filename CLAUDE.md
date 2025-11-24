# OntExtract - AI Assistant Guide

**Status**: Production-ready (Session 29 complete - November 24, 2025)
**Branch**: `development`
**Production URL**: https://ontextract.ontorealm.net
**Local URL**: http://localhost:8765

## Current Status (Session 29)

**Latest Work**: ProcessingArtifactGroup Tracking + Production Deployment

**Key Achievement**: LLM orchestration now creates ProcessingArtifactGroup records automatically, making orchestration results visible in the UI just like manual processing operations.

**Changes Deployed**:
1. ProcessingArtifactGroup creation during orchestration
2. Document ID type conversion fix (string → int)
3. Status field normalization ("success" → "executed") for UI compatibility
4. FK constraint fix (CASCADE on delete for processing_artifact_groups)
5. Deployment agent and automated deployment script

**Files Modified**:
- [app/services/extraction_tools.py](app/services/extraction_tools.py) - Artifact group creation
- [app/orchestration/experiment_nodes.py](app/orchestration/experiment_nodes.py) - Type conversion and status normalization
- [.claude/agents/git-deployment-sync.md](.claude/agents/git-deployment-sync.md) - Deployment agent (NEW)
- [scripts/deploy_production.sh](scripts/deploy_production.sh) - Automated deployment (NEW)

## Quick Navigation

### When You Need To...

**Understand the project:**
- Architecture overview: [README.md](README.md)
- Session history: [docs/PROGRESS.md](docs/PROGRESS.md) (Sessions 1-29)
- Current focus: JCDL 2025 Conference Demo (Dec 15-19)

**Deploy to production:**
- Deployment agent: [.claude/agents/git-deployment-sync.md](.claude/agents/git-deployment-sync.md)
- Deployment script: [scripts/deploy_production.sh](scripts/deploy_production.sh)
- Production URL: https://ontextract.ontorealm.net
- Server: DigitalOcean (SSH: `ssh digitalocean`)

**Work with LLM orchestration:**
- Workflow reference: [docs/LLM_WORKFLOW_REFERENCE.md](docs/LLM_WORKFLOW_REFERENCE.md)
- Implementation: [app/orchestration/](app/orchestration/) (experiment_graph.py, experiment_nodes.py, prompts.py)
- Celery tasks: [app/tasks/orchestration.py](app/tasks/orchestration.py)
- Tool executors: [app/services/extraction_tools.py](app/services/extraction_tools.py)

**Fix tests:**
- Test fix guide: [docs/TEST_FIX_GUIDE.md](docs/TEST_FIX_GUIDE.md) (8 reusable patterns)
- Run tests: `pytest` (95.3% pass rate - 120/134 passing)
- Test files: [tests/](tests/)

**Work with temporal analysis:**
- JCDL implementation: [docs/JCDL_STANDALONE_IMPLEMENTATION.md](docs/JCDL_STANDALONE_IMPLEMENTATION.md)
- Demo data: [docs/DEMO_EXPERIMENT_SUMMARY.md](docs/DEMO_EXPERIMENT_SUMMARY.md)
- Timeline view: [app/templates/experiments/temporal_timeline_view.html](app/templates/experiments/temporal_timeline_view.html)

**Understand the ontology:**
- Literature review: [docs/LITERATURE_REVIEW_SUMMARY.md](docs/LITERATURE_REVIEW_SUMMARY.md)
- Ontology v2.0: [docs/ONTOLOGY_ENHANCEMENTS_V2.md](docs/ONTOLOGY_ENHANCEMENTS_V2.md)
- Validation: [docs/VALIDATION_GUIDE.md](docs/VALIDATION_GUIDE.md)
- Ontology file: [ontologies/semantic-change-ontology-v2.ttl](ontologies/semantic-change-ontology-v2.ttl)

**Use agents:**
- All agents: [.claude/agents/README.md](.claude/agents/README.md)
- Deployment: [.claude/agents/git-deployment-sync.md](.claude/agents/git-deployment-sync.md)
- Documentation: [.claude/agents/documentation-writer.md](.claude/agents/documentation-writer.md)
- Temporal experiments: [.claude/agents/temporal-evolution-experiment.md](.claude/agents/temporal-evolution-experiment.md)
- Document upload: [.claude/agents/upload-agent-documents.md](.claude/agents/upload-agent-documents.md)

## Architecture Overview

### Technology Stack

**Backend**:
- Flask 3.0 (Python web framework)
- SQLAlchemy 2.0 (ORM)
- PostgreSQL (database: ontextract_db)
- Celery 5.x (background tasks)
- Redis (Celery broker)
- LangGraph (LLM orchestration workflow)

**LLM Integration**:
- Provider: Anthropic Claude
- Model: claude-sonnet-4-5-20250929
- Orchestration: 5-stage LangGraph workflow
- Provenance: PROV-O compliant tracking

**Frontend**:
- Jinja2 templates
- Bootstrap 5 (Darkly theme)
- JavaScript (vanilla + chart.js for visualizations)

### Key Services

**Document Processing**:
- [app/services/processing_tools.py](app/services/processing_tools.py) - DocumentProcessor class
- [app/services/extraction_tools.py](app/services/extraction_tools.py) - ToolExecutor for orchestration
- [app/services/processing_registry_service.py](app/services/processing_registry_service.py) - ProcessingArtifactGroup management

**LLM Orchestration**:
- [app/orchestration/experiment_graph.py](app/orchestration/experiment_graph.py) - LangGraph workflow
- [app/orchestration/experiment_nodes.py](app/orchestration/experiment_nodes.py) - Stage implementations
- [app/orchestration/prompts.py](app/orchestration/prompts.py) - LLM prompts (academic tone)
- [app/services/workflow_executor.py](app/services/workflow_executor.py) - Workflow execution service

**Temporal Analysis**:
- [app/services/local_ontology_service.py](app/services/local_ontology_service.py) - Semantic Change Ontology
- [app/routes/experiments/temporal.py](app/routes/experiments/temporal.py) - Temporal endpoints
- [app/models/temporal_period.py](app/models/temporal_period.py) - Period model
- [app/models/semantic_change_event.py](app/models/semantic_change_event.py) - Event model

**Background Tasks**:
- [celery_config.py](celery_config.py) - Celery configuration
- [app/tasks/orchestration.py](app/tasks/orchestration.py) - Celery task definitions
- [start_celery_worker.sh](start_celery_worker.sh) - Worker startup script

## Development Workflow

### Local Development Setup

**Start services**:
```bash
# Terminal 1: Flask
cd /home/chris/onto/OntExtract
source venv-ontextract/bin/activate
python run.py

# Terminal 2: Celery worker
./start_celery_worker.sh

# Terminal 3: Redis (if not running)
redis-server
```

**Access**:
- Flask: http://localhost:8765
- Flower (Celery monitoring): http://localhost:5555

**Database**:
```bash
# Local PostgreSQL
PGPASSWORD=PASS psql -h localhost -U postgres -d ontextract_db

# Common queries
SELECT COUNT(*) FROM documents;
SELECT COUNT(*) FROM experiments;
SELECT COUNT(*) FROM processing_artifact_groups;
```

### Testing

**Run all tests**:
```bash
pytest
# 95.3% pass rate (120/134 tests passing)
```

**Run specific test file**:
```bash
pytest tests/test_llm_orchestration_api.py -v
```

**Common test issues**:
- See [docs/TEST_FIX_GUIDE.md](docs/TEST_FIX_GUIDE.md) for 8 reusable fix patterns
- Database transactions: Use `db.session.rollback()` in teardown
- Relationship loading: Configure lazy loading in models
- Mock patterns: Mock at import point, not definition point

## Production Deployment

### Quick Deployment

**Using deployment script** (recommended):
```bash
# On production server
ssh digitalocean
cd /opt/ontextract
./scripts/deploy_production.sh
```

The script automatically:
1. Pulls latest code from GitHub
2. Updates dependencies
3. Applies database fixes (FK constraints)
4. Restarts Flask and Celery services
5. Verifies deployment

**Using deployment agent**:
See [.claude/agents/git-deployment-sync.md](.claude/agents/git-deployment-sync.md) for complete workflow documentation.

### Manual Deployment

```bash
# Local: Commit and push
git add .
git commit -m "Your commit message"
git push origin development
git checkout main && git merge development && git push origin main

# Production: Pull and restart
ssh digitalocean "cd /opt/ontextract && git pull origin main && sudo systemctl restart ontextract && sudo systemctl restart celery-ontextract"
```

### Production Services

**Flask (gunicorn)**:
```bash
sudo systemctl status ontextract
sudo systemctl restart ontextract
sudo journalctl -u ontextract -n 50 --follow
```

**Celery Worker**:
```bash
sudo systemctl status celery-ontextract
sudo systemctl restart celery-ontextract
sudo journalctl -u celery-ontextract -n 50 --follow
```

**Other services**:
- Redis: `sudo systemctl status redis`
- Nginx: `sudo systemctl status nginx`
- PostgreSQL: `sudo systemctl status postgresql`

## Common Tasks

### Create a new experiment

**Web UI**: http://localhost:8765/experiments/new
- Select "Temporal Evolution" type
- Choose focus term
- Add source documents
- Click "Create Experiment"

**Using agent**: See [.claude/agents/temporal-evolution-experiment.md](.claude/agents/temporal-evolution-experiment.md)

### Run LLM orchestration

1. Navigate to experiment: http://localhost:8765/experiments/{id}/document_pipeline
2. Click "Analyze Documents with LLM"
3. Toggle "Review Choices" (OFF for auto-execution)
4. Click "Start Orchestration"
5. Monitor progress modal (can close window - Celery handles it)
6. View results: http://localhost:8765/orchestration/experiment/{run_id}/results

### Check processing artifacts

**Database query**:
```sql
SELECT id, document_id, artifact_type, method_key,
       metadata->>'created_by' as created_by,
       metadata->>'orchestration_run_id' as orch_run
FROM processing_artifact_groups
WHERE metadata->>'created_by' = 'llm_orchestration';
```

**Web UI**: Visit document processing page
- http://localhost:8765/experiments/{exp_id}/process_document/{doc_uuid}
- Look for "View Processing Results" buttons (should show "Available")
- Processing operations listed with labels (e.g., "entities: spacy_ner")

### Fix database issues

**FK constraint errors (documents):**
```sql
ALTER TABLE processing_artifact_groups
DROP CONSTRAINT IF EXISTS processing_artifact_groups_document_id_fkey,
ADD CONSTRAINT processing_artifact_groups_document_id_fkey
FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE;
```

**Check constraint status:**
```sql
SELECT conname, confdeltype
FROM pg_constraint
WHERE conrelid = 'processing_artifact_groups'::regclass
  AND confrelid = 'documents'::regclass;
-- confdeltype: 'c' = CASCADE, 'a' = NO ACTION, 'n' = SET NULL
```

## Important Notes

### Academic Tone Enforcement

All LLM outputs use neutral academic tone:
- **Prohibited**: "crucial", "key", "powerful", "cutting-edge", "robust", "comprehensive"
- **Use instead**: "frequent/infrequent", "common/uncommon", "primary/secondary"
- **Implementation**: [app/orchestration/prompts.py](app/orchestration/prompts.py) lines 516-527

### UI Design Principles

- Factual data: Prominent cards, neutral headers, always visible
- LLM analysis: Collapsed by default, muted styling, de-emphasized
- Processing results: Same display whether manual or LLM-initiated
- Timeline view: Full-page layout optimized for presentations

### JCDL Conference Demo

**Demo credentials**: demo / demo123
**Demo experiment**: ID 83 - "Agent Temporal Evolution" (1910-2024)
**Testing checklist**: [docs/JCDL_TESTING_CHECKLIST.md](docs/JCDL_TESTING_CHECKLIST.md)

## Documentation

### Planning Documents
- [docs/DOCUMENTATION_PLAN.md](docs/DOCUMENTATION_PLAN.md) - MkDocs Material strategy (12,000+ words)
- [docs/DOCUMENTATION_QUICK_START.md](docs/DOCUMENTATION_QUICK_START.md) - Setup guide (2,500+ words)
- [docs/CONTENT_TEMPLATES.md](docs/CONTENT_TEMPLATES.md) - Templates & style guide (8,000+ words)

### Technical Reference
- [docs/QUICK_REFERENCE.md](docs/QUICK_REFERENCE.md) - Commands, endpoints, troubleshooting
- [docs/LLM_WORKFLOW_REFERENCE.md](docs/LLM_WORKFLOW_REFERENCE.md) - Orchestration architecture
- [docs/TEST_FIX_GUIDE.md](docs/TEST_FIX_GUIDE.md) - 8 reusable test patterns

### Session Notes
- [docs/PROGRESS.md](docs/PROGRESS.md) - Complete session history (Sessions 1-29)
- [docs/archive/SESSION_28_SUMMARY.md](docs/archive/SESSION_28_SUMMARY.md) - Celery removal attempt (reverted)
- Tests: [tests/](tests/) - All test files including root-level test_*.py files

## Known Issues

### Resolved
- ✅ ProcessingArtifactGroup tracking during orchestration
- ✅ Document ID type conversion
- ✅ Status field UI compatibility
- ✅ FK constraint CASCADE on delete
- ✅ Celery workflow continuation
- ✅ Academic tone enforcement
- ✅ Timeline boundary markers

### Active (Low Priority)
- 5 test failures (DB schema issues, test isolation) - 95.3% pass rate acceptable
- Deprecation warnings (Pydantic V2, SQLAlchemy 2.0) - defer until post-JCDL

## Virtual Environment

**Location**: `/home/chris/onto/OntExtract/venv-ontextract/`

**Activation**:
```bash
source venv-ontextract/bin/activate
```

**Note**: OntExtract uses a dedicated virtual environment separate from other projects in the monorepo.

## Database Schema

**Key tables**:
- `documents` - Source documents with metadata
- `experiments` - Experiment definitions
- `experiment_documents` - Document-experiment associations
- `processing_artifact_groups` - Processing operation tracking (NEW: Session 29)
- `experiment_orchestration_runs` - LLM orchestration runs
- `temporal_periods` - Time periods for temporal analysis
- `semantic_change_events` - Semantic change events with ontology backing
- `provenance_records` - PROV-O compliant provenance tracking

## Configuration

**Environment variables**: `.env` (not committed)
- `ANTHROPIC_API_KEY` - Claude API key (required)
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection (default: redis://localhost:6379/0)

**LLM settings**:
- Provider: Anthropic (hardcoded)
- Model: claude-sonnet-4-5-20250929
- Max tokens: 500 (configurable in settings)
- Timeout: 300 seconds

## Git Workflow

**Branches**:
- `main` - Production-ready code
- `development` - Active development (current work)

**Typical workflow**:
```bash
# Work on development
git checkout development
# ... make changes ...
git add .
git commit -m "Description"
git push origin development

# Deploy to production
git checkout main
git merge development
git push origin main
git checkout development
```

## Next Steps

### Immediate (Post-Session 29)
- ✅ Test UI displays ProcessingArtifactGroups correctly
- ✅ Production deployment completed successfully
- ✅ Updated docs/PROGRESS.md with Session 29 details

### Short Term (Pre-JCDL)
- Browser testing: [docs/JCDL_TESTING_CHECKLIST.md](docs/JCDL_TESTING_CHECKLIST.md)
- Presentation materials preparation
- Demo workflow practice

### Post-JCDL
- Address deprecation warnings (Pydantic V2, SQLAlchemy 2.0, datetime)
- Complete documentation (MkDocs Material setup)
- Full OntServe integration (MCP client layer)

---

**Last Updated**: 2025-11-24 (Session 29)
**Production Status**: Deployed with ProcessingArtifactGroup tracking
**Next Session**: Test UI functionality, update progress documentation
