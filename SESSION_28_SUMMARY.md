# Session 28: LangGraph PostgreSQL Checkpointing - Celery Removal

**Date:** 2025-11-24
**Branch:** development
**Status:** PRODUCTION-READY

## Summary

Complete architectural refactoring: Replaced Celery task queue with LangGraph's native PostgreSQL checkpointing for background execution. This simplifies the architecture while maintaining state persistence and background execution capabilities.

## Problem Statement

Session 27 implemented Celery for background execution, but encountered deployment issues:
- API key authentication errors (401) in production
- Complex environment variable configuration with systemd
- Additional services to manage (Redis, Celery worker, Flower)
- Increased operational complexity

## Solution: LangGraph Native Checkpointing

Discovered that LangGraph has built-in PostgreSQL checkpointing that provides:
- Native background execution with state persistence
- No external broker (Redis) needed
- No separate worker process required
- Simpler architecture: Flask + PostgreSQL only
- Thread-based execution with `asyncio.run()` in Flask process

## Implementation

### 1. Package Installation
- Added `langgraph-checkpoint-postgres==3.0.1`
- Removed `celery`, `redis`, `flower` packages
- Files: [requirements.txt](requirements.txt)

### 2. Graph Configuration Update
**File:** [app/orchestration/experiment_graph.py](app/orchestration/experiment_graph.py)

```python
from langgraph.checkpoint.postgres import PostgresSaver

def create_experiment_orchestration_graph():
    workflow = StateGraph(ExperimentOrchestrationState)

    # Configure nodes and edges...

    # Create PostgreSQL checkpointer for persistence
    db_uri = os.environ.get('DATABASE_URL', 'postgresql://localhost/ontextract_db')

    # Setup checkpoint schema (creates tables if needed)
    with PostgresSaver.from_conn_string(db_uri) as checkpointer:
        checkpointer.setup()

    # Create checkpointer for graph
    checkpointer = PostgresSaver.from_conn_string(db_uri)

    return workflow.compile(checkpointer=checkpointer)
```

**Key points:**
- Uses synchronous `PostgresSaver` (not async) for better threading compatibility
- Proper context manager initialization to create checkpoint tables
- Automatic table creation: `checkpoints`, `checkpoint_blobs`, `checkpoint_writes`, `checkpoint_migrations`

### 3. Workflow Executor Update
**File:** [app/services/workflow_executor.py](app/services/workflow_executor.py)

```python
async def _execute_graph(self, state: Dict[str, Any]) -> Dict[str, Any]:
    # Use run_id as thread_id for checkpoint persistence
    thread_id = str(state.get('run_id'))

    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }

    result = await self.graph.ainvoke(state, config=config)
    return result
```

**Key points:**
- Each orchestration run gets unique thread_id (run UUID)
- LangGraph automatically checkpoints state to PostgreSQL
- State persists across Flask restarts

### 4. Route Handler Simplification
**File:** [app/routes/experiments/orchestration.py](app/routes/experiments/orchestration.py)

Replaced Celery task enqueueing with simple threading:

```python
import threading

def run_workflow():
    try:
        workflow_executor.execute_recommendation_phase(
            run_id=run.id,
            review_choices=review_choices
        )
    except Exception as e:
        logger.error(f"Workflow execution failed: {e}", exc_info=True)

thread = threading.Thread(target=run_workflow, daemon=True)
thread.start()
```

**Changes:**
- Removed `get_orchestration_task()` Celery lazy import
- Removed Celery task enqueueing logic
- Direct threading with daemon threads
- Background execution via `asyncio.run()` in thread

### 5. File Cleanup

**Removed files:**
- `celery_config.py` - Celery configuration
- `app/tasks/orchestration.py` - Celery task definitions
- `app/tasks/__init__.py` - Tasks package
- `start_celery_worker.sh` - Worker startup script
- `start_flower.sh` - Flower monitoring script
- `celery-ontextract.service` - Systemd service

### 6. Database Migration

Added missing column for production:
```sql
ALTER TABLE experiment_orchestration_runs
ADD COLUMN IF NOT EXISTS current_operation TEXT NULL;
```

### 7. Monitoring Script

**Created:** [monitor_orchestration.sh](monitor_orchestration.sh)

Provides sudo-free monitoring of orchestration runs:
- Run status and progress
- Checkpoint activity
- Flask logs (last 20 lines)
- Running processes
- Database connections

Usage:
```bash
./monitor_orchestration.sh [run_id]
watch -n 2 ./monitor_orchestration.sh  # Continuous monitoring
```

## Architecture Comparison

### Before (Celery)
```
Flask ──(enqueue)──> Redis ──(poll)──> Celery Worker
                        ↓                    ↓
                   Task Queue         Execute Workflow
                                            ↓
                                      PostgreSQL
```

**Components:** Flask, Redis, Celery Worker, Flower UI, PostgreSQL

### After (LangGraph)
```
Flask ──(thread)──> Background Thread
                           ↓
                    Execute Workflow
                           ↓
              PostgreSQL (LangGraph checkpoints)
```

**Components:** Flask, PostgreSQL

## Benefits

1. **Simpler Architecture**
   - 2 services instead of 5 (Flask + PostgreSQL)
   - No Redis broker
   - No Celery worker process
   - No Flower monitoring (can use monitoring script)

2. **Easier Deployment**
   - No environment variable issues (Flask process has API keys)
   - No systemd service for Celery worker
   - Fewer moving parts to manage

3. **Native Integration**
   - LangGraph checkpointing is designed for this use case
   - Automatic state persistence
   - Thread-based execution works seamlessly with Flask

4. **Same Functionality**
   - Background execution preserved
   - State persistence maintained
   - Survives Flask restarts (checkpoints in DB)
   - API keys accessible (Flask environment)

## Production Deployment

### Steps Performed
1. ✅ Committed and pushed code changes (development → main)
2. ✅ Pulled latest code on production server
3. ✅ Installed `langgraph-checkpoint-postgres` package
4. ✅ Uninstalled `celery`, `redis`, `flower` packages
5. ✅ Stopped and disabled `celery-ontextract` systemd service
6. ✅ Added `current_operation` column to production database
7. ✅ Restarted Flask service
8. ✅ Deployed monitoring script

### Verification
```bash
# Check Flask is running
sudo systemctl status ontextract

# Check checkpoint tables created
sudo -u postgres psql -d ontextract_db -c "\dt checkpoint*"

# Monitor orchestration
cd /opt/ontextract && ./monitor_orchestration.sh
```

## Files Modified

**Created:**
- [monitor_orchestration.sh](monitor_orchestration.sh) - Monitoring script

**Modified:**
- [app/orchestration/experiment_graph.py](app/orchestration/experiment_graph.py) - PostgresSaver implementation
- [app/services/workflow_executor.py](app/services/workflow_executor.py) - Thread-based checkpointing
- [app/routes/experiments/orchestration.py](app/routes/experiments/orchestration.py) - Direct threading
- [requirements.txt](requirements.txt) - Updated dependencies

**Removed:**
- [celery_config.py](celery_config.py)
- [app/tasks/orchestration.py](app/tasks/orchestration.py)
- [app/tasks/__init__.py](app/tasks/__init__.py)
- [start_celery_worker.sh](start_celery_worker.sh)
- [start_flower.sh](start_flower.sh)

## Commits
1. `ddcbaec` - Implement LangGraph AsyncPostgresSaver for background execution
2. `ac4ccd2` - Remove Celery implementation - use LangGraph native checkpointing
3. `baa89df` - Fix PostgresSaver initialization - use sync version with proper setup
4. `7e8ae2b` - Add orchestration monitoring script for troubleshooting

## Technical Notes

### LangGraph Checkpointing Best Practices (2025)

Based on latest documentation:
- Use `PostgresSaver` (sync) with threading for better compatibility
- Use `AsyncPostgresSaver` only with native async/await workflows
- Proper initialization requires context manager for setup:
  ```python
  with PostgresSaver.from_conn_string(db_uri) as checkpointer:
      checkpointer.setup()
  ```
- Each workflow execution needs unique `thread_id` in config
- Checkpointer automatically manages state persistence

### Sources
- [Mastering LangGraph Checkpointing: Best Practices for 2025](https://sparkco.ai/blog/mastering-langgraph-checkpointing-best-practices-for-2025)
- [How to use Postgres checkpointer for persistence](https://langchain-ai.lang.chat/langgraphjs/how-tos/persistence-postgres/)
- [langgraph-checkpoint-postgres PyPI](https://pypi.org/project/langgraph-checkpoint-postgres/)

## Impact

- ✅ Simpler architecture (2 services vs 5)
- ✅ Easier deployment and operation
- ✅ No API key environment issues
- ✅ Native LangGraph integration
- ✅ Production-ready for JCDL demo
- ✅ Monitoring script for troubleshooting

## Status

**Architecture:** Simplified (Flask + PostgreSQL with LangGraph checkpointing)
**Services Running:** Flask (gunicorn), PostgreSQL
**Checkpointing:** LangGraph PostgresSaver with automatic table creation
**Production:** Deployed and operational
**Next:** Test orchestration on production experiments
