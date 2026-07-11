"""PROV-O timeline and graph JSON APIs."""

from flask import jsonify, request
from flask_login import current_user, login_required

from app.services.base_service import NotFoundError, PermissionError, ValidationError
from app.services.provenance_visualization_service import (
    ProvenanceVisualizationService,
)

from . import bp


@bp.route('/api/timeline')
@login_required
def api_timeline():
    """
    API endpoint for timeline data (for AJAX/dynamic updates).
    """
    return _response(lambda: ProvenanceVisualizationService.timeline_data(
        request.args,
        current_user.id,
    ))


@bp.route('/api/graph')
@login_required
def api_graph():
    """
    API endpoint for graph data in Cytoscape format.

    Query parameters:
    - experiment_id: Filter by experiment
    - document_id: Filter by document (includes all versions)
    - term_id: Filter by term UUID
    - limit: Maximum activities to include (default 50)

    Returns JSON with 'nodes', 'edges', and 'stats' arrays.
    """
    return _response(lambda: ProvenanceVisualizationService.graph_data(
        request.args,
        current_user.id,
    ))


def _response(factory):
    try:
        return jsonify(factory())
    except ValidationError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    except PermissionError:
        return jsonify({'success': False, 'error': 'Permission denied'}), 403
    except NotFoundError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 404
