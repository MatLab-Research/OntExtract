"""
References Blueprint Package

This package contains the references blueprint and all its route modules.

The references blueprint is organized into focused modules:
- crud.py: Basic CRUD operations (list, view, edit, delete, download)
- upload.py: Upload and parsing operations
- oed.py: Oxford English Dictionary operations and API endpoints
- api.py: Search and WordNet API endpoints

All routes have been extracted and organized into these focused modules.
"""

from flask import Blueprint

# Create the references blueprint
# This will be imported by route modules
references_bp = Blueprint('references', __name__, url_prefix='/references')

# Import route modules to register their routes
# This must come after blueprint creation
from . import crud  # noqa: F401, E402
from . import upload  # noqa: F401, E402
from . import oed  # noqa: F401, E402
from . import api  # noqa: F401, E402
