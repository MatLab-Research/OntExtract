"""Experiment embedding result route."""

from flask import abort, render_template

from app.services.base_service import NotFoundError
from app.services.experiment_embedding_results_service import (
    ExperimentEmbeddingResultsService,
)

from .. import experiments_bp


@experiments_bp.route('/<int:experiment_id>/results/embeddings')
def experiment_embeddings_results(experiment_id):
    """Render persisted embedding summaries for an experiment."""
    try:
        context = ExperimentEmbeddingResultsService.get_context(experiment_id)
        return render_template('experiments/results/embeddings.html', **context)
    except NotFoundError:
        abort(404)
