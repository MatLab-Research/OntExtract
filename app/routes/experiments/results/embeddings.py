"""Experiment embedding result routes."""

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

from .helpers import _get_experiment_documents, _get_orchestration_results


@experiments_bp.route('/<int:experiment_id>/results/embeddings')
def experiment_embeddings_results(experiment_id):
    """
    View embeddings information for an experiment.

    Shows:
    - Embedding method used per document
    - Dimension info
    - Chunk counts
    - Period-aware metadata
    """
    experiment = Experiment.query.get_or_404(experiment_id)
    documents, document_ids = _get_experiment_documents(experiment_id)

    if not document_ids:
        return render_template(
            'experiments/results/embeddings.html',
            experiment=experiment,
            documents=[],
            embeddings_info=[],
            total_embeddings=0
        )

    # Build document lookup
    doc_lookup = {doc.id: doc for doc in documents}

    embeddings_info = []
    total_embeddings = 0
    docs_with_embeddings = set()

    # First, determine which documents have embeddings from the orchestration pipeline
    # by checking orchestration_results JSON - these are "Pipeline" triggered
    orchestration_results = _get_orchestration_results(experiment_id)
    pipeline_doc_ids = set()
    for doc_id_str, doc_results in orchestration_results.items():
        if 'period_aware_embedding' in doc_results:
            tool_result = doc_results['period_aware_embedding']
            if tool_result.get('status') == 'executed':
                pipeline_doc_ids.add(int(doc_id_str))

    # 1. Check ProcessingArtifact table directly (primary source)
    # This is where embeddings from both LLM orchestration and manual processing are stored
    artifact_embeddings = ProcessingArtifact.query.filter(
        ProcessingArtifact.document_id.in_(document_ids),
        ProcessingArtifact.artifact_type == 'embedding_vector'
    ).all()

    # Group artifacts by document
    artifacts_by_doc = {}
    for emb in artifact_embeddings:
        if emb.document_id not in artifacts_by_doc:
            artifacts_by_doc[emb.document_id] = []
        artifacts_by_doc[emb.document_id].append(emb)

    for doc_id, artifacts in artifacts_by_doc.items():
        doc = doc_lookup.get(doc_id)
        if not artifacts:
            continue

        # Get metadata from first artifact
        first_artifact = artifacts[0]
        metadata = first_artifact.get_metadata() or {}
        content = first_artifact.get_content() or {}

        # Determine source: if doc_id is in orchestration results, it's from pipeline
        source = 'llm' if doc_id in pipeline_doc_ids else 'manual'

        info = {
            'document_id': doc_id,
            'document_title': doc.title if doc else f"Document {doc_id}",
            'document_uuid': str(doc.uuid) if doc else None,
            'document_year': metadata.get('document_year') or (doc.publication_date.year if doc and doc.publication_date else None),
            'method': metadata.get('method', content.get('method', 'period_aware')),
            'dimensions': metadata.get('dimensions', len(content.get('vector', content.get('embedding', [])))),
            'chunk_count': len(artifacts),
            'model': metadata.get('model', content.get('model', 'unknown')),
            'source': source,
            'created_at': first_artifact.created_at if hasattr(first_artifact, 'created_at') else None,
            # Period-aware metadata
            'period_category': metadata.get('period_category'),
            'selection_reason': metadata.get('selection_reason'),
            'selection_confidence': metadata.get('selection_confidence'),
            'era': metadata.get('era'),
            'handles_archaic': metadata.get('handles_archaic', False),
            'model_description': metadata.get('model_description'),
            'model_full': metadata.get('model_full')
        }
        embeddings_info.append(info)
        total_embeddings += len(artifacts)
        docs_with_embeddings.add(doc_id)

    # 2. Get LLM orchestration results from processing_results JSON (fallback)
    # (reusing orchestration_results from above)
    for doc_id_str, doc_results in orchestration_results.items():
        doc_id = int(doc_id_str)
        if doc_id not in document_ids or doc_id in docs_with_embeddings:
            continue

        doc = doc_lookup.get(doc_id)

        # Check for period_aware_embedding results
        if 'period_aware_embedding' in doc_results:
            tool_result = doc_results['period_aware_embedding']
            if tool_result.get('status') == 'executed':
                # Handle both old format (results.metadata) and new format (metadata directly)
                if 'results' in tool_result:
                    results = tool_result['results']
                    metadata = results.get('metadata', {})
                    data = results.get('data', {})
                else:
                    # New format: metadata is directly on tool_result
                    metadata = tool_result.get('metadata', {})
                    data = {}

                # Data might be a dict (single embedding) or list
                chunk_count = tool_result.get('count', 1)
                if isinstance(data, dict) and data:
                    chunk_count = 1
                elif isinstance(data, list):
                    chunk_count = len(data)

                info = {
                    'document_id': doc_id,
                    'document_title': doc.title if doc else f"Document {doc_id}",
                    'document_uuid': str(doc.uuid) if doc else None,
                    'document_year': metadata.get('document_year') or (doc.publication_date.year if doc and doc.publication_date else None),
                    'method': metadata.get('embedding_type', 'period_aware'),
                    'dimensions': metadata.get('dimensions', data.get('dimensions') if isinstance(data, dict) else 'N/A'),
                    'chunk_count': chunk_count,
                    'model': metadata.get('model', data.get('model') if isinstance(data, dict) else 'unknown'),
                    'source': 'llm',
                    'created_at': None,
                    # Period-aware metadata
                    'period_category': metadata.get('period_category'),
                    'selection_reason': metadata.get('selection_reason'),
                    'selection_confidence': metadata.get('selection_confidence', metadata.get('period_confidence')),
                    'era': metadata.get('era'),
                    'handles_archaic': metadata.get('handles_archaic', False),
                    'model_description': metadata.get('model_description'),
                    'model_full': metadata.get('model_full')
                }
                embeddings_info.append(info)
                total_embeddings += chunk_count
                docs_with_embeddings.add(doc_id)

    # 3. Get embedding artifact groups (older storage format)
    artifact_groups = ProcessingArtifactGroup.query.filter(
        ProcessingArtifactGroup.document_id.in_(document_ids),
        ProcessingArtifactGroup.artifact_type == 'embedding_vector'
    ).all()

    for group in artifact_groups:
        if group.document_id in docs_with_embeddings:
            continue

        doc = doc_lookup.get(group.document_id)
        metadata = group.get_metadata() or {}

        info = {
            'document_id': group.document_id,
            'document_title': doc.title if doc else f"Document {group.document_id}",
            'document_uuid': str(doc.uuid) if doc else None,
            'document_year': metadata.get('document_year') or (doc.publication_date.year if doc and doc.publication_date else None),
            'method': group.method_key or metadata.get('method', 'unknown'),
            'dimensions': metadata.get('dimensions', 'N/A'),
            'chunk_count': metadata.get('chunk_count', group.artifact_count),
            'model': metadata.get('model', 'unknown'),
            'source': 'llm',
            'created_at': group.created_at,
            # Period-aware metadata
            'period_category': metadata.get('period_category'),
            'selection_reason': metadata.get('selection_reason'),
            'selection_confidence': metadata.get('selection_confidence'),
            'era': metadata.get('era'),
            'handles_archaic': metadata.get('handles_archaic', False),
            'model_description': metadata.get('model_description'),
            'model_full': metadata.get('model_full')
        }
        embeddings_info.append(info)
        total_embeddings += info['chunk_count'] or 0
        docs_with_embeddings.add(group.document_id)

    # 4. Check ProcessingJob for manual embeddings
    embedding_jobs = ProcessingJob.query.filter(
        ProcessingJob.document_id.in_(document_ids),
        ProcessingJob.job_type == 'generate_embeddings',
        ProcessingJob.status == 'completed'
    ).all()

    for job in embedding_jobs:
        if job.document_id in docs_with_embeddings:
            continue

        doc = doc_lookup.get(job.document_id)
        result_data = job.get_result_data() or {}

        info = {
            'document_id': job.document_id,
            'document_title': doc.title if doc else f"Document {job.document_id}",
            'document_uuid': str(doc.uuid) if doc else None,
            'document_year': doc.publication_date.year if doc and doc.publication_date else None,
            'method': result_data.get('embedding_method', 'manual'),
            'dimensions': result_data.get('embedding_dimensions', 'N/A'),
            'chunk_count': result_data.get('chunk_count', result_data.get('total_embeddings', 1)),
            'model': result_data.get('model_used', 'unknown'),
            'source': 'manual',
            'created_at': job.completed_at or job.created_at,
            # No period-aware metadata for manual jobs
            'period_category': None,
            'selection_reason': None,
            'selection_confidence': None,
            'era': None,
            'handles_archaic': False,
            'model_description': None,
            'model_full': None
        }
        embeddings_info.append(info)
        total_embeddings += info['chunk_count'] or 0

    # Sort by document year
    embeddings_info.sort(key=lambda e: (e.get('document_year') or 9999, e.get('document_title', '')))

    return render_template(
        'experiments/results/embeddings.html',
        experiment=experiment,
        documents=documents,
        embeddings_info=embeddings_info,
        total_embeddings=total_embeddings
    )
