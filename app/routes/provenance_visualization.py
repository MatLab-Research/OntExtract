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
    - Document
    - Term
    - Activity type
    - Date range
    """
    # Get filter parameters
    experiment_id = request.args.get('experiment_id', type=int)
    document_id = request.args.get('document_id', type=int)
    document_uuid = request.args.get('document_uuid')
    term_id = request.args.get('term_id', type=int)
    activity_type = request.args.get('activity_type')
    limit = request.args.get('limit', 50, type=int)

    # Convert document_uuid to document_id if provided
    if document_uuid and not document_id:
        from app.models.document import Document
        from uuid import UUID
        doc = Document.query.filter_by(uuid=UUID(document_uuid)).first()
        if doc:
            document_id = doc.id

    # Get timeline data
    timeline_data = provenance_service.get_timeline(
        experiment_id=experiment_id,
        document_id=document_id,
        activity_type=activity_type,
        term_id=term_id,
        limit=limit
    )

    # Get experiments for filter dropdown
    experiments = Experiment.query.order_by(Experiment.created_at.desc()).all()

    # Get documents for filter dropdown
    from app.models.document import Document
    documents = Document.query.order_by(Document.created_at.desc()).all()

    # Get terms for filter dropdown
    from app.models.term import Term
    terms = Term.query.order_by(Term.term_text).all()

    # Get available activity types
    activity_types = [
        'term_creation',
        'term_update',
        'document_upload',
        'text_extraction',
        'metadata_extraction_pdf',
        'metadata_extraction',
        'document_save',
        'metadata_update',
        'metadata_field_update',
        'document_segmentation',
        'embedding_generation',
        'entity_extraction',
        'temporal_extraction',
        'definition_extraction',
        'experiment_creation',
        'experiment_document_processing',
        'tool_execution',
        'orchestration_run'
    ]

    return render_template(
        'provenance/timeline.html',
        timeline=timeline_data,
        experiments=experiments,
        documents=documents,
        terms=terms,
        activity_types=activity_types,
        selected_experiment_id=experiment_id,
        selected_document_id=document_id,
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


# ========================================================================
# ADMIN DELETE OPERATIONS
# ========================================================================

@bp.route('/activity/<activity_id>', methods=['DELETE'])
@login_required
def delete_activity(activity_id):
    """Delete a single provenance activity and all related records (admin only)."""
    if not current_user.is_admin:
        return jsonify({'error': 'Admin access required'}), 403

    from app.models.prov_o_models import ProvActivity, ProvEntity, ProvRelationship
    from app import db
    import uuid

    try:
        activity_uuid = uuid.UUID(activity_id)
    except ValueError:
        return jsonify({'error': 'Invalid activity ID'}), 400

    try:
        activity = ProvActivity.query.get(activity_uuid)
        if not activity:
            return jsonify({'error': 'Activity not found'}), 404

        # First, delete entities that were generated by this activity
        # (they violate the must_have_generation_provenance constraint if activity is deleted)
        generated_entities = ProvEntity.query.filter_by(wasgeneratedby=activity_uuid).all()
        entities_deleted = len(generated_entities)

        for entity in generated_entities:
            db.session.delete(entity)

        # Delete relationships where this activity is subject or object
        relationships_deleted = ProvRelationship.query.filter(
            db.or_(
                db.and_(ProvRelationship.subject_type == 'activity', ProvRelationship.subject_id == activity_uuid),
                db.and_(ProvRelationship.object_type == 'activity', ProvRelationship.object_id == activity_uuid)
            )
        ).delete(synchronize_session=False)

        # Finally, delete the activity itself
        db.session.delete(activity)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Activity {activity_id} deleted along with {entities_deleted} generated entities and {relationships_deleted} relationships',
            'deleted_count': 1 + entities_deleted + relationships_deleted
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/delete-all', methods=['DELETE'])
@login_required
def delete_all_provenance():
    """Delete ALL provenance records (admin only, use with extreme caution)."""
    if not current_user.is_admin:
        return jsonify({'error': 'Admin access required'}), 403

    from app.models.prov_o_models import ProvActivity, ProvEntity, ProvAgent, ProvRelationship
    from app import db

    try:
        # Delete all relationships first
        relationships_count = ProvRelationship.query.delete()

        # Delete all entities
        entities_count = ProvEntity.query.delete()

        # Delete all activities
        activities_count = ProvActivity.query.delete()

        # Don't delete agents - keep them for reuse
        agents_count = 0

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'All provenance records deleted',
            'activities_deleted': activities_count,
            'entities_deleted': entities_count,
            'agents_deleted': agents_count,
            'relationships_deleted': relationships_count
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
