"""Temporal visualization data and deterministic analysis API routes."""

import logging

from flask import jsonify, request

from app.services.base_service import NotFoundError, ValidationError
from app.services.temporal_visualization_service import TemporalVisualizationService

from . import temporal_visual_bp


logger = logging.getLogger(__name__)


def _read(method, identifier):
    try:
        return jsonify(method(identifier))
    except NotFoundError as exc:
        return jsonify({'error': str(exc)}), 404
    except Exception as exc:
        logger.error(f'Temporal visualization read failed: {exc}', exc_info=True)
        return jsonify({'error': 'Temporal visualization read failed'}), 500


@temporal_visual_bp.route('/api/experiment/<int:experiment_id>/data')
def get_experiment_data(experiment_id):
    return _read(TemporalVisualizationService.get_experiment_data, experiment_id)


@temporal_visual_bp.route('/api/analyze', methods=['POST'])
def analyze_temporal_evolution():
    try:
        return jsonify(TemporalVisualizationService.analyze(
            request.get_json(silent=True)
        ))
    except ValidationError as exc:
        return jsonify({'error': str(exc)}), 400
    except NotFoundError as exc:
        return jsonify({'error': str(exc)}), 404
    except Exception as exc:
        logger.error(f'Error analyzing temporal evolution: {exc}', exc_info=True)
        return jsonify({'error': 'Analysis failed', 'details': str(exc)}), 500


@temporal_visual_bp.route('/api/documents/<int:document_id>/details')
def get_document_details(document_id):
    return _read(TemporalVisualizationService.get_document_details, document_id)


@temporal_visual_bp.route('/api/experiments/temporal')
def list_temporal_experiments():
    try:
        return jsonify(TemporalVisualizationService.list_temporal_experiments())
    except Exception as exc:
        logger.error(f'Error listing temporal experiments: {exc}', exc_info=True)
        return jsonify({'error': 'Failed to list experiments'}), 500
