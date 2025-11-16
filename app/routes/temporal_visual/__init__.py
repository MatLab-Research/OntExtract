"""
Temporal Evolution Visual Interface

Routes for visualizing and analyzing temporal evolution of terms.
"""

from flask import Blueprint

temporal_visual_bp = Blueprint('temporal_visual', __name__, url_prefix='/temporal-visual')

# Import route modules to register them with the blueprint
from . import views, api  # noqa: F401, E402
