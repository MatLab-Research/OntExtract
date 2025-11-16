"""
Base DTO Classes

Provides base classes for all DTOs with common functionality.
"""

from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Any, Dict
from datetime import datetime


class BaseDTO(BaseModel):
    """
    Base class for all DTOs

    Provides common Pydantic configuration and utilities.
    """

    model_config = ConfigDict(
        # Allow arbitrary types (for SQLAlchemy models if needed)
        arbitrary_types_allowed=True,
        # Use enum values instead of enum instances
        use_enum_values=True,
        # Validate on assignment
        validate_assignment=True,
        # Allow population by field name or alias
        populate_by_name=True,
        # Convert strings to datetime automatically
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None
        }
    )

    def to_dict(self) -> Dict:
        """
        Convert DTO to dictionary

        Returns:
            Dictionary representation of DTO
        """
        return self.model_dump(exclude_none=True)

    def to_json(self) -> str:
        """
        Convert DTO to JSON string

        Returns:
            JSON string representation of DTO
        """
        return self.model_dump_json(exclude_none=True)


class ResponseDTO(BaseDTO):
    """
    Base class for API response DTOs

    Provides consistent response structure across all API endpoints.
    """

    success: bool
    message: Optional[str] = None
    error: Optional[str] = None
    data: Optional[Any] = None

    @classmethod
    def success_response(cls, data: Any = None, message: str = "Operation successful"):
        """
        Create a success response

        Args:
            data: Response data
            message: Success message

        Returns:
            ResponseDTO instance
        """
        return cls(success=True, data=data, message=message)

    @classmethod
    def error_response(cls, error: str, message: str = "Operation failed"):
        """
        Create an error response

        Args:
            error: Error details
            message: Error message

        Returns:
            ResponseDTO instance
        """
        return cls(success=False, error=error, message=message)


class PaginatedResponseDTO(ResponseDTO):
    """
    Response DTO for paginated data

    Includes pagination metadata along with response data.
    """

    page: int = 1
    per_page: int = 10
    total: int = 0
    pages: int = 0
    has_next: bool = False
    has_prev: bool = False

    @classmethod
    def from_pagination(
        cls,
        items: List[Any],
        page: int,
        per_page: int,
        total: int,
        message: str = "Data retrieved successfully"
    ):
        """
        Create paginated response from pagination data

        Args:
            items: List of items for current page
            page: Current page number
            per_page: Items per page
            total: Total number of items
            message: Success message

        Returns:
            PaginatedResponseDTO instance
        """
        pages = (total + per_page - 1) // per_page  # Ceiling division

        return cls(
            success=True,
            data=items,
            message=message,
            page=page,
            per_page=per_page,
            total=total,
            pages=pages,
            has_next=page < pages,
            has_prev=page > 1
        )


class ValidationErrorDTO(BaseDTO):
    """
    DTO for validation errors

    Provides detailed validation error information.
    """

    field: str
    message: str
    value: Optional[Any] = None

    @classmethod
    def from_pydantic_error(cls, error: Dict):
        """
        Create validation error from Pydantic error

        Args:
            error: Pydantic validation error dict

        Returns:
            ValidationErrorDTO instance
        """
        return cls(
            field=".".join(str(loc) for loc in error.get('loc', [])),
            message=error.get('msg', 'Validation error'),
            value=error.get('input')
        )


class BulkOperationResultDTO(BaseDTO):
    """
    DTO for bulk operation results

    Tracks success/failure for batch operations.
    """

    total: int
    successful: int
    failed: int
    errors: List[str] = []

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage"""
        if self.total == 0:
            return 0.0
        return (self.successful / self.total) * 100

    @property
    def all_successful(self) -> bool:
        """Check if all operations succeeded"""
        return self.failed == 0 and self.successful == self.total
