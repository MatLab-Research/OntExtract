"""
Temporal DTOs

Data Transfer Objects for temporal evolution analysis operations.
Provides validation and serialization for temporal-related operations.
"""

from pydantic import Field, field_validator
from typing import List, Dict, Any, Optional

from .base import BaseDTO


class UpdateTemporalTermsDTO(BaseDTO):
    """
    DTO for updating temporal terms and periods

    Validates input for updating temporal experiment configuration.
    """

    terms: List[str] = Field(default_factory=list, description="List of target terms")
    periods: List[int] = Field(default_factory=list, description="List of time periods")
    temporal_data: Dict[str, Any] = Field(default_factory=dict, description="Temporal data")

    @field_validator('periods')
    @classmethod
    def validate_periods(cls, v):
        """Ensure periods are valid years"""
        if v:
            for period in v:
                if not isinstance(period, int) or period < 1000 or period > 3000:
                    raise ValueError(f'Invalid year: {period}. Must be between 1000 and 3000')
        return v


class FetchTemporalDataDTO(BaseDTO):
    """
    DTO for fetching temporal data request

    Validates input for temporal analysis.
    """

    term: str = Field(..., min_length=1, max_length=200, description="Term to analyze")
    periods: Optional[List[int]] = Field(None, description="List of time periods to analyze")
    use_oed: bool = Field(default=False, description="Whether to use OED integration")

    @field_validator('periods')
    @classmethod
    def validate_periods(cls, v):
        """Ensure periods are valid years if provided"""
        if v:
            for period in v:
                if not isinstance(period, int) or period < 1000 or period > 3000:
                    raise ValueError(f'Invalid year: {period}. Must be between 1000 and 3000')
        return v


class TemporalConfigurationDTO(BaseDTO):
    """
    DTO for temporal configuration response

    Contains the temporal experiment configuration.
    """

    terms: List[str] = Field(default_factory=list, description="Target terms")
    periods: List[int] = Field(default_factory=list, description="Time periods")
    temporal_data: Dict[str, Any] = Field(default_factory=dict, description="Temporal data")


class OEDPeriodDataDTO(BaseDTO):
    """
    DTO for OED period data

    Contains OED-derived temporal information.
    """

    min_year: int = Field(..., description="Minimum year from OED")
    max_year: int = Field(..., description="Maximum year from OED")
    suggested_periods: List[int] = Field(default_factory=list, description="Suggested periods")
    quotation_years: List[int] = Field(default_factory=list, description="Years with quotations")


class PeriodDataDTO(BaseDTO):
    """
    DTO for data within a specific time period

    Contains analysis results for one period.
    """

    frequency: int = Field(default=0, description="Term frequency")
    contexts: List[str] = Field(default_factory=list, description="Usage contexts")
    co_occurring_terms: List[str] = Field(default_factory=list, description="Co-occurring terms")
    evolution: str = Field(default="unknown", description="Evolution status")
    definition: Optional[str] = Field(None, description="Definition for this period")
    source: Optional[str] = Field(None, description="Data source")
    is_oed_data: bool = Field(default=False, description="Whether this is OED data")
    oed_note: Optional[str] = Field(None, description="OED integration note")


class DriftAnalysisDTO(BaseDTO):
    """
    DTO for drift analysis results

    Contains semantic drift metrics.
    """

    average_drift: float = Field(default=0.0, description="Average drift score")
    stable_terms: List[str] = Field(default_factory=list, description="Stable associated terms")
    periods: Dict[str, Any] = Field(default_factory=dict, description="Period-specific drift data")


class TemporalAnalysisResponseDTO(BaseDTO):
    """
    DTO for temporal analysis response

    Contains complete temporal analysis results.
    """

    temporal_data: Dict[str, Any] = Field(default_factory=dict, description="Temporal data by period")
    frequency_data: Dict[int, int] = Field(default_factory=dict, description="Frequency by period")
    drift_analysis: Dict[str, Any] = Field(default_factory=dict, description="Drift analysis")
    narrative: str = Field(..., description="Evolution narrative")
    periods_used: List[int] = Field(default_factory=list, description="Periods analyzed")
    oed_data: Optional[Dict[str, Any]] = Field(None, description="OED data if available")


class TemporalUIDataDTO(BaseDTO):
    """
    DTO for temporal UI data

    Contains all data needed for temporal term management UI.
    """

    time_periods: List[int] = Field(default_factory=list, description="Time periods")
    terms: List[str] = Field(default_factory=list, description="Target terms")
    start_year: int = Field(default=2000, description="Start year")
    end_year: int = Field(default=2020, description="End year")
    use_oed_periods: bool = Field(default=False, description="Whether using OED periods")
    oed_period_data: Dict[str, Any] = Field(default_factory=dict, description="OED period data by term")
    term_periods: Dict[str, List[int]] = Field(default_factory=dict, description="Periods by term")
