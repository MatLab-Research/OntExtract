"""Temporal configuration and document-period generation routes."""

from flask import jsonify, request
from flask_login import current_user
from pydantic import ValidationError as PydanticValidationError

from app.dto.temporal_dto import UpdateTemporalTermsDTO
from app.services.base_service import (
    NotFoundError,
    PermissionError,
    ServiceError,
    ValidationError,
)
from app.utils.auth_decorators import api_require_login_for_write

from .. import experiments_bp
from .context import logger, temporal_service


def _error(exc, status):
    return jsonify({'success': False, 'error': str(exc)}), status


@experiments_bp.route('/<int:experiment_id>/update_temporal_terms', methods=['POST'])
@api_require_login_for_write
def update_temporal_terms(experiment_id):
    try:
        data = UpdateTemporalTermsDTO(**(request.get_json(silent=True) or {}))
        temporal_service.update_temporal_configuration(
            experiment_id,
            terms=data.terms,
            periods=data.periods,
            temporal_data=data.temporal_data,
            actor_id=current_user.id,
        )
        return jsonify({
            'success': True,
            'message': 'Temporal terms updated successfully',
        })
    except PydanticValidationError as exc:
        return jsonify({
            'success': False,
            'error': 'Validation failed',
            'details': exc.errors(include_context=False),
        }), 400
    except NotFoundError:
        return _error('Experiment not found', 404)
    except PermissionError as exc:
        return _error(exc, 403)
    except ValidationError as exc:
        return _error(exc, 400)
    except ServiceError as exc:
        logger.error(
            f'Failed to update temporal terms for experiment {experiment_id}: {exc}',
            exc_info=True,
        )
        return _error('Failed to update temporal terms', 500)


@experiments_bp.route('/<int:experiment_id>/get_temporal_terms')
@api_require_login_for_write
def get_temporal_terms(experiment_id):
    try:
        config = temporal_service.get_temporal_configuration(experiment_id)
        return jsonify({'success': True, **config})
    except NotFoundError:
        return _error('Experiment not found', 404)
    except ValidationError as exc:
        return _error(exc, 400)
    except ServiceError as exc:
        logger.error(
            f'Failed to get temporal terms for experiment {experiment_id}: {exc}',
            exc_info=True,
        )
        return _error('Failed to get temporal terms', 500)


@experiments_bp.route(
    '/<int:experiment_id>/generate_periods_from_documents',
    methods=['POST'],
)
@api_require_login_for_write
def generate_periods_from_documents(experiment_id):
    try:
        result = temporal_service.generate_periods_from_documents(
            experiment_id,
            current_user.id,
        )
        return jsonify({
            'success': True,
            'periods': result['periods'],
            'document_count': result['document_count'],
            'date_range': result['date_range'],
            'source_type': result.get('source_type', 'publication dates'),
            'using_fallback': result.get('using_fallback', False),
            'message': (
                f"Generated {len(result['periods'])} periods from "
                f"{result['document_count']} documents"
            ),
        })
    except NotFoundError:
        return _error('Experiment not found', 404)
    except PermissionError as exc:
        return _error(exc, 403)
    except ValidationError as exc:
        return _error(exc, 400)
    except ServiceError as exc:
        logger.error(
            f'Failed to generate periods for experiment {experiment_id}: {exc}',
            exc_info=True,
        )
        return _error('Failed to generate periods from documents', 500)
