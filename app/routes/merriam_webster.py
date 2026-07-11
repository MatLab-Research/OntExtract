"""Merriam-Webster dictionary and thesaurus proxy routes."""

from flask import Blueprint, current_app, jsonify

from app.services.base_service import ValidationError
from app.services.merriam_webster_service import (
    MerriamWebsterConfigurationError,
    MerriamWebsterService,
    MerriamWebsterUpstreamError,
)
from app.utils.auth_decorators import api_require_login_for_write


merriam_bp = Blueprint(
    'merriam',
    __name__,
    url_prefix='/api/merriam-webster',
)


def _service():
    return MerriamWebsterService(
        dictionary_key=current_app.config.get(
            'MERRIAM_WEBSTER_DICTIONARY_API_KEY'
        ),
        thesaurus_key=current_app.config.get(
            'MERRIAM_WEBSTER_THESAURUS_API_KEY'
        ),
        timeout=current_app.config.get('MERRIAM_WEBSTER_API_TIMEOUT', 10),
    )


def _lookup(method, service_name):
    try:
        return jsonify(method())
    except ValidationError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    except MerriamWebsterConfigurationError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 503
    except MerriamWebsterUpstreamError as exc:
        current_app.logger.error(str(exc), exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Failed to fetch {service_name} data',
        }), 502


@merriam_bp.route('/dictionary/<term>')
@api_require_login_for_write
def search_dictionary(term):
    service = _service()
    return _lookup(
        lambda: service.search_dictionary(term),
        'dictionary',
    )


@merriam_bp.route('/thesaurus/<term>')
@api_require_login_for_write
def search_thesaurus(term):
    service = _service()
    return _lookup(
        lambda: service.search_thesaurus(term),
        'thesaurus',
    )


@merriam_bp.route('/test')
@api_require_login_for_write
def test_api():
    return jsonify({
        'message': 'Merriam-Webster API integration active',
        'endpoints': {
            'dictionary': '/api/merriam-webster/dictionary/<term>',
            'thesaurus': '/api/merriam-webster/thesaurus/<term>',
        },
        'api_keys_configured': _service().configuration_status(),
    })
