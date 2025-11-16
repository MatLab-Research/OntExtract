"""
Pipeline DTOs

Data Transfer Objects for document processing pipeline operations.
Provides validation and serialization for pipeline-related operations.
"""

from pydantic import Field, field_validator
from typing import List, Dict, Any, Optional
from uuid import UUID

from .base import BaseDTO


class StartProcessingDTO(BaseDTO):
    """
    DTO for starting a processing operation

    Validates input for processing operation creation.
    """

    experiment_document_id: int = Field(..., gt=0, description="Experiment document ID")
    processing_type: str = Field(..., min_length=1, max_length=50, description="Type of processing")
    processing_method: str = Field(..., min_length=1, max_length=50, description="Processing method")

    @field_validator('processing_type')
    @classmethod
    def validate_processing_type(cls, v):
        """Ensure processing type is valid"""
        valid_types = ['embeddings', 'segmentation', 'entities', 'temporal', 'etymology']
        if v not in valid_types:
            raise ValueError(f'Invalid processing type. Must be one of: {", ".join(valid_types)}')
        return v

    @field_validator('processing_method')
    @classmethod
    def validate_processing_method(cls, v):
        """Ensure processing method is valid"""
        # Common methods across processing types
        valid_methods = [
            # Embeddings
            'openai', 'sentence_transformers', 'gemini',
            # Segmentation
            'paragraph', 'sentence', 'semantic',
            # Entities
            'spacy', 'nltk', 'llm'
        ]
        if v not in valid_methods:
            raise ValueError(f'Invalid processing method: {v}')
        return v


class ProcessingStatusResponseDTO(BaseDTO):
    """
    DTO for processing status response

    Contains processing status information.
    """

    experiment_document_id: int = Field(..., description="Experiment document ID")
    processing_operations: List[Dict[str, Any]] = Field(default_factory=list, description="Processing operations")


class ProcessingArtifactsResponseDTO(BaseDTO):
    """
    DTO for processing artifacts response

    Contains artifacts for a processing operation.
    """

    processing_id: str = Field(..., description="Processing ID")
    processing_type: str = Field(..., description="Type of processing")
    processing_method: str = Field(..., description="Processing method")
    artifacts: List[Dict[str, Any]] = Field(default_factory=list, description="Processing artifacts")


class OperationTypeInfo(BaseDTO):
    """
    DTO for operation type information

    Contains statistics for a processing type.
    """

    total: int = Field(default=0, description="Total operations")
    completed: int = Field(default=0, description="Completed operations")
    status: str = Field(default="pending", description="Overall status")


class ProcessedDocumentDTO(BaseDTO):
    """
    DTO for processed document information

    Contains processing status for a document.
    """

    id: int = Field(..., description="Document ID")
    exp_doc_id: int = Field(..., description="Experiment document ID")
    name: str = Field(..., description="Document name")
    file_type: Optional[str] = Field(None, description="File type")
    word_count: int = Field(default=0, description="Word count")
    status: str = Field(default="pending", description="Processing status")
    processing_progress: int = Field(default=0, ge=0, le=100, description="Progress percentage")
    operation_types: Dict[str, Any] = Field(default_factory=dict, description="Operation types")
    total_operations: int = Field(default=0, description="Total operations")
    completed_operations: int = Field(default=0, description="Completed operations")


class PipelineOverviewDTO(BaseDTO):
    """
    DTO for pipeline overview data

    Contains all data for pipeline overview page.
    """

    documents: List[Dict[str, Any]] = Field(default_factory=list, description="Processed documents")
    total_count: int = Field(default=0, description="Total document count")
    completed_count: int = Field(default=0, description="Completed document count")
    progress_percentage: float = Field(default=0.0, ge=0.0, le=100.0, description="Overall progress")


class DocumentNavigationDTO(BaseDTO):
    """
    DTO for document navigation information

    Contains navigation data for document processing view.
    """

    has_previous: bool = Field(default=False, description="Has previous document")
    has_next: bool = Field(default=False, description="Has next document")
    previous_doc_id: Optional[int] = Field(None, description="Previous document ID")
    next_doc_id: Optional[int] = Field(None, description="Next document ID")
    doc_index: int = Field(default=0, description="Current document index")
    total_docs: int = Field(default=0, description="Total documents")


class ProcessDocumentDataDTO(BaseDTO):
    """
    DTO for process document view data

    Contains all data for document processing page.
    """

    processing_operations: List[Dict[str, Any]] = Field(default_factory=list, description="Processing operations")
    processing_progress: int = Field(default=0, ge=0, le=100, description="Progress percentage")
    navigation: Dict[str, Any] = Field(default_factory=dict, description="Navigation info")


class EmbeddingInfoDTO(BaseDTO):
    """
    DTO for embedding information

    Contains metadata about applied embeddings.
    """

    type: str = Field(..., description="Embedding type (single or chunked)")
    model: str = Field(..., description="Embedding model name")
    dimension: int = Field(..., description="Embedding dimension")
    experiment_id: int = Field(..., description="Experiment ID")
    chunks: Optional[int] = Field(None, description="Number of chunks (if chunked)")
    chunk_size: Optional[int] = Field(None, description="Chunk size (if chunked)")


class ApplyEmbeddingsResponseDTO(BaseDTO):
    """
    DTO for apply embeddings response

    Contains result of embedding application.
    """

    embedding_info: Dict[str, Any] = Field(..., description="Embedding information")
    processing_progress: int = Field(default=0, ge=0, le=100, description="Processing progress")


class StartProcessingResponseDTO(BaseDTO):
    """
    DTO for start processing response

    Contains result of starting a processing operation.
    """

    processing_id: str = Field(..., description="Processing operation ID")
    status: str = Field(..., description="Processing status")
