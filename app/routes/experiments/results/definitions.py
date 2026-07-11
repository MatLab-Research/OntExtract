"""Experiment definition result page."""

from flask import abort, render_template

from app.services.base_service import NotFoundError
from app.services.experiment_definition_results_service import (
    ExperimentDefinitionResultsService,
)

from .. import experiments_bp


@experiments_bp.route('/<int:experiment_id>/results/definitions')
def experiment_definitions_results(experiment_id):
    try:
        context = ExperimentDefinitionResultsService.get_context(experiment_id)
    except NotFoundError:
        abort(404)
    return render_template(
        'experiments/results/definitions.html',
        **context,
    )
