"""
Base Service Class

Provides common functionality for all service classes:
- Database session management
- Error handling utilities
- Logging setup
- Common CRUD operations
"""

import logging
from typing import TypeVar, Generic, Type, Optional, List
from flask import current_app
from app import db


# Type variable for generic service
T = TypeVar('T')


class BaseService(Generic[T]):
    """
    Base class for all service classes

    Provides common functionality and patterns for service layer.
    Services contain business logic and coordinate between routes and data layer.

    Example:
        >>> class ExperimentService(BaseService):
        ...     def create_experiment(self, data):
        ...         # Business logic here
        ...         pass
    """

    def __init__(self, model: Optional[Type[T]] = None):
        """
        Initialize base service

        Args:
            model: SQLAlchemy model class (optional)
        """
        self.model = model
        self.logger = logging.getLogger(self.__class__.__name__)

    # Database session helpers

    def commit(self):
        """Commit current database session"""
        try:
            db.session.commit()
            self.logger.debug("Database session committed successfully")
        except Exception as e:
            self.logger.error(f"Error committing session: {e}")
            db.session.rollback()
            raise

    def rollback(self):
        """Rollback current database session"""
        db.session.rollback()
        self.logger.debug("Database session rolled back")

    def flush(self):
        """Flush current database session"""
        db.session.flush()

    def add(self, instance: T):
        """
        Add instance to database session

        Args:
            instance: Model instance to add
        """
        db.session.add(instance)
        self.logger.debug(f"Added {instance.__class__.__name__} to session")

    def delete(self, instance: T):
        """
        Delete instance from database

        Args:
            instance: Model instance to delete
        """
        db.session.delete(instance)
        self.logger.debug(f"Deleted {instance.__class__.__name__} from session")

    # Error handling utilities

    def handle_error(self, error: Exception, message: str):
        """
        Handle service errors consistently

        Args:
            error: Exception that occurred
            message: User-friendly error message

        Raises:
            ServiceError: Wrapped exception with context
        """
        self.logger.error(f"{message}: {str(error)}", exc_info=True)
        self.rollback()
        raise ServiceError(message) from error

    # Validation helpers

    def validate_required(self, value, field_name: str):
        """
        Validate that a required field is present

        Args:
            value: Value to validate
            field_name: Name of field for error message

        Raises:
            ValidationError: If value is None or empty
        """
        if value is None or (isinstance(value, str) and not value.strip()):
            raise ValidationError(f"{field_name} is required")

    def validate_positive(self, value: int, field_name: str):
        """
        Validate that a value is positive

        Args:
            value: Value to validate
            field_name: Name of field for error message

        Raises:
            ValidationError: If value is not positive
        """
        if value is None or value <= 0:
            raise ValidationError(f"{field_name} must be a positive number")


class ServiceError(Exception):
    """Base exception for service layer errors"""
    pass


class ValidationError(ServiceError):
    """Exception for validation errors"""
    pass


class NotFoundError(ServiceError):
    """Exception for resource not found errors"""
    pass


class PermissionError(ServiceError):
    """Exception for permission/authorization errors"""
    pass
