"""
Evolution DTOs

Data Transfer Objects for semantic evolution analysis operations.
Provides validation and serialization for evolution-related operations.
"""

from pydantic import Field, field_validator
from typing import List, Dict, Any, Optional

from .base import BaseDTO


class AnalyzeEvolutionDTO(BaseDTO):
    """
    DTO for evolution analysis request

    Validates input for semantic evolution analysis.
    """

    term: str = Field(..., min_length=1, max_length=200, description="Term to analyze")
    periods: List[Any] = Field(..., min_items=1, description="List of time periods to analyze")

    @field_validator('periods')
    @classmethod
    def validate_periods(cls, v):
        """Ensure at least one period is provided"""
        if not v or len(v) == 0:
            raise ValueError('At least one period is required')
        return v


class DriftMetricsDTO(BaseDTO):
    """
    DTO for semantic drift metrics

    Contains quantitative measures of semantic drift.
    """

    average_drift: float = Field(default=0.0, description="Average drift score")
    total_drift: float = Field(default=0.0, description="Total drift across all periods")
    stable_term_count: int = Field(default=0, description="Number of stable associated terms")


class EvolutionAnalysisResponseDTO(BaseDTO):
    """
    DTO for evolution analysis response

    Contains narrative analysis and drift metrics.
    """

    analysis: str = Field(..., description="Narrative analysis text")
    drift_metrics: Dict[str, Any] = Field(default_factory=dict, description="Drift metrics")


class AcademicAnchorDTO(BaseDTO):
    """
    DTO for an academic anchor point

    Represents a temporal version of a term.
    """

    year: int = Field(..., description="Year of this version")
    period: str = Field(..., description="Temporal period label")
    meaning: str = Field(..., description="Meaning description")
    citation: str = Field(..., description="Source citation")
    domain: str = Field(..., description="Domain/discipline")
    confidence: float = Field(default=1.0, description="Confidence level")
    context_anchor: List[str] = Field(default_factory=list, description="Context anchors")


class EvolutionVisualizationDataDTO(BaseDTO):
    """
    DTO for evolution visualization data

    Contains all data needed for semantic evolution visualization.
    """

    term: str = Field(..., description="Target term")
    academic_anchors: List[Dict[str, Any]] = Field(default_factory=list, description="Temporal versions")
    oed_data: Optional[Dict[str, Any]] = Field(None, description="OED etymological data")
    reference_data: Dict[str, Any] = Field(default_factory=dict, description="Reference data")
    temporal_span: int = Field(default=0, description="Span of years covered")
    domains: List[str] = Field(default_factory=list, description="List of domains")
