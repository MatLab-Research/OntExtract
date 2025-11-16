"""
Temporal Visual View Routes

View routes for temporal evolution visual interface.

Routes:
- GET /temporal-visual/                      - Main interface
- GET /temporal-visual/experiment/<id>       - Experiment view
"""

from flask import render_template, jsonify
from app.models import Experiment
import logging

from . import temporal_visual_bp

logger = logging.getLogger(__name__)


@temporal_visual_bp.route('/')
def index():
    """Main temporal evolution visual interface."""
    return render_template('experiments/temporal_evolution_visual.html')


@temporal_visual_bp.route('/experiment/<int:experiment_id>')
def experiment_view(experiment_id):
    """View temporal evolution for a specific experiment."""
    try:
        experiment = Experiment.query.get_or_404(experiment_id)

        # Verify this is a temporal evolution experiment
        if experiment.experiment_type != 'temporal_evolution':
            return jsonify({
                'error': 'This experiment is not a temporal evolution type',
                'experiment_type': experiment.experiment_type
            }), 400

        return render_template('experiments/temporal_evolution_visual.html',
                             experiment=experiment)
    except Exception as e:
        logger.error(f"Error loading temporal evolution experiment {experiment_id}: {str(e)}")
        return jsonify({'error': 'Failed to load experiment'}), 500
