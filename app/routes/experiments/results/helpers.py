"""Shared experiment result document and orchestration queries."""

from flask import render_template
from app.models import Experiment, Document
from app.models.experiment_document import ExperimentDocument
from app.models.experiment_processing import (
    ProcessingArtifact,
    ExperimentDocumentProcessing
)
from app.models.experiment_orchestration_run import ExperimentOrchestrationRun
from app.models.processing_artifact_group import ProcessingArtifactGroup
from app.models.processing_job import ProcessingJob
from app.models.text_segment import TextSegment
from app.models.extracted_entity import ExtractedEntity
from app import db
import logging
from .. import experiments_bp


def _get_experiment_documents(experiment_id):
    """
    Get all documents for an experiment with their IDs.

    Groups documents by root and returns the latest version for each.
    This matches the logic in crud.view() and pipeline_service.get_pipeline_overview().

    Version chain: v1 (original) -> v2 (experimental, used in experiments)
    """
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
    documents = []
    document_ids = []
    for root_id, family_members in doc_families.items():
        # Sort by version_number (desc) and pick the first one
        family_members.sort(key=lambda x: x[1].version_number or 0, reverse=True)
        exp_doc, doc = family_members[0]
        documents.append(doc)
        document_ids.append(doc.id)

    return documents, document_ids

def _get_orchestration_results(experiment_id):
    """Get the most recent orchestration run results for an experiment."""
    run = ExperimentOrchestrationRun.query.filter_by(
        experiment_id=experiment_id
    ).order_by(ExperimentOrchestrationRun.started_at.desc()).first()

    if run and run.processing_results:
        return run.processing_results
    return {}
