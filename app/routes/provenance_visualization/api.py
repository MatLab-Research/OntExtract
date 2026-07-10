"""PROV-O timeline and graph JSON APIs."""

from flask import jsonify, request
from flask_login import login_required

from app.services.provenance_service import provenance_service

from . import bp


@bp.route('/api/timeline')
@login_required
def api_timeline():
    """
    API endpoint for timeline data (for AJAX/dynamic updates).
    """
    experiment_id = request.args.get('experiment_id', type=int)
    activity_type = request.args.get('activity_type')
    limit = request.args.get('limit', 50, type=int)

    timeline_data = provenance_service.get_timeline(
        experiment_id=experiment_id,
        activity_type=activity_type,
        limit=limit
    )

    return jsonify({
        'success': True,
        'timeline': timeline_data,
        'count': len(timeline_data)
    })


@bp.route('/api/graph')
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
    experiment_id = request.args.get('experiment_id', type=int)
    document_id = request.args.get('document_id', type=int)
    term_id = request.args.get('term_id')
    limit = request.args.get('limit', 50, type=int)

    graph_data = provenance_service.get_graph_data(
        experiment_id=experiment_id,
        document_id=document_id,
        term_id=term_id,
        limit=limit
    )

    return jsonify({
        'success': True,
        **graph_data
    })
