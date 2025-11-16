"""
Orchestration DTOs

Data Transfer Objects for LLM orchestration operations.
Provides validation and serialization for orchestration-related operations.
"""

from pydantic import Field, field_validator
from typing import List, Dict, Any, Optional

from .base import BaseDTO


class CreateOrchestrationDecisionDTO(BaseDTO):
    """
    DTO for creating an orchestration decision

    Validates input for decision creation.
    """

    term_text: str = Field(..., min_length=1, max_length=200, description="Term to analyze")


class RunOrchestrated

AnalysisDTO(BaseDTO):
    """
    DTO for running orchestrated analysis

    Validates input for running analysis with multiple terms.
    """

    terms: List[str] = Field(..., min_items=1, description="List of terms to analyze")

    @field_validator('terms')
    @classmethod
    def validate_terms(cls, v):
        """Ensure at least one term is provided"""
        if not v or len(v) == 0:
            raise ValueError('At least one term is required')
        if not all(isinstance(term, str) for term in v):
            raise ValueError('All terms must be strings')
        return v


class OrchestrationDecisionResponseDTO(BaseDTO):
    """
    DTO for orchestration decision response

    Contains the created decision details.
    """

    decision_id: str = Field(..., description="Decision ID")
    selected_tools: List[str] = Field(default_factory=list, description="Selected NLP tools")
    embedding_model: str = Field(..., description="Embedding model selected")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Decision confidence")
    reasoning: str = Field(..., description="Reasoning for tool selection")


class AnalysisResultDTO(BaseDTO):
    """
    DTO for a single analysis result

    Contains results for one term's analysis.
    """

    term: str = Field(..., description="Term analyzed")
    decision_id: str = Field(..., description="Decision ID used")
    tools_used: List[str] = Field(default_factory=list, description="Tools used")
    embedding_model: str = Field(..., description="Embedding model used")
    confidence: float = Field(..., description="Confidence score")
    processing_time: str = Field(..., description="Processing time")
    semantic_drift_detected: bool = Field(default=False, description="Whether drift was detected")
    drift_magnitude: Optional[float] = Field(None, description="Magnitude of drift")
    periods_analyzed: int = Field(default=0, description="Number of periods analyzed")
    insights: List[str] = Field(default_factory=list, description="Analysis insights")


class RunAnalysisResponseDTO(BaseDTO):
    """
    DTO for orchestrated analysis response

    Contains results for all terms analyzed.
    """

    results: List[Dict[str, Any]] = Field(default_factory=list, description="Analysis results")
    total_decisions: int = Field(..., description="Total number of decisions")


class OrchestrationResultsDTO(BaseDTO):
    """
    DTO for orchestration results view

    Contains comprehensive results data for display.
    """

    total_decisions: int = Field(default=0, description="Total decisions")
    completed_decisions: int = Field(default=0, description="Completed decisions")
    avg_confidence: float = Field(default=0.0, description="Average confidence")
    cross_document_insights: Optional[str] = Field(None, description="Cross-document insights (HTML)")
    duration: Optional[str] = Field(None, description="Analysis duration")
    document_count: int = Field(default=0, description="Number of documents")
