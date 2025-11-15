"""
Experiments Blueprint Package

This package contains the experiments blueprint and all its route modules.

The experiments blueprint is organized into focused modules:
- crud.py: Basic CRUD operations (create, read, update, delete, run)
- terms.py: Term management for domain comparison (to be extracted)
- temporal.py: Temporal term analysis (to be extracted)
- evolution.py: Semantic evolution analysis (to be extracted)
- orchestration.py: LLM orchestration (to be extracted)
- pipeline.py: Document processing pipelines (to be extracted)

The blueprint itself is registered here and route modules import it.
"""

from flask import Blueprint

# Create the experiments blueprint
# This will be imported by route modules
experiments_bp = Blueprint('experiments', __name__, url_prefix='/experiments')

# Import route modules to register their routes
# This must come after blueprint creation
from . import crud  # noqa: F401, E402
from . import terms  # noqa: F401, E402
from . import temporal  # noqa: F401, E402
from . import evolution  # noqa: F401, E402

# Import remaining routes (temporary until fully extracted)
from app.routes import experiments_remaining  # noqa: F401, E402

# Note: Additional modules will be imported as they are extracted:
# from . import orchestration  # LLM orchestration
# from . import pipeline   # Document pipeline
