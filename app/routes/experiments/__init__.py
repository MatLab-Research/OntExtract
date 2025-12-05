"""
Experiments Blueprint Package

This package contains the experiments blueprint and all its route modules.

The experiments blueprint is organized into focused modules:
- crud.py: Basic CRUD operations (create, read, update, delete, run)
- terms.py: Term management for domain comparison
- temporal.py: Temporal term analysis
- evolution.py: Semantic evolution analysis
- orchestration.py: LLM orchestration
- pipeline.py: Document processing pipelines

All routes have been successfully extracted and organized into these focused modules.
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
from . import orchestration  # noqa: F401, E402
from . import pipeline  # noqa: F401, E402
from . import results  # noqa: F401, E402
