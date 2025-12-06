"""
Experiments Results Routes

Unified experiment-centric results pages for viewing processing outputs.
Combines data from both LLM orchestration and manual processing paths.

Routes:
- GET /experiments/<id>/results/definitions - View all definitions
- GET /experiments/<id>/results/entities - View all entities
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

    Documents in experiments are the experimental versions (v2) which store
    processing artifacts directly. No additional version traversal needed.

    Version chain: v1 (original) -> v2 (experimental, used in experiments)
    """
    exp_docs = ExperimentDocument.query.filter_by(experiment_id=experiment_id).all()
    document_ids = [ed.document_id for ed in exp_docs]

    documents = Document.query.filter(Document.id.in_(document_ids)).all() if document_ids else []
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

    Combines data from:
    - ExperimentOrchestrationRun.processing_results (LLM orchestration)
    - ProcessingArtifact (if used)
    - ProcessingJob (manual processing)
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
    auto_count = 0  # Count of automated extractions (DeftEval, pattern, spaCy)

    # 1. Get LLM orchestration results from processing_results JSON
    orchestration_results = _get_orchestration_results(experiment_id)
    for doc_id_str, doc_results in orchestration_results.items():
        doc_id = int(doc_id_str)
        if doc_id not in document_ids:
            continue

        doc = doc_lookup.get(doc_id)
        doc_title = doc.title if doc else f"Document {doc_id}"
        doc_uuid = str(doc.uuid) if doc else None
        doc_year = doc.publication_date.year if doc and doc.publication_date else None

        # Check for extract_definitions results
        if 'extract_definitions' in doc_results:
            tool_result = doc_results['extract_definitions']
            if tool_result.get('status') == 'executed' and 'results' in tool_result:
                results = tool_result['results']
                data = results.get('data', [])
                # Get actual extraction method from metadata
                # Method is typically: "zero_shot_filtering+pattern_matching+dependency_parsing"
                extraction_metadata = results.get('metadata', {})
                extraction_method = extraction_metadata.get('method', 'pattern_matching')
                classifier_used = extraction_metadata.get('classifier_used', False)
                classifier_model = extraction_metadata.get('classifier_model', '')

                # Determine source label based on actual method
                if classifier_used and classifier_model:
                    # Zero-shot classification was used to filter sentences
                    source_label = 'zeroshot'
                else:
                    source_label = 'pattern'

                for idx, defn in enumerate(data):
                    definition = {
                        'id': f"auto_{doc_id}_{idx}",
                        'term': defn.get('term', ''),
                        'definition': defn.get('definition', ''),
                        'pattern': defn.get('pattern', 'unknown'),
                        'confidence': defn.get('confidence', 0),
                        'sentence': defn.get('sentence', ''),
                        'start_char': defn.get('start'),
                        'end_char': defn.get('end'),
                        'method': extraction_method,
                        'source': source_label,
                        'document_id': doc_id,
                        'document_title': doc_title,
                        'document_uuid': doc_uuid,
                        'document_year': doc_year
                    }
                    definitions.append(definition)
                    auto_count += 1

                    # Group by document
                    if doc_id not in definitions_by_document:
                        definitions_by_document[doc_id] = {
                            'document': doc,
                            'definitions': []
                        }
                    definitions_by_document[doc_id]['definitions'].append(definition)

    # 2. Get from ProcessingArtifact (if any exist)
    llm_artifacts = ProcessingArtifact.query.filter(
        ProcessingArtifact.document_id.in_(document_ids),
        ProcessingArtifact.artifact_type == 'definition'
    ).order_by(ProcessingArtifact.document_id, ProcessingArtifact.artifact_index).all()

    for artifact in llm_artifacts:
        content = artifact.get_content()
        metadata = artifact.get_metadata()

        doc = doc_lookup.get(artifact.document_id)
        doc_title = doc.title if doc else f"Document {artifact.document_id}"

        # Determine source from artifact metadata
        artifact_method = metadata.get('method', 'pattern_matching')
        if 'zero_shot' in artifact_method.lower() or 'zeroshot' in artifact_method.lower():
            artifact_source = 'zeroshot'
        else:
            artifact_source = 'pattern'

        definition = {
            'id': f"artifact_{artifact.id}",
            'term': content.get('term', ''),
            'definition': content.get('definition', ''),
            'pattern': content.get('pattern', 'unknown'),
            'confidence': content.get('confidence', 0),
            'sentence': content.get('sentence', ''),
            'start_char': metadata.get('start_char'),
            'end_char': metadata.get('end_char'),
            'method': artifact_method,
            'source': artifact_source,
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

    # 3. Get manual processing definitions from ProcessingJob
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

    Combines data from:
    - ExperimentOrchestrationRun.processing_results (LLM orchestration)
    - ProcessingArtifact (if used)
    - ExtractedEntity table (older processing)
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

    # 1. Get LLM orchestration results from processing_results JSON
    orchestration_results = _get_orchestration_results(experiment_id)
    for doc_id_str, doc_results in orchestration_results.items():
        doc_id = int(doc_id_str)
        if doc_id not in document_ids:
            continue

        doc = doc_lookup.get(doc_id)
        doc_title = doc.title if doc else f"Document {doc_id}"
        doc_uuid = str(doc.uuid) if doc else None
        doc_year = doc.publication_date.year if doc and doc.publication_date else None

        # Check for extract_entities_spacy results
        if 'extract_entities_spacy' in doc_results:
            tool_result = doc_results['extract_entities_spacy']
            if tool_result.get('status') == 'executed' and 'results' in tool_result:
                data = tool_result['results'].get('data', [])
                for idx, ent in enumerate(data):
                    entity = {
                        'id': f"llm_{doc_id}_{idx}",
                        'text': ent.get('entity', ent.get('text', '')),
                        'entity_type': ent.get('entity_type', ent.get('label', 'UNKNOWN')),
                        'start_position': ent.get('start'),
                        'end_position': ent.get('end'),
                        'confidence': ent.get('confidence', 0),
                        'context': ent.get('context', ''),
                        'source': 'llm',
                        'document_id': doc_id,
                        'document_title': doc_title,
                        'document_uuid': doc_uuid,
                        'document_year': doc_year
                    }
                    add_entity(entity)

    # 2. Get from ProcessingArtifact (if any exist)
    llm_artifacts = ProcessingArtifact.query.filter(
        ProcessingArtifact.document_id.in_(document_ids),
        ProcessingArtifact.artifact_type == 'extracted_entity'
    ).order_by(ProcessingArtifact.document_id, ProcessingArtifact.artifact_index).all()

    for artifact in llm_artifacts:
        content = artifact.get_content()
        doc = doc_lookup.get(artifact.document_id)

        entity = {
            'id': f"artifact_{artifact.id}",
            'text': content.get('entity', ''),
            'entity_type': content.get('entity_type', 'UNKNOWN'),
            'start_position': content.get('start_char'),
            'end_position': content.get('end_char'),
            'confidence': content.get('confidence', 0),
            'context': content.get('context', ''),
            'source': 'llm',
            'document_id': artifact.document_id,
            'document_title': doc.title if doc else f"Document {artifact.document_id}",
            'document_uuid': str(doc.uuid) if doc else None,
            'document_year': doc.publication_date.year if doc and doc.publication_date else None
        }
        add_entity(entity)

    # 3. Get entities from ExtractedEntity table (older processing)
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


@experiments_bp.route('/<int:experiment_id>/results/embeddings')
def experiment_embeddings_results(experiment_id):
    """
    View embeddings information for an experiment.

    Shows:
    - Embedding method used per document
    - Dimension info
    - Chunk counts
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

    # 1. Get LLM orchestration results from processing_results JSON
    orchestration_results = _get_orchestration_results(experiment_id)
    for doc_id_str, doc_results in orchestration_results.items():
        doc_id = int(doc_id_str)
        if doc_id not in document_ids:
            continue

        doc = doc_lookup.get(doc_id)

        # Check for period_aware_embedding results
        if 'period_aware_embedding' in doc_results:
            tool_result = doc_results['period_aware_embedding']
            if tool_result.get('status') == 'executed' and 'results' in tool_result:
                results = tool_result['results']
                metadata = results.get('metadata', {})
                data = results.get('data', [])

                info = {
                    'document_id': doc_id,
                    'document_title': doc.title if doc else f"Document {doc_id}",
                    'document_uuid': str(doc.uuid) if doc else None,
                    'document_year': doc.publication_date.year if doc and doc.publication_date else None,
                    'method': metadata.get('embedding_method', 'period_aware'),
                    'dimensions': metadata.get('embedding_dimensions', 'N/A'),
                    'chunk_count': len(data),
                    'model': metadata.get('model', 'unknown'),
                    'source': 'llm',
                    'created_at': None
                }
                embeddings_info.append(info)
                total_embeddings += len(data)
                docs_with_embeddings.add(doc_id)

    # 2. Get embedding artifact groups
    artifact_groups = ProcessingArtifactGroup.query.filter(
        ProcessingArtifactGroup.document_id.in_(document_ids),
        ProcessingArtifactGroup.artifact_type == 'embedding_vector'
    ).all()

    for group in artifact_groups:
        if group.document_id in docs_with_embeddings:
            continue

        doc = doc_lookup.get(group.document_id)
        metadata = group.get_metadata()

        info = {
            'document_id': group.document_id,
            'document_title': doc.title if doc else f"Document {group.document_id}",
            'document_uuid': str(doc.uuid) if doc else None,
            'document_year': doc.publication_date.year if doc and doc.publication_date else None,
            'method': group.method_key or 'unknown',
            'dimensions': metadata.get('dimensions', 'N/A'),
            'chunk_count': metadata.get('chunk_count', group.artifact_count),
            'model': metadata.get('model', 'unknown'),
            'source': 'llm',
            'created_at': group.created_at
        }
        embeddings_info.append(info)
        total_embeddings += info['chunk_count'] or 0
        docs_with_embeddings.add(group.document_id)

    # 3. Check ProcessingJob for manual embeddings
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
            'created_at': job.completed_at or job.created_at
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

        segment_text = content.get('text', '')
        segment = {
            'id': f"artifact_{artifact.id}",
            'segment_number': artifact.artifact_index + 1,
            'content': segment_text,
            'word_count': metadata.get('word_count', len(segment_text.split()) if segment_text else 0),
            'character_count': len(segment_text) if segment_text else 0,
            'method': content.get('segment_type', metadata.get('method', 'unknown')),
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
