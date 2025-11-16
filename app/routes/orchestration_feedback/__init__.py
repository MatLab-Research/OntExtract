"""
Human-in-the-Loop Orchestration Feedback Routes

RESTful API endpoints for researchers to provide feedback on orchestration decisions
and apply manual overrides for continuous system improvement.
"""

from flask import Blueprint

bp = Blueprint('orchestration_feedback', __name__, url_prefix='/orchestration')

# Import route modules to register them with the blueprint
from . import dashboard, decisions, patterns, analytics, helpers  # noqa: F401, E402
