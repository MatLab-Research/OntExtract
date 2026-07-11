"""Authorized orchestration provenance JSON routes."""

from flask import jsonify
from flask_login import current_user, login_required

from app.services.base_service import NotFoundError, PermissionError, ServiceError
from app.services.orchestration_read_service import OrchestrationReadService

from .. import experiments_bp
from .context import logger, orchestration_service


def _error(exc):
    if isinstance(exc, PermissionError):
        return jsonify({'error': 'Permission denied'}), 403
    if isinstance(exc, NotFoundError):
        return jsonify({'error': str(exc)}), 404
    logger.error('Failed to generate orchestration provenance', exc_info=True)
    return jsonify({'error': 'Failed to generate provenance data'}), 500


@experiments_bp.route('/<int:experiment_id>/orchestration-provenance.json')
@login_required
def orchestration_provenance_json(experiment_id):
    try:
        payload = OrchestrationReadService.experiment_provenance(
            experiment_id,
            current_user.id,
            orchestration_service,
        )
        return jsonify(payload)
    except (NotFoundError, PermissionError, ServiceError) as exc:
        return _error(exc)


@experiments_bp.route('/<int:experiment_id>/orchestration/llm-provenance/<uuid:run_id>')
@login_required
def download_llm_provenance(experiment_id, run_id):
    try:
        return jsonify(OrchestrationReadService.run_provenance(
            experiment_id,
            run_id,
            current_user.id,
        ))
    except (NotFoundError, PermissionError, ServiceError) as exc:
        return _error(exc)
