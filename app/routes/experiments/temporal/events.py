"""Semantic event creation, update, and removal routes."""

from flask import jsonify, request
from flask_login import current_user

from app.services.base_service import NotFoundError, PermissionError, ValidationError
from app.services.semantic_event_service import SemanticEventService
from app.utils.auth_decorators import api_require_login_for_write

from .. import experiments_bp
from .context import logger


def _error(exc, status):
    return jsonify({'success': False, 'error': str(exc)}), status


@experiments_bp.route('/<int:experiment_id>/save_semantic_event', methods=['POST'])
@api_require_login_for_write
def save_semantic_event(experiment_id):
    try:
        return jsonify(SemanticEventService().save(
            experiment_id,
            request.get_json(silent=True),
            current_user,
        ))
    except NotFoundError as exc:
        return _error(exc, 404)
    except PermissionError as exc:
        return _error(exc, 403)
    except ValidationError as exc:
        return _error(exc, 400)
    except Exception as exc:
        logger.error(
            f'Error saving semantic event for experiment {experiment_id}: {exc}',
            exc_info=True,
        )
        return _error(exc, 500)


@experiments_bp.route('/<int:experiment_id>/remove_semantic_event', methods=['POST'])
@api_require_login_for_write
def remove_semantic_event(experiment_id):
    try:
        data = request.get_json(silent=True) or {}
        return jsonify(SemanticEventService().remove(
            experiment_id,
            data.get('event_id'),
            current_user,
        ))
    except NotFoundError as exc:
        return _error(exc, 404)
    except PermissionError as exc:
        return _error(exc, 403)
    except ValidationError as exc:
        return _error(exc, 400)
    except Exception as exc:
        logger.error(
            f'Error removing semantic event for experiment {experiment_id}: {exc}',
            exc_info=True,
        )
        return _error(exc, 500)
