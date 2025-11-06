"""
PROV-O Provenance Routes

Provides:
1. Graph visualizations (existing)
2. Timeline audit trail (new)
3. Entity lineage tracking (new)
"""

from flask import Blueprint, render_template, request, jsonify
from flask_login import current_user, login_required
from app.services.provenance_service import provenance_service
from app.models.experiment import Experiment

bp = Blueprint('provenance', __name__, url_prefix='/provenance')

# ========================================================================
# GRAPH VISUALIZATIONS (Existing)
# ========================================================================

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

# ========================================================================
# TIMELINE AUDIT TRAIL (New)
# ========================================================================

@bp.route('/timeline')
@login_required
def timeline():
    """
    Display complete provenance timeline.

    Filterable by:
    - Experiment
    - Activity type
    - Term
    - Date range
    """
    # Get filter parameters
    experiment_id = request.args.get('experiment_id', type=int)
    activity_type = request.args.get('activity_type')
    term_id = request.args.get('term_id', type=int)
    limit = request.args.get('limit', 50, type=int)

    # Get timeline data
    timeline_data = provenance_service.get_timeline(
        experiment_id=experiment_id,
        activity_type=activity_type,
        term_id=term_id,
        limit=limit
    )

    # Get experiments for filter dropdown
    experiments = Experiment.query.order_by(Experiment.created_at.desc()).all()

    # Get terms for filter dropdown
    from app.models.term import Term
    terms = Term.query.order_by(Term.term_text).all()

    # Get available activity types
    activity_types = [
        'term_creation',
        'term_update',
        'document_upload',
        'experiment_creation',
        'tool_execution',
        'orchestration_run'
    ]

    return render_template(
        'provenance/timeline.html',
        timeline=timeline_data,
        experiments=experiments,
        terms=terms,
        activity_types=activity_types,
        selected_experiment_id=experiment_id,
        selected_activity_type=activity_type,
        selected_term_id=term_id
    )


@bp.route('/experiment/<int:experiment_id>')
@login_required
def experiment_timeline(experiment_id):
    """
    Display provenance timeline for a specific experiment.
    """
    experiment = Experiment.query.get_or_404(experiment_id)

    # Get experiment-specific timeline
    timeline_data = provenance_service.get_timeline(
        experiment_id=experiment_id,
        limit=100
    )

    return render_template(
        'provenance/experiment_timeline.html',
        experiment=experiment,
        timeline=timeline_data
    )


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


@bp.route('/entity/<entity_id>/lineage')
@login_required
def entity_lineage(entity_id):
    """
    Display full lineage of an entity (derivation chain).
    """
    from app.models.prov_o_models import ProvEntity
    import uuid

    try:
        entity_uuid = uuid.UUID(entity_id)
    except ValueError:
        return "Invalid entity ID", 400

    entity = ProvEntity.query.get_or_404(entity_uuid)
    lineage = provenance_service.get_entity_lineage(entity_uuid)

    return render_template(
        'provenance/lineage.html',
        entity=entity,
        lineage=lineage
    )
