"""
Processing Blueprint Package

This package contains the processing blueprint and all its route modules.

The processing blueprint is organized into focused modules:
- status.py: Status monitoring and job tracking
- pipeline.py: Core document processing (embeddings, segmentation, entities, metadata)
- batch.py: Batch processing operations
- validation.py: Testing and validation utilities

All routes have been extracted and organized into these focused modules.
"""

from flask import Blueprint

# Create the processing blueprint
# This will be imported by route modules
processing_bp = Blueprint('processing', __name__)

# Import route modules to register their routes
# This must come after blueprint creation
from . import status  # noqa: F401, E402
from . import pipeline  # noqa: F401, E402
from . import batch  # noqa: F401, E402
from . import validation  # noqa: F401, E402
