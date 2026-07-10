"""Orchestration run and experiment processing status routes."""

from flask import jsonify

from app.services.base_service import NotFoundError
from app.services.orchestration_status_service import OrchestrationStatusService

from .. import experiments_bp
from .context import logger


@experiments_bp.route('/<int:experiment_id>/orchestration/check-status', methods=['GET'])
def check_experiment_processing_status(experiment_id):
    try:
        return jsonify(
            OrchestrationStatusService.get_experiment_processing_status(
                experiment_id
            )
        )
    except NotFoundError as exc:
        return jsonify({'error': str(exc)}), 404
    except Exception as exc:
        logger.error(
            f'Error checking processing status for experiment {experiment_id}: {exc}',
            exc_info=True,
        )
        return jsonify({'error': str(exc)}), 500


@experiments_bp.route('/<int:experiment_id>/orchestration/latest-run', methods=['GET'])
def get_latest_orchestration_run(experiment_id):
    try:
        return jsonify(
            OrchestrationStatusService().get_latest_active_run(experiment_id)
        )
    except NotFoundError as exc:
        if str(exc) == 'No active orchestration run found':
            return jsonify({'run_id': None, 'status': None}), 404
        return jsonify({'error': str(exc)}), 404
    except Exception as exc:
        logger.error(
            f'Error getting latest run for experiment {experiment_id}: {exc}',
            exc_info=True,
        )
        return jsonify({'error': str(exc)}), 500


@experiments_bp.route('/orchestration/status/<uuid:run_id>', methods=['GET'])
def get_orchestration_status(run_id):
    try:
        return jsonify(OrchestrationStatusService.get_run_status(run_id))
    except NotFoundError as exc:
        return jsonify({'error': str(exc)}), 404
    except Exception as exc:
        logger.error(
            f'Error getting orchestration status for run {run_id}: {exc}',
            exc_info=True,
        )
        return jsonify({'error': str(exc)}), 500
