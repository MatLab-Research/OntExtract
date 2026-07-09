"""Experiment temporal result routes."""

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

from .helpers import _get_experiment_documents


@experiments_bp.route('/<int:experiment_id>/results/temporal')
def experiment_temporal_results(experiment_id):
    """
    View all temporal extraction results for an experiment.

    All temporal data is stored in ProcessingArtifact table (artifact_type='temporal_marker'),
    regardless of whether processing was triggered via LLM orchestration or manual processing.
    """
    experiment = Experiment.query.get_or_404(experiment_id)
    documents, document_ids = _get_experiment_documents(experiment_id)

    if not document_ids:
        return render_template(
            'experiments/results/temporal.html',
            experiment=experiment,
            documents=[],
            temporal_expressions=[],
            expressions_by_type={},
            expressions_by_document={},
            total_expressions=0
        )

    # Build document lookup
    doc_lookup = {doc.id: doc for doc in documents}

    temporal_expressions = []
    expressions_by_type = {}
    expressions_by_document = {}

    def add_expression(expr_data):
        """Helper to add expression and update groupings."""
        temporal_expressions.append(expr_data)
        expr_type = expr_data['type']
        if expr_type not in expressions_by_type:
            expressions_by_type[expr_type] = []
        expressions_by_type[expr_type].append(expr_data)

        doc_id = expr_data['document_id']
        if doc_id not in expressions_by_document:
            expressions_by_document[doc_id] = {
                'document': doc_lookup.get(doc_id),
                'expressions': []
            }
        expressions_by_document[doc_id]['expressions'].append(expr_data)

    # Get all temporal expressions from ProcessingArtifact table
    # This is the unified storage for both orchestrated and manual processing
    temporal_artifacts = ProcessingArtifact.query.filter(
        ProcessingArtifact.document_id.in_(document_ids),
        ProcessingArtifact.artifact_type == 'temporal_marker'
    ).order_by(ProcessingArtifact.document_id, ProcessingArtifact.artifact_index).all()

    for artifact in temporal_artifacts:
        content = artifact.get_content()
        metadata = artifact.get_metadata()
        doc = doc_lookup.get(artifact.document_id)

        # Handle both dict and string content
        if isinstance(content, str):
            expr_text = content
            expr_type = 'UNKNOWN'
            normalized = None
            confidence = 0.75
        else:
            expr_text = content.get('text', '')
            expr_type = content.get('type', 'UNKNOWN')
            normalized = content.get('normalized')
            confidence = content.get('confidence', 0.75)

        # Get position from content first, fall back to metadata
        start_pos = content.get('start') if isinstance(content, dict) else None
        end_pos = content.get('end') if isinstance(content, dict) else None
        if start_pos is None and isinstance(metadata, dict):
            start_pos = metadata.get('start_char')
            end_pos = metadata.get('end_char')

        expression = {
            'id': f"artifact_{artifact.id}",
            'text': expr_text,
            'type': expr_type,
            'normalized': normalized,
            'start_position': start_pos,
            'end_position': end_pos,
            'confidence': confidence,
            'context': content.get('context', '') if isinstance(content, dict) else '',
            'method': metadata.get('method', 'spacy_ner_plus_regex') if isinstance(metadata, dict) else 'spacy_ner_plus_regex',
            'source': 'spacy',
            'document_id': artifact.document_id,
            'document_title': doc.title if doc else f"Document {artifact.document_id}",
            'document_uuid': str(doc.uuid) if doc else None,
            'document_year': doc.publication_date.year if doc and doc.publication_date else None
        }
        add_expression(expression)

    # Sort expressions by document year then by position
    temporal_expressions.sort(key=lambda e: (
        e.get('document_year') or 9999,
        e.get('start_position') or 0
    ))

    return render_template(
        'experiments/results/temporal.html',
        experiment=experiment,
        documents=documents,
        temporal_expressions=temporal_expressions,
        expressions_by_type=expressions_by_type,
        expressions_by_document=expressions_by_document,
        total_expressions=len(temporal_expressions)
    )
