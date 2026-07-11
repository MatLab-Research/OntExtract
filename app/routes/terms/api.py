"""Term autocomplete, context discovery, and fuzziness API routes."""

from flask import current_app, flash, jsonify, redirect, request, url_for
from flask_login import current_user

from app.services.base_service import NotFoundError, PermissionError, ServiceError, ValidationError
from app.services.term_api_service import AnalysisUnavailableError, TermApiService
from app.utils.auth_decorators import api_require_login_for_write

from . import get_term_analysis_service, terms_bp


@terms_bp.route('/api/context-anchors')
@api_require_login_for_write
def api_context_anchors():
    return jsonify(TermApiService.search_context_anchors(
        request.args.get('query', ''),
        request.args.get('limit', 20),
    ))


@terms_bp.route('/api/terms/search')
@api_require_login_for_write
def api_term_search():
    return jsonify(TermApiService.search_terms(
        request.args.get('query', request.args.get('q', '')),
        request.args.get('limit', 10),
    ))


@terms_bp.route(
    '/<uuid:term_id>/versions/<uuid:version_id>/adjust-fuzziness',
    methods=['POST'],
)
@api_require_login_for_write
def adjust_fuzziness(term_id, version_id):
    try:
        adjustment = TermApiService.adjust_fuzziness(
            term_id,
            version_id,
            request.form.get('fuzziness_score'),
            request.form.get('adjustment_reason'),
            current_user.id,
        )
        flash(
            f'Fuzziness score adjusted to {float(adjustment.adjusted_score):.3f}.',
            'success',
        )
    except (NotFoundError, ValidationError, PermissionError) as exc:
        flash(str(exc), 'error')
    except Exception as exc:
        current_app.logger.error(
            f'Error adjusting fuzziness: {exc}',
            exc_info=True,
        )
        flash('An error occurred while adjusting the fuzziness score.', 'error')
    return redirect(url_for('terms.view_term', term_id=term_id))


@terms_bp.route('/api/discover-context-anchors')
@api_require_login_for_write
def api_discover_context_anchors():
    try:
        return jsonify(TermApiService.discover_context_anchors(
            request.args.get('term_text', ''),
            request.args.get('meaning_description', ''),
            request.args.get('limit', 10),
            get_term_analysis_service(),
        ))
    except ValidationError as exc:
        return jsonify({'error': str(exc)}), 400
    except ServiceError as exc:
        current_app.logger.error(str(exc), exc_info=True)
        return jsonify({'error': str(exc)}), 500


@terms_bp.route('/api/calculate-fuzziness', methods=['POST'])
@api_require_login_for_write
def api_calculate_fuzziness():
    data = request.get_json(silent=True) or {}
    if not data.get('term_id') or not data.get('version_id'):
        return jsonify({'error': 'Term ID and version ID required'}), 400
    try:
        return jsonify(TermApiService.calculate_fuzziness(
            data['term_id'],
            data['version_id'],
            get_term_analysis_service(),
        ))
    except NotFoundError as exc:
        return jsonify({'error': str(exc)}), 404
    except ValidationError as exc:
        return jsonify({'error': str(exc)}), 400
    except AnalysisUnavailableError as exc:
        return jsonify({'error': str(exc)}), 503
    except Exception as exc:
        current_app.logger.error(
            f'Error calculating fuzziness: {exc}',
            exc_info=True,
        )
        return jsonify({'error': 'Fuzziness calculation failed'}), 500
