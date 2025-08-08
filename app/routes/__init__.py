# Route blueprints initialization
from .auth import auth_bp
from .text_input import text_input_bp
from .processing import processing_bp
from .results import results_bp

__all__ = ['auth_bp', 'text_input_bp', 'processing_bp', 'results_bp']
