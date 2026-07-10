"""Experiment temporal-expression result page."""

from flask import abort, render_template

from app.services.base_service import NotFoundError
from app.services.experiment_temporal_results_service import (
    ExperimentTemporalResultsService,
)

from .. import experiments_bp


@experiments_bp.route('/<int:experiment_id>/results/temporal')
def experiment_temporal_results(experiment_id):
    try:
        context = ExperimentTemporalResultsService.get_context(experiment_id)
    except NotFoundError:
        abort(404)
    return render_template('experiments/results/temporal.html', **context)
