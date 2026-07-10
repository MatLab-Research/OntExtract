"""PROV-O graph visualization pages."""

from flask import abort, render_template, request
from flask_login import current_user, login_required

from app.services.base_service import NotFoundError, PermissionError, ValidationError
from app.services.provenance_visualization_service import (
    ProvenanceVisualizationService,
)

from . import bp


@bp.route('/graph')
@login_required
def provenance_graph():
    """
    Display the PROV-O provenance graph visualization.

    Supports optional entity filters via query parameters:
    - experiment_id: Filter by experiment
    - document_id: Filter by document (includes all versions)
    - term_id: Filter by term UUID

    Examples:
    - /provenance/graph?document_id=123
    - /provenance/graph?experiment_id=83
    - /provenance/graph?term_id=uuid-string
    """
    try:
        context = ProvenanceVisualizationService.graph_context(
            request.args,
            current_user.id,
        )
    except ValidationError:
        abort(400)
    except PermissionError:
        abort(403)
    except NotFoundError:
        abort(404)
    return render_template('provenance_graph.html', **context)

@bp.route('/graph/compact')
def provenance_graph_compact():
    """Display the compact PROV-O provenance graph for papers."""
    return render_template('provenance_graph_compact.html')

@bp.route('/graph/simple')
def provenance_graph_simple():
    """Display the simple PROV-O provenance graph with manual layout."""
    return render_template('provenance_graph_simple.html')
