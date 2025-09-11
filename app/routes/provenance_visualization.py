"""
Route for serving the PROV-O provenance graph visualization
"""

from flask import Blueprint, render_template

bp = Blueprint('provenance', __name__, url_prefix='/provenance')

@bp.route('/graph')
def provenance_graph():
    """Display the PROV-O provenance graph visualization."""
    return render_template('provenance_graph.html')

@bp.route('/graph/compact')
def provenance_graph_compact():
    """Display the compact PROV-O provenance graph for papers."""
    return render_template('provenance_graph_compact.html')

@bp.route('/graph/simple')
def provenance_graph_simple():
    """Display the simple PROV-O provenance graph with manual layout."""
    return render_template('provenance_graph_simple.html')
