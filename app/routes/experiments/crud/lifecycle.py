"""Experiment duplication, execution, completion, and deletion routes."""

from flask import flash, jsonify, url_for
from flask_login import current_user

from app.services.base_service import (
    NotFoundError,
    PermissionError,
    ServiceError,
    ValidationError,
)
from app.services.experiment_lifecycle_service import ExperimentLifecycleService
from app.utils.auth_decorators import api_require_login_for_write

from .. import experiments_bp
from .context import experiment_service, logger


def _error(message, status):
    return jsonify({'success': False, 'error': message}), status


@experiments_bp.route('/<int:experiment_id>/delete', methods=['POST'])
@api_require_login_for_write
def delete(experiment_id):
    try:
        experiment_service.delete_experiment(experiment_id, current_user.id)
        return jsonify({
            'success': True,
            'message': (
                'Experiment and all associated processing data deleted successfully'
            ),
        })
    except NotFoundError as exc:
        return _error(str(exc), 404)
    except ValidationError as exc:
        logger.warning(f'Validation error deleting experiment {experiment_id}: {exc}')
        return _error(str(exc), 400)
    except PermissionError as exc:
        logger.warning(f'Permission error deleting experiment {experiment_id}: {exc}')
        return _error('Permission denied', 403)
    except ServiceError as exc:
        logger.error(
            f'Service error deleting experiment {experiment_id}: {exc}',
            exc_info=True,
        )
        return _error('Failed to delete experiment', 500)
    except Exception as exc:
        logger.error(
            f'Unexpected error deleting experiment {experiment_id}: {exc}',
            exc_info=True,
        )
        return _error('An unexpected error occurred', 500)


@experiments_bp.route('/<int:experiment_id>/duplicate', methods=['POST'])
@api_require_login_for_write
def duplicate(experiment_id):
    try:
        duplicated = ExperimentLifecycleService.duplicate(
            experiment_id,
            current_user.id,
        )
        flash(
            f'Created new experiment "{duplicated.name}". '
            'You can now edit and run it.',
            'success',
        )
        return jsonify({
            'success': True,
            'message': 'Experiment duplicated successfully',
            'new_experiment_id': duplicated.id,
            'redirect_url': url_for(
                'experiments.edit',
                experiment_id=duplicated.id,
            ),
        })
    except NotFoundError as exc:
        return _error(str(exc), 404)
    except Exception as exc:
        logger.error(
            f'Error duplicating experiment {experiment_id}: {exc}',
            exc_info=True,
        )
        return _error('Failed to duplicate experiment', 500)


@experiments_bp.route('/<int:experiment_id>/mark-complete', methods=['POST'])
@api_require_login_for_write
def mark_complete(experiment_id):
    try:
        ExperimentLifecycleService.mark_complete(
            experiment_id,
            current_user.id,
        )
        logger.info(
            f'Experiment {experiment_id} manually marked as complete '
            f'by user {current_user.id}'
        )
        return jsonify({
            'success': True,
            'message': 'Experiment marked as complete',
            'status': 'completed',
        })
    except NotFoundError as exc:
        return _error(str(exc), 404)
    except PermissionError as exc:
        return _error(str(exc), 403)
    except ValidationError as exc:
        return _error(str(exc), 400)
    except Exception as exc:
        logger.error(
            f'Error marking experiment {experiment_id} as complete: {exc}',
            exc_info=True,
        )
        return _error('Failed to mark experiment as complete', 500)


@experiments_bp.route('/<int:experiment_id>/run', methods=['POST'])
@api_require_login_for_write
def run(experiment_id):
    try:
        experiment = ExperimentLifecycleService().run(
            experiment_id,
            current_user.id,
        )
        return jsonify({
            'success': True,
            'message': 'Experiment completed successfully',
            'results_summary': experiment.results_summary,
        })
    except NotFoundError as exc:
        return _error(str(exc), 404)
    except PermissionError as exc:
        return _error(str(exc), 403)
    except ValidationError as exc:
        return jsonify({'error': str(exc)}), 400
    except Exception as exc:
        logger.error(f'Error running experiment {experiment_id}: {exc}', exc_info=True)
        return jsonify({'error': str(exc)}), 500
