"""Mappings shared by pipeline presentation and execution layers."""

LLM_TOOL_TO_OPERATION_MAP = {
    "extract_entities_spacy": {"type": "entities", "method": "spacy"},
    "extract_temporal": {"type": "temporal", "method": "spacy"},
    "extract_definitions": {"type": "definitions", "method": "pattern"},
    "extract_causal": {"type": "causal", "method": "spacy"},
    "period_aware_embedding": {"type": "embeddings", "method": "period_aware"},
    "segment_paragraph": {"type": "segmentation", "method": "paragraph"},
    "segment_sentence": {"type": "segmentation", "method": "sentence"},
}
