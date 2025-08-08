"""
Shared services for text processing, ontology handling, and LLM integration.

This package provides reusable components that can be shared between 
ProEthica and OntExtract applications.
"""

__version__ = "0.1.0"

# Import main services for easy access
from .embedding.embedding_service import EmbeddingService
from .ontology.entity_service import OntologyEntityService

__all__ = [
    "EmbeddingService", 
    "OntologyEntityService"
]
