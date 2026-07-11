"""Human-in-the-loop orchestration review routes."""

from flask import abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.services.base_service import NotFoundError, PermissionError, ValidationError
from app.services.orchestration_read_service import OrchestrationReadService
from app.services.orchestration_review_service import (
    OrchestrationApprovalService,
    OrchestrationReviewService,
)
from app.utils.auth_decorators import api_require_login_for_write

from .. import experiments_bp
from .context import logger


@experiments_bp.route('/<int:experiment_id>/orchestration/review/<uuid:run_id>')
@login_required
def orchestration_review_page(experiment_id, run_id):
    """Render the dedicated LLM strategy review page."""
    try:
        OrchestrationReadService.authorized_run(
            run_id,
            current_user.id,
            experiment_id=experiment_id,
        )
        context = OrchestrationReviewService.build_review_context(
            experiment_id,
            run_id,
        )
        return render_template('experiments/orchestration_review.html', **context)
    except NotFoundError:
        abort(404)
    except PermissionError:
        abort(403)
    except ValidationError as exc:
        flash(str(exc), 'warning')
        return redirect(url_for(
            'experiments.document_pipeline',
            experiment_id=experiment_id,
        ))
    except Exception as exc:
        logger.error(
            f'Error loading orchestration review page: {exc}',
            exc_info=True,
        )
        abort(500)


@experiments_bp.route(
    '/orchestration/approve-strategy/<uuid:run_id>',
    methods=['POST'],
)
@api_require_login_for_write
def approve_orchestration_strategy(run_id):
    """Approve or reject a strategy and optionally queue its execution."""
    try:
        result = OrchestrationApprovalService.apply_decision(
            run_id,
            request.get_json() or {},
            current_user.id,
        )
        return jsonify(result), 200
    except NotFoundError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 404
    except PermissionError:
        return jsonify({'success': False, 'error': 'Permission denied'}), 403
    except ValidationError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    except Exception as exc:
        logger.error(
            f'Error approving strategy for run {run_id}: {exc}',
            exc_info=True,
        )
        return jsonify({
            'success': False,
            'error': 'Failed to apply orchestration decision',
        }), 500
