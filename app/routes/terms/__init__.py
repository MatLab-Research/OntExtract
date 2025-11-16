"""
Terms Blueprint Package

This package contains the terms blueprint and all its route modules.

The terms blueprint is organized into focused modules:
- crud.py: Basic CRUD operations (list, add, view, edit, delete, add version)
- analysis.py: Term analysis operations (analyze, detect drift)
- api.py: API endpoints (context anchors, search, fuzziness)
- import_export.py: Import and export operations
- stats.py: Status and statistics endpoints

All routes have been extracted and organized into these focused modules.
"""

from flask import Blueprint, current_app

# Create the terms blueprint
# This will be imported by route modules
terms_bp = Blueprint('terms', __name__, url_prefix='/terms')

# Initialize term analysis service (singleton)
_term_analysis_service = None


def get_term_analysis_service():
    """Get or create term analysis service instance."""
    global _term_analysis_service
    if _term_analysis_service is None:
        try:
            from app.services.term_analysis_service import TermAnalysisService
            _term_analysis_service = TermAnalysisService()
            current_app.logger.info("TermAnalysisService initialized successfully")
        except Exception as e:
            current_app.logger.error(f"Failed to initialize TermAnalysisService: {e}")
            _term_analysis_service = None
    return _term_analysis_service


# Import route modules to register their routes
# This must come after blueprint creation
from . import crud  # noqa: F401, E402
from . import analysis  # noqa: F401, E402
from . import api  # noqa: F401, E402
from . import import_export  # noqa: F401, E402
from . import stats  # noqa: F401, E402
