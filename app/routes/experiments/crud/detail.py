"""Experiment detail and summary result pages."""

from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import current_user
from app.utils.auth_decorators import api_require_login_for_write, write_login_required
from app import db
from app.models import Document, Experiment
from app.services.text_processing import TextProcessingService
from app.services.experiment_domain_comparison import DomainComparisonService
from app.services.experiment_service import get_experiment_service
from app.dto.experiment_dto import (
    CreateExperimentDTO,
    UpdateExperimentDTO,
    ExperimentResponseDTO,
    ExperimentListItemDTO,
    ExperimentDetailDTO
)
from app.services.base_service import ServiceError, ValidationError
from pydantic import ValidationError as PydanticValidationError
from datetime import datetime
import json
from typing import Optional
import logging
from .. import experiments_bp


@experiments_bp.route('/<int:experiment_id>')
def view(experiment_id):
    """View experiment details - Enhanced dashboard view"""
    experiment = Experiment.query.filter_by(id=experiment_id).first_or_404()

    # Get most recent orchestration run for this experiment
    from app.models import ExperimentOrchestrationRun
    from sqlalchemy import func

    recent_orchestration = ExperimentOrchestrationRun.query.filter_by(
        experiment_id=experiment_id
    ).order_by(ExperimentOrchestrationRun.started_at.desc()).first()

    # --- Processing Summary ---
    # Use the same data sources as document_pipeline: ExperimentDocumentProcessing & DocumentProcessingIndex
    from app.models.experiment_processing import ExperimentDocumentProcessing, DocumentProcessingIndex, ProcessingArtifact
    from app.models import ExperimentDocument

    # Get actual artifact counts from processing_artifacts table
    # This gives us real totals, not just document counts
    artifact_counts = db.session.query(
        ProcessingArtifact.artifact_type,
        func.count(ProcessingArtifact.id)
    ).join(
        Document, ProcessingArtifact.document_id == Document.id
    ).join(
        ExperimentDocument, ExperimentDocument.document_id == Document.id
    ).filter(
        ExperimentDocument.experiment_id == experiment_id
    ).group_by(ProcessingArtifact.artifact_type).all()

    # Convert to processing_summary dict with display-friendly names
    processing_summary = {}
    artifact_type_map = {
        'extracted_entity': 'entities',
        'term_definition': 'definitions',
        'temporal_marker': 'temporal',
        'embedding_vector': 'embeddings'
    }
    for artifact_type, count in artifact_counts:
        display_name = artifact_type_map.get(artifact_type, artifact_type)
        processing_summary[display_name] = count

    # Get experiment documents and group by root to find latest versions
    # This matches the logic in pipeline_service.get_pipeline_overview()
    exp_docs = ExperimentDocument.query.filter_by(experiment_id=experiment_id).all()

    # Group documents by root to show only latest version
    doc_families = {}
    for exp_doc in exp_docs:
        doc = exp_doc.document
        # Get root document ID (either the document itself or its source)
        root_id = doc.source_document_id if doc.source_document_id else doc.id
        if root_id not in doc_families:
            doc_families[root_id] = []
        doc_families[root_id].append((exp_doc, doc))

    # For each family, select only the latest version
    latest_exp_docs = []
    for root_id, family_members in doc_families.items():
        # Sort by version_number (desc) and pick the first one
        family_members.sort(key=lambda x: x[1].version_number or 0, reverse=True)
        latest_exp_docs.append(family_members[0])  # (exp_doc, doc) tuple

    # --- Document Details with Versions and Cross-Experiment Usage ---
    documents_enhanced = []
    for exp_doc, doc in latest_exp_docs:
        # Count how many OTHER experiments use the root document
        root_doc = doc.source_document if doc.source_document_id else doc
        other_exp_count = root_doc.experiments.count() - 1  # Exclude current experiment

        # Collect processing operations from both systems
        operations_list = []

        # 1. Check manual processing operations (from process_document page buttons)
        manual_ops = ExperimentDocumentProcessing.query.filter_by(
            experiment_document_id=exp_doc.id,
            status='completed'
        ).all()

        for op in manual_ops:
            operations_list.append({
                'type': op.processing_type,
                'method': op.processing_method,
                'source': 'manual'
            })

        # 2. Check DocumentProcessingIndex (experiment-specific processing)
        index_entries = DocumentProcessingIndex.query.filter_by(
            document_id=doc.id,
            experiment_id=experiment_id,
            status='completed'
        ).all()

        for entry in index_entries:
            operations_list.append({
                'type': entry.processing_type,
                'method': entry.processing_method,
                'source': 'experiment'
            })

        # Note: We no longer check orchestration_run.processing_results JSON
        # because LLM orchestration already creates ExperimentDocumentProcessing
        # records which are captured in section 1 above.

        # Deduplicate by (type, method)
        seen = set()
        unique_operations = []
        for op in operations_list:
            key = (op['type'], op['method'])
            if key not in seen:
                seen.add(key)
                unique_operations.append(op)

        # Group by artifact type for template display
        doc_processing_by_type = {}
        for op in unique_operations:
            artifact_type = op['type']
            if artifact_type not in doc_processing_by_type:
                doc_processing_by_type[artifact_type] = []
            doc_processing_by_type[artifact_type].append({
                'method_key': op['method'],
                'source': op['source']
            })
            # Note: processing_summary is now calculated from actual artifact counts above

        documents_enhanced.append({
            'document': doc,
            'other_experiments_count': other_exp_count,
            'processing_by_type': doc_processing_by_type,
            'processing_count': len(unique_operations)
        })

    # Count total processing operations across all documents
    total_processing_ops = sum(processing_summary.values())

    # --- Temporal Periods (for temporal_evolution experiments) ---
    temporal_data = None
    if experiment.experiment_type == 'temporal_evolution':
        try:
            from app.services.temporal_service import get_temporal_service
            temporal_service = get_temporal_service()
            temporal_data = temporal_service.get_temporal_ui_data(experiment_id)
        except Exception as e:
            logger.warning(f"Failed to get temporal data for experiment {experiment_id}: {e}")
            temporal_data = None

    return render_template(
        'experiments/view.html',
        experiment=experiment,
        recent_orchestration=recent_orchestration,
        processing_summary=processing_summary,
        total_processing_ops=total_processing_ops,
        documents_enhanced=documents_enhanced,
        temporal_data=temporal_data
    )

@experiments_bp.route('/<int:experiment_id>/results')
def results(experiment_id):
    """
    View experiment results.

    Smart routing:
    - If experiment has a completed LLM orchestration run → redirect to LLM results
    - Otherwise → show static results page with processing summary
    """
    experiment = Experiment.query.filter_by(id=experiment_id).first_or_404()

    if experiment.status != 'completed':
        flash('Experiment has not been completed yet', 'warning')
        return redirect(url_for('experiments.view', experiment_id=experiment_id))

    # Check for completed LLM orchestration run
    from app.models.experiment_orchestration_run import ExperimentOrchestrationRun
    orchestration_run = ExperimentOrchestrationRun.query.filter_by(
        experiment_id=experiment_id,
        status='completed'
    ).order_by(ExperimentOrchestrationRun.completed_at.desc()).first()

    if orchestration_run:
        # Redirect to LLM results page
        return redirect(url_for('experiments.llm_orchestration_results',
                               experiment_id=experiment_id,
                               run_id=orchestration_run.id))

    # Manual experiment - show static results page
    # Get processing statistics
    from app.models.processing_artifact_group import ProcessingArtifactGroup
    from app.models.document_index import DocumentProcessingIndex
    from sqlalchemy import func

    # Get processing counts by type from ProcessingArtifactGroup
    artifact_counts = db.session.query(
        ProcessingArtifactGroup.artifact_type,
        func.count(ProcessingArtifactGroup.id)
    ).filter_by(experiment_id=experiment_id).group_by(
        ProcessingArtifactGroup.artifact_type
    ).all()

    # Get processing counts from DocumentProcessingIndex
    index_counts = db.session.query(
        DocumentProcessingIndex.processing_type,
        func.count(DocumentProcessingIndex.id)
    ).join(Document).filter(
        Document.experiment_id == experiment_id
    ).group_by(DocumentProcessingIndex.processing_type).all()

    # Merge counts
    processing_summary = {}
    for artifact_type, count in artifact_counts:
        processing_summary[artifact_type] = processing_summary.get(artifact_type, 0) + count
    for proc_type, count in index_counts:
        processing_summary[proc_type] = processing_summary.get(proc_type, 0) + count

    total_operations = sum(processing_summary.values())

    # Get per-document processing info
    documents_with_processing = []
    for doc in experiment.documents:
        doc_artifacts = ProcessingArtifactGroup.query.filter_by(
            experiment_id=experiment_id,
            document_id=doc.id
        ).all()
        doc_indexes = DocumentProcessingIndex.query.filter_by(document_id=doc.id).all()

        doc_processing = {}
        for artifact in doc_artifacts:
            doc_processing[artifact.artifact_type] = doc_processing.get(artifact.artifact_type, 0) + 1
        for idx in doc_indexes:
            doc_processing[idx.processing_type] = doc_processing.get(idx.processing_type, 0) + 1

        documents_with_processing.append({
            'document': doc,
            'processing': doc_processing,
            'total_ops': sum(doc_processing.values())
        })

    # Parse configuration JSON for template convenience
    config_data = {}
    if experiment.configuration:
        try:
            config_data = json.loads(experiment.configuration)
        except Exception:
            config_data = {}

    return render_template('experiments/results.html',
                         experiment=experiment,
                         processing_summary=processing_summary,
                         total_operations=total_operations,
                         documents_with_processing=documents_with_processing,
                         config_data=config_data)
