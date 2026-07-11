"""Authorized orchestration result pages."""

from flask import abort, render_template
from flask_login import current_user, login_required

from app.services.base_service import NotFoundError, PermissionError
from app.services.orchestration_read_service import OrchestrationReadService

from .. import experiments_bp


@experiments_bp.route('/<int:experiment_id>/orchestration/llm-results/<uuid:run_id>')
@login_required
def llm_orchestration_results(experiment_id, run_id):
    try:
        context = OrchestrationReadService.results_context(
            experiment_id,
            run_id,
            current_user.id,
        )
    except NotFoundError:
        abort(404)
    except PermissionError:
        abort(403)
    return render_template(
        'experiments/llm_orchestration_results.html',
        **context,
    )
