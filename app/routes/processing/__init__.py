"""
Processing Blueprint Package

This package contains the processing blueprint and all its route modules.

The processing blueprint is organized into focused modules:
- status.py: Status monitoring and job tracking
- pipeline.py: Core document processing (embeddings, segmentation, entities, metadata)
- batch.py: Batch processing operations
- validation.py: Testing and validation utilities

Routes are registered when this package is imported.
"""

from flask import Blueprint

# Create the processing blueprint
processing_bp = Blueprint('processing', __name__)

# Import route modules to register their routes
# This happens when the package is imported
# Note: Only importing pipeline to avoid duplicate endpoint conflicts with status.py
# TODO: Resolve duplicate endpoint names (job_list exists in both pipeline.py and status.py)
from . import pipeline  # noqa: F401
