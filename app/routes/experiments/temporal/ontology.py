"""Semantic event and temporal period ontology catalog routes."""

from flask import flash, jsonify, redirect, render_template, url_for

from app.services.base_service import NotFoundError, ValidationError
from app.services.temporal_ontology_service import TemporalOntologyService
from app.utils.auth_decorators import api_require_login_for_write

from .. import experiments_bp
from .context import logger


@experiments_bp.route('/ontology/info', methods=['GET'])
def ontology_info():
    try:
        return render_template(
            'experiments/ontology_info.html',
            **TemporalOntologyService().get_info_context(),
        )
    except Exception as exc:
        logger.error(f'Error displaying ontology info: {exc}', exc_info=True)
        flash('Failed to load ontology information', 'danger')
        return redirect(url_for('experiments.index'))


@experiments_bp.route('/<int:experiment_id>/semantic_event_types', methods=['GET'])
@api_require_login_for_write
def get_semantic_event_types(experiment_id):
    try:
        return jsonify(
            TemporalOntologyService().get_event_catalog(experiment_id)
        )
    except NotFoundError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 404
    except ValidationError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    except Exception as exc:
        logger.error(f'Failed to load event types: {exc}', exc_info=True)
        return jsonify({'success': False, 'error': str(exc)}), 500


@experiments_bp.route('/period_types', methods=['GET'])
def get_period_types():
    return jsonify(TemporalOntologyService().get_period_catalog())
