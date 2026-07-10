"""OED term enrichment/read APIs and service health endpoint."""

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user

from app.services.base_service import NotFoundError, PermissionError, ValidationError
from app.services.oed_enrichment import OEDEnrichmentService
from app.services.oed_service import OEDService
from app.services.oed_term_api_service import (
    OEDTermApiService,
    OEDTermUpstreamError,
)
from app.utils.auth_decorators import api_require_login_for_write


api_bp = Blueprint('api', __name__, url_prefix='/api')


def _service():
    return OEDTermApiService(OEDEnrichmentService(), OEDService())


def _error(message, status):
    return jsonify({'success': False, 'error': str(message)}), status


@api_bp.route('/terms/enrich-oed', methods=['POST'])
@api_require_login_for_write
def enrich_term_with_oed():
    data = request.get_json(silent=True) or {}
    try:
        return jsonify(_service().enrich(
            data.get('term_text'),
            current_user.id,
            experiment_id=data.get('experiment_id'),
            entry_id=data.get('entry_id'),
        ))
    except ValidationError as exc:
        return _error(exc, 400)
    except PermissionError as exc:
        return _error(exc, 403)
    except NotFoundError as exc:
        return _error(exc, 404)
    except OEDTermUpstreamError as exc:
        current_app.logger.error(str(exc), exc_info=True)
        return _error('OED term enrichment failed', 502)


@api_bp.route('/terms/<term_id>/oed-data', methods=['GET'])
@api_require_login_for_write
def get_term_oed_data(term_id):
    try:
        return jsonify({
            'success': True,
            'data': OEDTermApiService.get_persisted_data(term_id),
        })
    except NotFoundError as exc:
        return _error(exc, 404)


@api_bp.route('/terms/search-oed', methods=['GET'])
@api_require_login_for_write
def search_oed_entries():
    try:
        return jsonify(_service().search(
            request.args.get('term'),
            request.args.get('limit', 10),
        ))
    except ValidationError as exc:
        return _error(exc, 400)
    except OEDTermUpstreamError as exc:
        current_app.logger.error(str(exc), exc_info=True)
        return _error('OED search failed', 502)


@api_bp.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'service': 'OntExtract API'})
