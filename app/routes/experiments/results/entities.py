"""Experiment entity result routes."""

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


@experiments_bp.route('/<int:experiment_id>/results/entities')
def experiment_entities_results(experiment_id):
    """
    View all entity extraction results for an experiment.

    All entity data is stored in ProcessingArtifact table (artifact_type='extracted_entity'),
    regardless of whether processing was triggered via LLM orchestration or manual processing.
    """
    experiment = Experiment.query.get_or_404(experiment_id)
    documents, document_ids = _get_experiment_documents(experiment_id)

    if not document_ids:
        return render_template(
            'experiments/results/entities.html',
            experiment=experiment,
            documents=[],
            entities=[],
            entities_by_type={},
            entities_by_document={},
            total_entities=0
        )

    # Build document lookup
    doc_lookup = {doc.id: doc for doc in documents}

    entities = []
    entities_by_type = {}
    entities_by_document = {}

    def add_entity(entity_data):
        """Helper to add entity and update groupings."""
        entities.append(entity_data)
        entity_type = entity_data['entity_type']
        if entity_type not in entities_by_type:
            entities_by_type[entity_type] = []
        entities_by_type[entity_type].append(entity_data)

        doc_id = entity_data['document_id']
        if doc_id not in entities_by_document:
            entities_by_document[doc_id] = {
                'document': doc_lookup.get(doc_id),
                'entities': []
            }
        entities_by_document[doc_id]['entities'].append(entity_data)

    # Get all entities from ProcessingArtifact table
    # This is the unified storage for both orchestrated and manual processing
    entity_artifacts = ProcessingArtifact.query.filter(
        ProcessingArtifact.document_id.in_(document_ids),
        ProcessingArtifact.artifact_type == 'extracted_entity'
    ).order_by(ProcessingArtifact.document_id, ProcessingArtifact.artifact_index).all()

    for artifact in entity_artifacts:
        content = artifact.get_content()
        metadata = artifact.get_metadata()
        doc = doc_lookup.get(artifact.document_id)

        # Handle both dict and string content
        if isinstance(content, str):
            entity_text = content
            entity_type = 'UNKNOWN'
        else:
            entity_text = content.get('entity', content.get('text', ''))
            # spaCy stores type in 'type' key
            entity_type = content.get('type', content.get('entity_type', content.get('label', 'UNKNOWN')))

        entity = {
            'id': f"artifact_{artifact.id}",
            'text': entity_text,
            'entity_type': entity_type,
            'start_position': content.get('start') if isinstance(content, dict) else None,
            'end_position': content.get('end') if isinstance(content, dict) else None,
            'confidence': content.get('confidence', 0.85) if isinstance(content, dict) else 0.85,
            'context': content.get('context', '') if isinstance(content, dict) else '',
            'source': 'spacy',
            'document_id': artifact.document_id,
            'document_title': doc.title if doc else f"Document {artifact.document_id}",
            'document_uuid': str(doc.uuid) if doc else None,
            'document_year': doc.publication_date.year if doc and doc.publication_date else None
        }
        add_entity(entity)

    # Also check ExtractedEntity table for older processing (backward compatibility)
    entity_jobs = ProcessingJob.query.filter(
        ProcessingJob.document_id.in_(document_ids),
        ProcessingJob.job_type == 'entity_extraction'
    ).all()

    job_ids = [job.id for job in entity_jobs]
    if job_ids:
        old_entities = ExtractedEntity.query.filter(
            ExtractedEntity.processing_job_id.in_(job_ids)
        ).all()

        for ent in old_entities:
            job = next((j for j in entity_jobs if j.id == ent.processing_job_id), None)
            if not job:
                continue

            doc = doc_lookup.get(job.document_id)
            entity = {
                'id': f"old_{ent.id}",
                'text': ent.entity_text,
                'entity_type': ent.entity_type or 'UNKNOWN',
                'start_position': ent.start_position,
                'end_position': ent.end_position,
                'confidence': ent.confidence_score or 0,
                'context': '',
                'source': 'manual',
                'document_id': job.document_id,
                'document_title': doc.title if doc else f"Document {job.document_id}",
                'document_uuid': str(doc.uuid) if doc else None,
                'document_year': doc.publication_date.year if doc and doc.publication_date else None
            }
            add_entity(entity)

    # Sort entities by document year then by text
    entities.sort(key=lambda e: (e.get('document_year') or 9999, e.get('text', '').lower()))

    return render_template(
        'experiments/results/entities.html',
        experiment=experiment,
        documents=documents,
        entities=entities,
        entities_by_type=entities_by_type,
        entities_by_document=entities_by_document,
        total_entities=len(entities)
    )
