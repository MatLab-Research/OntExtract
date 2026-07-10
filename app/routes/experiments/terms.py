"""Domain-comparison experiment term management routes."""

import logging

from flask import flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user
from pydantic import ValidationError as PydanticValidationError

from app.dto.term_dto import FetchDefinitionsDTO, UpdateTermsDTO
from app.services.base_service import (
    NotFoundError,
    PermissionError,
    ServiceError,
    ValidationError,
)
from app.services.term_service import get_term_service
from app.utils.auth_decorators import api_require_login_for_write

from . import experiments_bp


logger = logging.getLogger(__name__)
term_service = get_term_service()


def _api_error(exc, fallback=None, status=400):
    message = fallback or str(exc)
    return jsonify({'success': False, 'error': message}), status


@experiments_bp.route('/<int:experiment_id>/manage_terms')
@api_require_login_for_write
def manage_terms(experiment_id):
    try:
        experiment = term_service.get_experiment(experiment_id)
        config = term_service.get_term_configuration(experiment_id)
        return render_template(
            'experiments/term_manager.html',
            experiment=experiment,
            domains=config['domains'],
            terms=config['terms'],
        )
    except NotFoundError:
        return _api_error(
            NotFoundError(f'Experiment {experiment_id} not found'),
            status=404,
        )
    except ValidationError as exc:
        flash(str(exc), 'warning')
    except ServiceError as exc:
        logger.error(f'Service error getting term configuration: {exc}', exc_info=True)
        flash('Failed to load term configuration', 'danger')
    except Exception as exc:
        logger.error(
            f'Unexpected error getting term configuration: {exc}',
            exc_info=True,
        )
        flash('An unexpected error occurred', 'danger')
    return redirect(url_for('experiments.view', experiment_id=experiment_id))


@experiments_bp.route('/<int:experiment_id>/update_terms', methods=['POST'])
@api_require_login_for_write
def update_terms(experiment_id):
    try:
        data = UpdateTermsDTO(**(request.get_json(silent=True) or {}))
        term_service.update_term_configuration(
            experiment_id,
            terms=data.terms,
            domains=data.domains,
            definitions=data.definitions,
            actor_id=current_user.id,
        )
        return jsonify({'success': True, 'message': 'Terms updated successfully'})
    except PydanticValidationError as exc:
        return jsonify({
            'success': False,
            'error': 'Validation failed',
            'details': exc.errors(include_context=False),
        }), 400
    except NotFoundError as exc:
        return _api_error(exc, status=404)
    except PermissionError as exc:
        return _api_error(exc, 'Permission denied', 403)
    except ValidationError as exc:
        return _api_error(exc)
    except ServiceError as exc:
        logger.error(f'Service error updating terms: {exc}', exc_info=True)
        return _api_error(exc, 'Failed to update terms', 500)
    except Exception as exc:
        logger.error(f'Unexpected error updating terms: {exc}', exc_info=True)
        return _api_error(exc, 'An unexpected error occurred', 500)


@experiments_bp.route('/<int:experiment_id>/get_terms')
@api_require_login_for_write
def get_terms(experiment_id):
    try:
        config = term_service.get_term_configuration(experiment_id)
        return jsonify({'success': True, **config})
    except NotFoundError as exc:
        return _api_error(exc, status=404)
    except ValidationError as exc:
        return _api_error(exc)
    except ServiceError as exc:
        logger.error(f'Service error getting terms: {exc}', exc_info=True)
        return _api_error(exc, 'Failed to get terms', 500)
    except Exception as exc:
        logger.error(f'Unexpected error getting terms: {exc}', exc_info=True)
        return _api_error(exc, 'An unexpected error occurred', 500)


@experiments_bp.route('/<int:experiment_id>/fetch_definitions', methods=['POST'])
@api_require_login_for_write
def fetch_definitions(experiment_id):
    try:
        data = FetchDefinitionsDTO(**(request.get_json(silent=True) or {}))
        result = term_service.fetch_definitions(
            experiment_id,
            term=data.term,
            domains=data.domains,
            actor_id=current_user.id,
        )
        return jsonify({'success': True, **result})
    except PydanticValidationError as exc:
        return jsonify({
            'success': False,
            'error': 'Validation failed',
            'details': exc.errors(include_context=False),
        }), 400
    except NotFoundError as exc:
        return _api_error(exc, status=404)
    except PermissionError as exc:
        return _api_error(exc, 'Permission denied', 403)
    except ValidationError as exc:
        return _api_error(exc)
    except ServiceError as exc:
        logger.error(f'Service error fetching definitions: {exc}', exc_info=True)
        return _api_error(exc, 'Failed to fetch definitions', 500)
    except Exception as exc:
        logger.error(f'Unexpected error fetching definitions: {exc}', exc_info=True)
        return _api_error(exc, 'An unexpected error occurred', 500)
