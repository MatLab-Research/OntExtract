"""
Term DTOs

Data Transfer Objects for term management operations.
Provides validation and serialization for term-related operations.
"""

from pydantic import Field, field_validator
from typing import List, Dict, Any, Optional

from .base import BaseDTO


class UpdateTermsDTO(BaseDTO):
    """
    DTO for updating terms and domains

    Validates input for term configuration updates.
    """

    terms: List[str] = Field(default_factory=list, description="List of target terms")
    domains: List[str] = Field(default_factory=list, description="List of domains")
    definitions: Optional[Dict[str, Any]] = Field(None, description="Optional term definitions")

    @field_validator('terms')
    @classmethod
    def validate_terms(cls, v):
        """Ensure terms is a list of strings"""
        if not isinstance(v, list):
            raise ValueError('Terms must be a list')
        if not all(isinstance(term, str) for term in v):
            raise ValueError('All terms must be strings')
        return v

    @field_validator('domains')
    @classmethod
    def validate_domains(cls, v):
        """Ensure domains is a list of strings"""
        if not isinstance(v, list):
            raise ValueError('Domains must be a list')
        if not all(isinstance(domain, str) for domain in v):
            raise ValueError('All domains must be strings')
        return v


class FetchDefinitionsDTO(BaseDTO):
    """
    DTO for fetching term definitions

    Validates input for definition fetching.
    """

    term: str = Field(..., min_length=1, max_length=200, description="Term to fetch definitions for")
    domains: List[str] = Field(..., min_items=1, description="List of domains to search")

    @field_validator('domains')
    @classmethod
    def validate_domains(cls, v):
        """Ensure at least one domain is provided"""
        if not v or len(v) == 0:
            raise ValueError('At least one domain is required')
        if not all(isinstance(domain, str) for domain in v):
            raise ValueError('All domains must be strings')
        return v


class TermConfigurationDTO(BaseDTO):
    """
    DTO for term configuration response

    Serializes term configuration data for API responses.
    """

    terms: List[str] = Field(default_factory=list, description="List of target terms")
    domains: List[str] = Field(default_factory=list, description="List of domains")
    definitions: Dict[str, Any] = Field(default_factory=dict, description="Term definitions by domain")


class DefinitionDTO(BaseDTO):
    """
    DTO for a single definition

    Represents a term definition with source information.
    """

    text: str = Field(..., description="Definition text")
    source: Optional[str] = Field(None, description="Source of definition")


class OntologyMappingDTO(BaseDTO):
    """
    DTO for ontology mapping

    Represents a mapping to an ontology concept.
    """

    label: str = Field(..., description="Ontology concept label")
    description: str = Field(..., description="Ontology concept description")


class DefinitionResponseDTO(BaseDTO):
    """
    DTO for definition fetch response

    Contains definitions and ontology mappings for a term across domains.
    """

    definitions: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Definitions by domain"
    )
    ontology_mappings: Dict[str, List[Dict[str, str]]] = Field(
        default_factory=dict,
        description="Ontology mappings by domain"
    )
