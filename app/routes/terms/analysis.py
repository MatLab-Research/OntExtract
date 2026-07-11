"""Authorized term analysis and semantic-drift HTTP adapters."""

from flask import current_app, flash, jsonify, redirect, request, url_for
from flask_login import current_user

from app.services.base_service import (
    NotFoundError,
    PermissionError,
    ServiceError,
    ValidationError,
)
from app.services.term_analysis_workflow_service import (
    AnalysisUnavailableError,
    TermAnalysisWorkflowService,
)
from app.utils.auth_decorators import api_require_login_for_write

from . import get_term_analysis_service, terms_bp


def _workflow():
    return TermAnalysisWorkflowService(get_term_analysis_service())


def _json_error(message, status):
    return jsonify({'success': False, 'error': str(message)}), status


@terms_bp.route('/<uuid:term_id>/analyze', methods=['POST'])
@api_require_login_for_write
def analyze_term(term_id):
    try:
        data = request.get_json(silent=True) or {}
        result = _workflow().analyze(
            term_id,
            data.get('corpus_texts', []),
            current_user.id,
        )
        if request.is_json:
            return jsonify({
                'success': True,
                'analysis': result['analysis'],
            })
        flash(
            f'Analysis completed for "{result["term"].term_text}". '
            f'Fuzziness score: {result["analysis"]["fuzziness_score"]:.3f}',
            'success',
        )
    except (ValidationError, PermissionError, NotFoundError) as exc:
        if request.is_json:
            status = 400 if isinstance(exc, ValidationError) else (
                403 if isinstance(exc, PermissionError) else 404
            )
            return _json_error(
                'Permission denied' if status == 403 else exc,
                status,
            )
        flash(str(exc), 'error')
    except AnalysisUnavailableError as exc:
        if request.is_json:
            return _json_error(exc, 503)
        flash('Term analysis service is not available.', 'warning')
    except ServiceError as exc:
        current_app.logger.error(str(exc), exc_info=True)
        if request.is_json:
            return _json_error('Term analysis failed', 500)
        flash('An error occurred during analysis. Please try again.', 'error')
    return redirect(url_for('terms.view_term', term_id=term_id))


@terms_bp.route('/<uuid:term_id>/detect-drift', methods=['POST'])
@api_require_login_for_write
def detect_semantic_drift(term_id):
    data = request.get_json(silent=True) or {}
    if not data.get('baseline_version_id') or not data.get('comparison_version_id'):
        return _json_error('Both version IDs required', 400)
    try:
        return jsonify(_workflow().detect_drift(
            term_id,
            data['baseline_version_id'],
            data['comparison_version_id'],
            current_user.id,
        ))
    except ValidationError as exc:
        return _json_error(exc, 400)
    except PermissionError:
        return _json_error('Permission denied', 403)
    except NotFoundError as exc:
        return _json_error(exc, 404)
    except AnalysisUnavailableError as exc:
        return _json_error(exc, 503)
    except ServiceError as exc:
        current_app.logger.error(str(exc), exc_info=True)
        return _json_error('Semantic drift detection failed', 500)
