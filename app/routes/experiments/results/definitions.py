"""Experiment definition result routes."""

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


@experiments_bp.route('/<int:experiment_id>/results/definitions')
def experiment_definitions_results(experiment_id):
    """
    View all definition extraction results for an experiment.

    All definition data is stored in ProcessingArtifact table (artifact_type='term_definition'),
    regardless of whether processing was triggered via LLM orchestration or manual processing.
    """
    experiment = Experiment.query.get_or_404(experiment_id)
    documents, document_ids = _get_experiment_documents(experiment_id)

    if not document_ids:
        return render_template(
            'experiments/results/definitions.html',
            experiment=experiment,
            documents=[],
            definitions=[],
            definitions_by_document={},
            total_definitions=0,
            auto_count=0,
            manual_count=0
        )

    # Build document lookup
    doc_lookup = {doc.id: doc for doc in documents}

    definitions = []
    definitions_by_document = {}
    auto_count = 0  # Count of automated extractions (pattern matching, etc.)

    # Get all definitions from ProcessingArtifact table
    # This is the unified storage for both orchestrated and manual processing
    definition_artifacts = ProcessingArtifact.query.filter(
        ProcessingArtifact.document_id.in_(document_ids),
        ProcessingArtifact.artifact_type == 'term_definition'
    ).order_by(ProcessingArtifact.document_id, ProcessingArtifact.artifact_index).all()

    for artifact in definition_artifacts:
        content = artifact.get_content()
        metadata = artifact.get_metadata()

        doc = doc_lookup.get(artifact.document_id)
        doc_title = doc.title if doc else f"Document {artifact.document_id}"

        # Handle both dict and string content
        if isinstance(content, str):
            term = ''
            definition_text = content
            pattern = 'unknown'
            confidence = 0
            sentence = ''
        else:
            term = content.get('term', '')
            definition_text = content.get('definition', '')
            pattern = content.get('pattern', 'unknown')
            confidence = content.get('confidence', 0)
            sentence = content.get('sentence', '')

        # Get method from metadata
        artifact_method = metadata.get('method', 'pattern_matching') if isinstance(metadata, dict) else 'pattern_matching'

        # Determine source label based on method
        if 'zero_shot' in artifact_method.lower() or 'zeroshot' in artifact_method.lower():
            source_label = 'zeroshot'
        else:
            source_label = 'pattern'

        definition = {
            'id': f"artifact_{artifact.id}",
            'term': term,
            'definition': definition_text,
            'pattern': pattern,
            'confidence': confidence,
            'sentence': sentence,
            'start_char': metadata.get('start_char') if isinstance(metadata, dict) else None,
            'end_char': metadata.get('end_char') if isinstance(metadata, dict) else None,
            'method': artifact_method,
            'source': source_label,
            'document_id': artifact.document_id,
            'document_title': doc_title,
            'document_uuid': str(doc.uuid) if doc else None,
            'document_year': doc.publication_date.year if doc and doc.publication_date else None
        }
        definitions.append(definition)
        auto_count += 1

        if artifact.document_id not in definitions_by_document:
            definitions_by_document[artifact.document_id] = {
                'document': doc,
                'definitions': []
            }
        definitions_by_document[artifact.document_id]['definitions'].append(definition)

    # Also check ProcessingJob for older manual definitions (backward compatibility)
    manual_jobs = ProcessingJob.query.filter(
        ProcessingJob.document_id.in_(document_ids),
        ProcessingJob.job_type == 'definition_extraction',
        ProcessingJob.status == 'completed'
    ).all()

    manual_count = 0
    for job in manual_jobs:
        result_data = job.get_result_data()
        if result_data and 'definitions' in result_data:
            doc = doc_lookup.get(job.document_id)
            doc_title = doc.title if doc else f"Document {job.document_id}"

            for idx, defn in enumerate(result_data['definitions']):
                definition = {
                    'id': f"job_{job.id}_{idx}",
                    'term': defn.get('term', ''),
                    'definition': defn.get('definition', ''),
                    'pattern': defn.get('pattern', 'unknown'),
                    'confidence': defn.get('confidence', 0),
                    'sentence': defn.get('sentence', ''),
                    'start_char': defn.get('start_char'),
                    'end_char': defn.get('end_char'),
                    'method': defn.get('method', 'manual'),
                    'source': 'manual',
                    'document_id': job.document_id,
                    'document_title': doc_title,
                    'document_uuid': str(doc.uuid) if doc else None,
                    'document_year': doc.publication_date.year if doc and doc.publication_date else None
                }
                definitions.append(definition)
                manual_count += 1

                if job.document_id not in definitions_by_document:
                    definitions_by_document[job.document_id] = {
                        'document': doc,
                        'definitions': []
                    }
                definitions_by_document[job.document_id]['definitions'].append(definition)

    # Sort definitions by document year (oldest first) then by term
    definitions.sort(key=lambda d: (d.get('document_year') or 9999, d.get('term', '').lower()))

    return render_template(
        'experiments/results/definitions.html',
        experiment=experiment,
        documents=documents,
        definitions=definitions,
        definitions_by_document=definitions_by_document,
        total_definitions=len(definitions),
        auto_count=auto_count,
        manual_count=manual_count
    )
