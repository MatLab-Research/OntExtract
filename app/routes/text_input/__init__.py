"""
Text Input Blueprint Package

This package contains the text_input blueprint and all its route modules.

The text_input blueprint is organized into focused modules:
- forms.py: Upload and paste forms (upload_form, paste_form, submit_text, upload_file)
- crud/: Document listing, editing, and deletion routes
- api.py: API endpoints (document content, document list)
- processing.py: Processing operations (apply embeddings)

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
