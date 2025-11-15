"""
Embeddings Blueprint Package

This package contains two related blueprints:
- embeddings_bp: API endpoints for embedding operations
- document_api_bp: API endpoints for document data access

The blueprints are organized into focused modules:
- embeddings.py: Embedding-related API endpoints (embeddings_bp)
- documents.py: Document data API endpoints (document_api_bp)

Both blueprints are exported from this package for registration in app/__init__.py.
"""

from flask import Blueprint

# Create the embeddings blueprint
embeddings_bp = Blueprint('embeddings', __name__, url_prefix='/api/embeddings')

# Create the document API blueprint
document_api_bp = Blueprint('document_api', __name__, url_prefix='/api/document')

# Import route modules to register their routes
# This must come after blueprint creation
from . import embeddings  # noqa: F401, E402
from . import documents  # noqa: F401, E402
