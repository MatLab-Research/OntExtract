"""Experiment segmentation result routes."""

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


@experiments_bp.route('/<int:experiment_id>/results/segments')
def experiment_segments_results(experiment_id):
    """
    View all segmentation results for an experiment.
    """
    experiment = Experiment.query.get_or_404(experiment_id)
    documents, document_ids = _get_experiment_documents(experiment_id)

    if not document_ids:
        return render_template(
            'experiments/results/segments.html',
            experiment=experiment,
            documents=[],
            segments=[],
            segments_by_document={},
            total_segments=0,
            avg_length=0,
            avg_words=0
        )

    # Build document lookup
    doc_lookup = {doc.id: doc for doc in documents}

    segments = []
    segments_by_document = {}

    def add_segment(segment_data):
        """Helper to add segment and update groupings."""
        segments.append(segment_data)
        doc_id = segment_data['document_id']
        if doc_id not in segments_by_document:
            segments_by_document[doc_id] = {
                'document': doc_lookup.get(doc_id),
                'segments': []
            }
        segments_by_document[doc_id]['segments'].append(segment_data)

    # 1. Get segments from TextSegment table
    text_segments = TextSegment.query.filter(
        TextSegment.document_id.in_(document_ids)
    ).order_by(TextSegment.document_id, TextSegment.segment_number).all()

    for seg in text_segments:
        doc = doc_lookup.get(seg.document_id)
        segment = {
            'id': seg.id,
            'segment_number': seg.segment_number,
            'content': seg.content,
            'word_count': len(seg.content.split()) if seg.content else 0,
            'character_count': len(seg.content) if seg.content else 0,
            'method': seg.segment_type or 'paragraph',
            'source': 'text_segment',
            'document_id': seg.document_id,
            'document_title': doc.title if doc else f"Document {seg.document_id}",
            'document_uuid': str(doc.uuid) if doc else None,
            'document_year': doc.publication_date.year if doc and doc.publication_date else None
        }
        add_segment(segment)

    # Track which documents already have segments
    docs_with_segments = set(segments_by_document.keys())

    # 2. Get segments from ProcessingArtifact (LLM orchestration)
    segment_artifacts = ProcessingArtifact.query.filter(
        ProcessingArtifact.document_id.in_(document_ids),
        ProcessingArtifact.artifact_type == 'text_segment'
    ).order_by(ProcessingArtifact.document_id, ProcessingArtifact.artifact_index).all()

    for artifact in segment_artifacts:
        if artifact.document_id in docs_with_segments:
            continue

        content = artifact.get_content()
        metadata = artifact.get_metadata()
        doc = doc_lookup.get(artifact.document_id)

        # Handle both dict and string content formats
        if isinstance(content, str):
            segment_text = content
        elif isinstance(content, dict):
            segment_text = content.get('text', '')
        else:
            segment_text = ''
        # Get segment type from content dict or fallback to metadata
        segment_type = 'unknown'
        metadata_method = metadata.get('method', 'unknown') if isinstance(metadata, dict) else 'unknown'
        if isinstance(content, dict):
            segment_type = content.get('segment_type', metadata_method)
        else:
            segment_type = metadata_method

        # Calculate word count
        default_word_count = len(segment_text.split()) if segment_text else 0
        word_count = metadata.get('word_count', default_word_count) if isinstance(metadata, dict) else default_word_count

        segment = {
            'id': f"artifact_{artifact.id}",
            'segment_number': artifact.artifact_index + 1,
            'content': segment_text,
            'word_count': word_count,
            'character_count': len(segment_text) if segment_text else 0,
            'method': segment_type,
            'source': 'artifact',
            'document_id': artifact.document_id,
            'document_title': doc.title if doc else f"Document {artifact.document_id}",
            'document_uuid': str(doc.uuid) if doc else None,
            'document_year': doc.publication_date.year if doc and doc.publication_date else None
        }
        add_segment(segment)

    # Calculate statistics
    total_segments = len(segments)
    avg_length = sum(s['character_count'] for s in segments) / total_segments if total_segments else 0
    avg_words = sum(s['word_count'] for s in segments) / total_segments if total_segments else 0

    return render_template(
        'experiments/results/segments.html',
        experiment=experiment,
        documents=documents,
        segments=segments,
        segments_by_document=segments_by_document,
        total_segments=total_segments,
        avg_length=avg_length,
        avg_words=avg_words
    )
