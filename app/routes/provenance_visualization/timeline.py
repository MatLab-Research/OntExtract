"""PROV-O timeline pages."""

from flask import render_template, request
from flask_login import login_required

from app.models.experiment import Experiment
from app.services.provenance_service import provenance_service

from . import bp


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
    term_id = request.args.get('term_id')  # UUID string, not int
    activity_type = request.args.get('activity_type')
    limit = request.args.get('limit', 50, type=int)
    include_deleted = request.args.get('include_deleted', '').lower() == 'true'

    # Convert document_uuid to document_id if provided
    if document_uuid and not document_id:
        from app.models.document import Document
        from uuid import UUID
        doc = Document.query.filter_by(uuid=UUID(document_uuid)).first()
        if doc:
            document_id = doc.id

    # Get all document IDs in the family if a document is selected
    # This allows showing provenance for all versions of a document
    from app.models.document import Document
    document_ids = None
    selected_document = None
    if document_id:
        selected_document = Document.query.get(document_id)
        if selected_document:
            # Get all versions in this document family
            all_versions = selected_document.get_all_versions()
            document_ids = [v.id for v in all_versions]

    # Get timeline data - pass document_ids to include all versions
    timeline_data = provenance_service.get_timeline(
        experiment_id=experiment_id,
        document_ids=document_ids,
        activity_type=activity_type,
        term_id=term_id,
        limit=limit,
        include_invalidated=include_deleted
    )

    # Get experiments for filter dropdown
    experiments = Experiment.query.order_by(Experiment.created_at.desc()).all()

    # Get documents for filter dropdown - only show original (v1) documents
    documents = Document.query.filter_by(version_type='original').order_by(Document.created_at.desc()).all()

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
        'orchestration_run',
        'semantic_event_creation',
        'semantic_event_update',
        'semantic_event_deletion'
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
        selected_term_id=term_id,
        version_count=len(document_ids) if document_ids else 0,
        include_deleted=include_deleted
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
