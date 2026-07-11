"""Authorized orchestration status JSON routes."""

from flask import jsonify
from flask_login import current_user, login_required

from app.services.base_service import NotFoundError, PermissionError
from app.services.orchestration_read_service import OrchestrationReadService

from .. import experiments_bp


def _error(exc):
    if isinstance(exc, PermissionError):
        return jsonify({'error': 'Permission denied'}), 403
    return jsonify({'error': str(exc)}), 404


@experiments_bp.route('/<int:experiment_id>/orchestration/check-status')
@login_required
def check_experiment_processing_status(experiment_id):
    try:
        return jsonify(OrchestrationReadService.processing_status(
            experiment_id,
            current_user.id,
        ))
    except (NotFoundError, PermissionError) as exc:
        return _error(exc)


@experiments_bp.route('/<int:experiment_id>/orchestration/latest-run')
@login_required
def get_latest_orchestration_run(experiment_id):
    try:
        return jsonify(OrchestrationReadService.latest_run(
            experiment_id,
            current_user.id,
        ))
    except NotFoundError as exc:
        if str(exc) == 'No active orchestration run found':
            return jsonify({'run_id': None, 'status': None}), 404
        return _error(exc)
    except PermissionError as exc:
        return _error(exc)


@experiments_bp.route('/orchestration/status/<uuid:run_id>')
@login_required
def get_orchestration_status(run_id):
    try:
        return jsonify(OrchestrationReadService.run_status(
            run_id,
            current_user.id,
        ))
    except (NotFoundError, PermissionError) as exc:
        return _error(exc)
