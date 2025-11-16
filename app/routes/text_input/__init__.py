"""
Text Input Blueprint Package

This package contains the text_input blueprint and all its route modules.

The text_input blueprint is organized into focused modules:
- forms.py: Upload and paste forms (upload_form, paste_form, submit_text, upload_file)
- crud.py: Document CRUD operations (list, detail, delete, delete_all_versions)
- api.py: API endpoints (document content, document list)
- processing.py: Processing operations (apply embeddings)
- composite.py: Composite document operations (create, get sources, update)

All routes have been extracted and organized into these focused modules.
"""

from flask import Blueprint

# Create the text_input blueprint
text_input_bp = Blueprint('text_input', __name__)

# Import route modules to register their routes
# This must come after blueprint creation
from . import forms  # noqa: F401, E402
from . import crud  # noqa: F401, E402
from . import api  # noqa: F401, E402
from . import processing  # noqa: F401, E402
from . import composite  # noqa: F401, E402
