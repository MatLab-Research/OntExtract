"""
Data Transfer Objects (DTOs)

DTOs provide validation, serialization, and clear contracts between layers.
Using Pydantic for automatic validation and type safety.
"""

from .base import BaseDTO, ResponseDTO, PaginatedResponseDTO

__all__ = [
    'BaseDTO',
    'ResponseDTO',
    'PaginatedResponseDTO'
]
