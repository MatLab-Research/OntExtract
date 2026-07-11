"""Public facade for the experiment document processing pipeline."""

from app.services.base_service import BaseService
from app.services.pipeline import (
    LLM_TOOL_TO_OPERATION_MAP,
    PipelineEmbeddingMixin,
    PipelineEntityMixin,
    PipelineExecutionMixin,
    PipelineExtractionMixin,
    PipelineOverviewMixin,
    PipelineProvenanceMixin,
    PipelineQueryMixin,
    PipelineSegmentationMixin,
)


class PipelineService(
    PipelineOverviewMixin,
    PipelineQueryMixin,
    PipelineExecutionMixin,
    PipelineEmbeddingMixin,
    PipelineSegmentationMixin,
    PipelineEntityMixin,
    PipelineExtractionMixin,
    PipelineProvenanceMixin,
    BaseService,
):
    """Coordinate pipeline reads, execution, artifacts, and provenance."""


_pipeline_service = None


def get_pipeline_service() -> PipelineService:
    """Return the process-wide pipeline service instance."""
    global _pipeline_service
    if _pipeline_service is None:
        _pipeline_service = PipelineService()
    return _pipeline_service


__all__ = [
    "LLM_TOOL_TO_OPERATION_MAP",
    "PipelineService",
    "get_pipeline_service",
]
