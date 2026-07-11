"""Experiment entity result page."""

from flask import abort, render_template

from app.services.base_service import NotFoundError
from app.services.experiment_entity_results_service import (
    ExperimentEntityResultsService,
)

from .. import experiments_bp


@experiments_bp.route('/<int:experiment_id>/results/entities')
def experiment_entities_results(experiment_id):
    try:
        context = ExperimentEntityResultsService.get_context(experiment_id)
    except NotFoundError:
        abort(404)
    return render_template('experiments/results/entities.html', **context)
