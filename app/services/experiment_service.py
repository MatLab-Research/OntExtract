"""
Experiment Service

Business logic for experiment operations.
Handles CRUD operations, validation, and document/reference management.
"""

import json
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from app import db
from app.models import Experiment, Document
from app.services.base_service import BaseService, ServiceError, NotFoundError, ValidationError
from app.dto.experiment_dto import (
    CreateExperimentDTO,
    UpdateExperimentDTO,
    ExperimentDetailDTO,
    ExperimentListItemDTO
)

logger = logging.getLogger(__name__)


class ExperimentService(BaseService):
    """
    Service for experiment operations

    Handles all business logic related to experiments including:
    - Creating and updating experiments
    - Managing document and reference associations
    - Running experiments
    - Retrieving experiment data and status
    """

    def __init__(self):
        """Initialize ExperimentService"""
        super().__init__(model=Experiment)

    def create_experiment(
        self,
        data: CreateExperimentDTO,
        user_id: int
    ) -> Experiment:
        """
        Create a new experiment

        Args:
            data: Validated experiment creation data
            user_id: ID of user creating the experiment

        Returns:
            Created experiment instance

        Raises:
            ValidationError: If validation fails
            ServiceError: If creation fails
        """
        try:
            # Create experiment instance
            experiment = Experiment(
                name=data.name,
                description=data.description or '',
                experiment_type=data.experiment_type,
                user_id=user_id,
                configuration=json.dumps(data.configuration)
            )

            # Add to session and flush to get ID
            self.add(experiment)
            self.flush()

            logger.info(f"Created experiment '{experiment.name}' (ID: {experiment.id})")

            # Add documents to experiment
            if data.document_ids:
                self._add_documents_to_experiment(experiment, data.document_ids)

            # Add references to experiment
            if data.reference_ids:
                self._add_references_to_experiment(experiment, data.reference_ids)

            # Commit transaction
            self.commit()

            logger.info(
                f"Experiment {experiment.id} created with "
                f"{len(data.document_ids)} documents and {len(data.reference_ids)} references"
            )

            return experiment

        except Exception as e:
            self.rollback()
            logger.error(f"Failed to create experiment: {e}", exc_info=True)
            raise ServiceError(f"Failed to create experiment: {str(e)}") from e

    def update_experiment(
        self,
        experiment_id: int,
        data: UpdateExperimentDTO,
        user_id: Optional[int] = None
    ) -> Experiment:
        """
        Update an existing experiment

        Args:
            experiment_id: ID of experiment to update
            data: Validated update data
            user_id: Optional user ID for permission check

        Returns:
            Updated experiment instance

        Raises:
            NotFoundError: If experiment doesn't exist
            PermissionError: If user doesn't have permission
            ServiceError: If update fails
        """
        try:
            # Get experiment
            experiment = self.get_experiment(experiment_id)

            # Check permissions if user_id provided
            if user_id is not None and experiment.user_id != user_id:
                raise PermissionError(f"User {user_id} does not have permission to update experiment {experiment_id}")

            # Update fields if provided
            if data.name is not None:
                experiment.name = data.name

            if data.description is not None:
                experiment.description = data.description

            if data.configuration is not None:
                experiment.configuration = json.dumps(data.configuration)

            # Commit changes
            self.commit()

            logger.info(f"Updated experiment {experiment_id}")

            return experiment

        except (NotFoundError, PermissionError):
            raise
        except Exception as e:
            self.rollback()
            logger.error(f"Failed to update experiment {experiment_id}: {e}", exc_info=True)
            raise ServiceError(f"Failed to update experiment: {str(e)}") from e

    def delete_experiment(
        self,
        experiment_id: int,
        user_id: Optional[int] = None
    ) -> bool:
        """
        Delete an experiment

        Args:
            experiment_id: ID of experiment to delete
            user_id: Optional user ID for permission check

        Returns:
            True if deleted successfully

        Raises:
            NotFoundError: If experiment doesn't exist
            PermissionError: If user doesn't have permission
            ServiceError: If deletion fails
        """
        try:
            # Get experiment
            experiment = self.get_experiment(experiment_id)

            # Check permissions if user_id provided
            if user_id is not None and experiment.user_id != user_id:
                raise PermissionError(f"User {user_id} does not have permission to delete experiment {experiment_id}")

            # Delete experiment
            self.delete(experiment)
            self.commit()

            logger.info(f"Deleted experiment {experiment_id}")

            return True

        except (NotFoundError, PermissionError):
            raise
        except Exception as e:
            self.rollback()
            logger.error(f"Failed to delete experiment {experiment_id}: {e}", exc_info=True)
            raise ServiceError(f"Failed to delete experiment: {str(e)}") from e

    def get_experiment(self, experiment_id: int) -> Experiment:
        """
        Get experiment by ID

        Args:
            experiment_id: ID of experiment to retrieve

        Returns:
            Experiment instance

        Raises:
            NotFoundError: If experiment doesn't exist
        """
        experiment = Experiment.query.filter_by(id=experiment_id).first()

        if not experiment:
            raise NotFoundError(f"Experiment {experiment_id} not found")

        return experiment

    def get_experiment_detail(self, experiment_id: int) -> ExperimentDetailDTO:
        """
        Get detailed experiment information

        Args:
            experiment_id: ID of experiment

        Returns:
            ExperimentDetailDTO with full experiment data

        Raises:
            NotFoundError: If experiment doesn't exist
        """
        experiment = self.get_experiment(experiment_id)
        return ExperimentDetailDTO.from_model(experiment)

    def list_experiments(
        self,
        user_id: Optional[int] = None,
        experiment_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[ExperimentListItemDTO]:
        """
        List experiments with optional filtering

        Args:
            user_id: Filter by user ID
            experiment_type: Filter by experiment type
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of ExperimentListItemDTO
        """
        query = Experiment.query

        # Apply filters
        if user_id is not None:
            query = query.filter_by(user_id=user_id)

        if experiment_type is not None:
            query = query.filter_by(experiment_type=experiment_type)

        # Order by creation date (newest first)
        query = query.order_by(Experiment.created_at.desc())

        # Apply pagination
        experiments = query.limit(limit).offset(offset).all()

        # Convert to DTOs
        return [ExperimentListItemDTO.from_model(exp) for exp in experiments]

    def add_documents_to_experiment(
        self,
        experiment_id: int,
        document_ids: List[int]
    ) -> Experiment:
        """
        Add documents to an experiment

        Args:
            experiment_id: ID of experiment
            document_ids: List of document IDs to add

        Returns:
            Updated experiment instance

        Raises:
            NotFoundError: If experiment doesn't exist
            ServiceError: If operation fails
        """
        try:
            experiment = self.get_experiment(experiment_id)
            self._add_documents_to_experiment(experiment, document_ids)
            self.commit()

            logger.info(f"Added {len(document_ids)} documents to experiment {experiment_id}")

            return experiment

        except NotFoundError:
            raise
        except Exception as e:
            self.rollback()
            logger.error(f"Failed to add documents to experiment {experiment_id}: {e}", exc_info=True)
            raise ServiceError(f"Failed to add documents: {str(e)}") from e

    def add_references_to_experiment(
        self,
        experiment_id: int,
        reference_ids: List[int]
    ) -> Experiment:
        """
        Add references to an experiment

        Args:
            experiment_id: ID of experiment
            reference_ids: List of reference IDs to add

        Returns:
            Updated experiment instance

        Raises:
            NotFoundError: If experiment doesn't exist
            ServiceError: If operation fails
        """
        try:
            experiment = self.get_experiment(experiment_id)
            self._add_references_to_experiment(experiment, reference_ids)
            self.commit()

            logger.info(f"Added {len(reference_ids)} references to experiment {experiment_id}")

            return experiment

        except NotFoundError:
            raise
        except Exception as e:
            self.rollback()
            logger.error(f"Failed to add references to experiment {experiment_id}: {e}", exc_info=True)
            raise ServiceError(f"Failed to add references: {str(e)}") from e

    # Private helper methods

    def _add_documents_to_experiment(
        self,
        experiment: Experiment,
        document_ids: List[int]
    ):
        """
        Internal method to add documents to experiment

        Args:
            experiment: Experiment instance
            document_ids: List of document IDs
        """
        for doc_id in document_ids:
            document = Document.query.filter_by(id=doc_id, document_type='document').first()
            if document:
                experiment.add_document(document)
                logger.debug(f"Added document {doc_id} to experiment {experiment.id}")
            else:
                logger.warning(f"Document {doc_id} not found, skipping")

    def _add_references_to_experiment(
        self,
        experiment: Experiment,
        reference_ids: List[int]
    ):
        """
        Internal method to add references to experiment

        Args:
            experiment: Experiment instance
            reference_ids: List of reference IDs
        """
        for ref_id in reference_ids:
            reference = Document.query.filter_by(id=ref_id, document_type='reference').first()
            if reference:
                experiment.add_reference(reference, include_in_analysis=True)
                logger.debug(f"Added reference {ref_id} to experiment {experiment.id}")
            else:
                logger.warning(f"Reference {ref_id} not found, skipping")


# Singleton instance for easy access
_experiment_service = None


def get_experiment_service() -> ExperimentService:
    """
    Get the singleton ExperimentService instance

    Returns:
        ExperimentService instance
    """
    global _experiment_service
    if _experiment_service is None:
        _experiment_service = ExperimentService()
    return _experiment_service
