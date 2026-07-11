"""Public facade for document processing tools.

Implementations are grouped by responsibility in ``document_processing_tools``.
This module preserves the original import and factory API.
"""

from typing import Optional

from app.services.document_processing_tools import (
    DefinitionExtractionTools,
    EmbeddingTools,
    EntityExtractionTools,
    ProcessingResult,
    RelationshipExtractionTools,
    SegmentationTools,
)


class DocumentProcessor(
    SegmentationTools,
    EntityExtractionTools,
    RelationshipExtractionTools,
    DefinitionExtractionTools,
    EmbeddingTools,
):
    """Facade exposing all supported document processing operations."""


def get_processor(
    user_id: Optional[int] = None,
    experiment_id: Optional[int] = None,
) -> DocumentProcessor:
    """Create a document processor with optional provenance context."""
    return DocumentProcessor(user_id=user_id, experiment_id=experiment_id)


__all__ = ["DocumentProcessor", "ProcessingResult", "get_processor"]
