"""
Experiment DTOs

Data Transfer Objects for experiment-related operations.
Provides validation and serialization for experiment CRUD operations.
"""

from pydantic import Field, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime

from .base import BaseDTO, ResponseDTO


class CreateExperimentDTO(BaseDTO):
    """
    DTO for experiment creation

    Validates all required fields and business rules for creating an experiment.
    """

    name: str = Field(..., min_length=1, max_length=200, description="Experiment name")
    description: Optional[str] = Field(None, max_length=2000, description="Experiment description")
    experiment_type: str = Field(
        ...,
        pattern="^(temporal_analysis|temporal_evolution|semantic_drift|domain_comparison|entity_extraction)$",
        description="Type of experiment to run"
    )
    document_ids: List[int] = Field(default_factory=list, description="List of document IDs")
    reference_ids: List[int] = Field(default_factory=list, description="List of reference IDs")
    configuration: Dict[str, Any] = Field(default_factory=dict, description="Experiment configuration")

    @field_validator('document_ids', 'reference_ids')
    @classmethod
    def validate_has_documents(cls, v, info):
        """Ensure at least one document or reference is provided"""
        # Check if this is the reference_ids field and document_ids exists
        if info.field_name == 'reference_ids':
            document_ids = info.data.get('document_ids', [])
            if len(document_ids) == 0 and len(v) == 0:
                raise ValueError('At least one document or reference must be selected')
        return v

    @field_validator('configuration')
    @classmethod
    def validate_configuration(cls, v):
        """Validate configuration structure"""
        # Ensure configuration is a valid dict
        if not isinstance(v, dict):
            raise ValueError('Configuration must be a dictionary')
        return v


class UpdateExperimentDTO(BaseDTO):
    """
    DTO for experiment updates

    All fields are optional to allow partial updates.
    """

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    configuration: Optional[Dict[str, Any]] = None
    document_ids: Optional[List[int]] = None
    reference_ids: Optional[List[int]] = None


class ExperimentResponseDTO(ResponseDTO):
    """
    DTO for experiment API responses

    Provides consistent response structure for experiment operations.
    """

    experiment_id: Optional[int] = None
    experiment: Optional[Dict[str, Any]] = None


class ExperimentDetailDTO(BaseDTO):
    """
    DTO for experiment details

    Serializes experiment data for API responses.
    """

    id: int
    name: str
    description: Optional[str] = None
    experiment_type: str
    status: str = "pending"
    created_at: datetime
    updated_at: Optional[datetime] = None
    document_count: int = 0
    reference_count: int = 0
    configuration: Dict[str, Any] = Field(default_factory=dict)
    user_id: Optional[int] = None

    @classmethod
    def from_model(cls, experiment):
        """
        Create DTO from SQLAlchemy model

        Args:
            experiment: Experiment model instance

        Returns:
            ExperimentDetailDTO instance
        """
        import json

        # Parse configuration if it's a string
        config = experiment.configuration
        if isinstance(config, str):
            try:
                config = json.loads(config)
            except (json.JSONDecodeError, TypeError):
                config = {}

        return cls(
            id=experiment.id,
            name=experiment.name,
            description=experiment.description,
            experiment_type=experiment.experiment_type,
            status=experiment.status if hasattr(experiment, 'status') else 'pending',
            created_at=experiment.created_at,
            updated_at=experiment.updated_at if hasattr(experiment, 'updated_at') else None,
            document_count=len(experiment.documents) if hasattr(experiment, 'documents') else 0,
            reference_count=len(experiment.references) if hasattr(experiment, 'references') else 0,
            configuration=config,
            user_id=experiment.user_id
        )


class ExperimentListItemDTO(BaseDTO):
    """
    DTO for experiment list items

    Lighter version of ExperimentDetailDTO for list views.
    """

    id: int
    name: str
    experiment_type: str
    status: str = "pending"
    created_at: datetime
    document_count: int = 0

    @classmethod
    def from_model(cls, experiment):
        """
        Create DTO from SQLAlchemy model

        Args:
            experiment: Experiment model instance

        Returns:
            ExperimentListItemDTO instance
        """
        return cls(
            id=experiment.id,
            name=experiment.name,
            experiment_type=experiment.experiment_type,
            status=experiment.status if hasattr(experiment, 'status') else 'pending',
            created_at=experiment.created_at,
            document_count=len(experiment.documents) if hasattr(experiment, 'documents') else 0
        )
