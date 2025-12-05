"""
Helper functions for retrieving LLM orchestration results for documents.

These functions query ExperimentOrchestrationRun.processing_results JSON
to get results that were stored during LLM orchestration runs.
"""

from typing import Dict, List, Any, Optional
from app.models import Document
from app.models.experiment_document import ExperimentDocument
from app.models.experiment_orchestration_run import ExperimentOrchestrationRun
import logging

logger = logging.getLogger(__name__)


def get_orchestration_results_for_document(document_id: int) -> Dict[str, Any]:
    """
    Get LLM orchestration results for a specific document.

    Looks up which experiment(s) the document belongs to and retrieves
    the processing_results from the most recent orchestration run.

    Args:
        document_id: The document ID to look up

    Returns:
        Dictionary of tool_name -> tool_results, or empty dict if none found
    """
    # Find experiment associations for this document
    exp_docs = ExperimentDocument.query.filter_by(document_id=document_id).all()

    if not exp_docs:
        return {}

    # Get the most recent orchestration run from any associated experiment
    results = {}
    for exp_doc in exp_docs:
        run = ExperimentOrchestrationRun.query.filter_by(
            experiment_id=exp_doc.experiment_id
        ).order_by(ExperimentOrchestrationRun.started_at.desc()).first()

        if run and run.processing_results:
            doc_id_str = str(document_id)
            if doc_id_str in run.processing_results:
                # Found results for this document
                results = run.processing_results[doc_id_str]
                logger.debug(f"Found orchestration results for document {document_id} "
                           f"in experiment {exp_doc.experiment_id}")
                break

    return results


def get_definitions_from_orchestration(document_id: int) -> List[Dict[str, Any]]:
    """
    Get definition extraction results from LLM orchestration.

    Args:
        document_id: The document ID

    Returns:
        List of definition dictionaries
    """
    orch_results = get_orchestration_results_for_document(document_id)

    if 'extract_definitions' not in orch_results:
        return []

    tool_result = orch_results['extract_definitions']
    if tool_result.get('status') != 'executed' or 'results' not in tool_result:
        return []

    data = tool_result['results'].get('data', [])
    definitions = []

    for defn in data:
        definitions.append({
            'term': defn.get('term', ''),
            'definition': defn.get('definition', ''),
            'pattern': defn.get('pattern', 'unknown'),
            'confidence': defn.get('confidence', 0),
            'sentence': defn.get('sentence', ''),
            'start_char': defn.get('start'),
            'end_char': defn.get('end'),
            'method': 'llm_orchestration',
            'source': 'llm'
        })

    return definitions


def get_entities_from_orchestration(document_id: int) -> List[Dict[str, Any]]:
    """
    Get entity extraction results from LLM orchestration.

    Args:
        document_id: The document ID

    Returns:
        List of entity dictionaries
    """
    orch_results = get_orchestration_results_for_document(document_id)

    if 'extract_entities_spacy' not in orch_results:
        return []

    tool_result = orch_results['extract_entities_spacy']
    if tool_result.get('status') != 'executed' or 'results' not in tool_result:
        return []

    data = tool_result['results'].get('data', [])
    entities = []

    for ent in data:
        entities.append({
            'text': ent.get('entity', ent.get('text', '')),
            'entity_type': ent.get('entity_type', ent.get('label', 'UNKNOWN')),
            'start': ent.get('start'),
            'end': ent.get('end'),
            'confidence': ent.get('confidence', 0),
            'context': ent.get('context', ''),
            'source': 'llm'
        })

    return entities


def get_embeddings_from_orchestration(document_id: int) -> Dict[str, Any]:
    """
    Get embedding results from LLM orchestration.

    Args:
        document_id: The document ID

    Returns:
        Dictionary with embedding metadata and data, or empty dict
    """
    orch_results = get_orchestration_results_for_document(document_id)

    if 'period_aware_embedding' not in orch_results:
        return {}

    tool_result = orch_results['period_aware_embedding']
    if tool_result.get('status') != 'executed' or 'results' not in tool_result:
        return {}

    results = tool_result['results']
    return {
        'metadata': results.get('metadata', {}),
        'data': results.get('data', []),
        'count': tool_result.get('count', len(results.get('data', []))),
        'source': 'llm'
    }


def get_temporal_from_orchestration(document_id: int) -> List[Dict[str, Any]]:
    """
    Get temporal extraction results from LLM orchestration.

    Args:
        document_id: The document ID

    Returns:
        List of temporal marker dictionaries
    """
    orch_results = get_orchestration_results_for_document(document_id)

    if 'extract_temporal' not in orch_results:
        return []

    tool_result = orch_results['extract_temporal']
    if tool_result.get('status') != 'executed' or 'results' not in tool_result:
        return []

    data = tool_result['results'].get('data', [])
    temporal_markers = []

    for item in data:
        temporal_markers.append({
            'text': item.get('text', ''),
            'type': item.get('type', 'unknown'),
            'normalized': item.get('normalized', ''),
            'start': item.get('start'),
            'end': item.get('end'),
            'source': 'llm'
        })

    return temporal_markers
