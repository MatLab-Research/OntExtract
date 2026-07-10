"""Experiment detail and summary result pages."""

from flask import abort, flash, redirect, render_template, url_for

from app.services.base_service import NotFoundError
from app.services.experiment_detail_read_service import ExperimentDetailReadService

from .. import experiments_bp


@experiments_bp.route('/<int:experiment_id>')
def view(experiment_id):
    """Render the enhanced experiment dashboard."""
    try:
        context = ExperimentDetailReadService.get_detail_context(experiment_id)
        return render_template('experiments/view.html', **context)
    except NotFoundError:
        abort(404)


@experiments_bp.route('/<int:experiment_id>/results')
def results(experiment_id):
    """Redirect orchestration results or render a manual processing summary."""
    try:
        context = ExperimentDetailReadService.get_manual_results_context(
            experiment_id
        )
    except NotFoundError:
        abort(404)

    experiment = context['experiment']
    if experiment.status != 'completed':
        flash('Experiment has not been completed yet', 'warning')
        return redirect(url_for('experiments.view', experiment_id=experiment_id))

    orchestration_run = ExperimentDetailReadService.get_completed_orchestration(
        experiment_id
    )
    if orchestration_run:
        return redirect(url_for(
            'experiments.llm_orchestration_results',
            experiment_id=experiment_id,
            run_id=orchestration_run.id,
        ))
    return render_template('experiments/results.html', **context)
