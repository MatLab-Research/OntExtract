"""Experiment segmentation result page."""

from flask import abort, render_template

from app.services.base_service import NotFoundError
from app.services.experiment_segment_results_service import (
    ExperimentSegmentResultsService,
)

from .. import experiments_bp


@experiments_bp.route('/<int:experiment_id>/results/segments')
def experiment_segments_results(experiment_id):
    try:
        context = ExperimentSegmentResultsService.get_context(experiment_id)
    except NotFoundError:
        abort(404)
    return render_template('experiments/results/segments.html', **context)
