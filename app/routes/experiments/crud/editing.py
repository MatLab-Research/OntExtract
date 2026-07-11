"""Authorized experiment editing HTTP adapters."""

from flask import abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user
from pydantic import ValidationError as PydanticValidationError

from app.dto.experiment_dto import UpdateExperimentDTO
from app.services.base_service import (
    NotFoundError,
    PermissionError,
    ServiceError,
    ValidationError,
)
from app.services.experiment_editing_service import ExperimentEditingService
from app.utils.auth_decorators import api_require_login_for_write, write_login_required

from .. import experiments_bp
from .context import logger


@experiments_bp.route('/<int:experiment_id>/edit')
@write_login_required
def edit(experiment_id):
    try:
        context = ExperimentEditingService.get_context(
            experiment_id,
            current_user.id,
        )
    except NotFoundError:
        abort(404)
    except PermissionError:
        abort(403)
    except ValidationError as exc:
        flash(str(exc), 'warning')
        return redirect(url_for('experiments.view', experiment_id=experiment_id))
    return render_template('experiments/edit.html', **context)


@experiments_bp.route('/<int:experiment_id>/update', methods=['POST'])
@api_require_login_for_write
def update(experiment_id):
    try:
        data = UpdateExperimentDTO(**(request.get_json(silent=True) or {}))
        experiment = ExperimentEditingService.update(
            experiment_id,
            data,
            current_user.id,
        )
        return jsonify({
            'success': True,
            'message': 'Experiment updated successfully',
            'experiment_id': experiment.id,
        })
    except PydanticValidationError as exc:
        return jsonify({
            'success': False,
            'error': 'Validation failed',
            'details': exc.errors(include_context=False),
        }), 400
    except ValidationError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    except PermissionError:
        return jsonify({'success': False, 'error': 'Permission denied'}), 403
    except NotFoundError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 404
    except ServiceError as exc:
        logger.error(
            'Failed to update experiment %s: %s',
            experiment_id,
            exc,
            exc_info=True,
        )
        return jsonify({
            'success': False,
            'error': 'Failed to update experiment',
        }), 500
