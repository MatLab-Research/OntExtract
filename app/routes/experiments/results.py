"""
Experiments Results Routes

Unified experiment-centric results pages for viewing processing outputs.
Combines data from both LLM orchestration and manual processing paths.

Routes:
- GET /experiments/<id>/results/definitions - View all definitions
- GET /experiments/<id>/results/entities - View all entities
- GET /experiments/<id>/results/temporal - View all temporal expressions
- GET /experiments/<id>/results/embeddings - View embeddings info
- GET /experiments/<id>/results/segments - View all segments
"""

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

from . import experiments_bp

logger = logging.getLogger(__name__)


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
            if tool_result.get('status') == 'executed' and 'results' in tool_result:
                results = tool_result['results']
                metadata = results.get('metadata', {})
                data = results.get('data', {})

                # Data might be a dict (single embedding) or list
                chunk_count = 1 if isinstance(data, dict) else len(data) if data else 1

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
