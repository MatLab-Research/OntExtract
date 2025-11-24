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
from app.models.user import User
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
                term_id=data.term_id if data.term_id else None,
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
            if user_id is not None:
                user = User.query.get(user_id)
                if not user or not user.can_edit_resource(experiment):
                    raise PermissionError(f"User {user_id} does not have permission to update experiment {experiment_id}")

            # Cannot update running experiments
            if experiment.status == 'running':
                raise ValidationError("Cannot update an experiment that is currently running")

            # Update fields if provided
            if data.name is not None:
                experiment.name = data.name

            if data.description is not None:
                experiment.description = data.description

            if data.configuration is not None:
                experiment.configuration = json.dumps(data.configuration)

            # Update documents if provided
            if data.document_ids is not None:
                # Clear existing documents and add new ones
                experiment.documents = []
                self.flush()
                self._add_documents_to_experiment(experiment, data.document_ids)

            # Update references if provided
            if data.reference_ids is not None:
                # Clear existing references and add new ones
                experiment.references = []
                self.flush()
                self._add_references_to_experiment(experiment, data.reference_ids)

            # Update timestamp
            experiment.updated_at = datetime.utcnow()

            # Commit changes
            self.commit()

            logger.info(f"Updated experiment {experiment_id}")

            return experiment

        except (NotFoundError, PermissionError, ValidationError):
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
        Delete an experiment and all associated processing data

        This performs cascading deletes of:
        - Processing artifacts
        - Document processing indices
        - Experiment document processing records
        - Experiment-document associations
        - Experiment-reference associations
        - The experiment itself

        Note: Original documents are preserved (not deleted)

        Args:
            experiment_id: ID of experiment to delete
            user_id: Optional user ID for permission check

        Returns:
            True if deleted successfully

        Raises:
            NotFoundError: If experiment doesn't exist
            PermissionError: If user doesn't have permission
            ValidationError: If experiment cannot be deleted (e.g., running)
            ServiceError: If deletion fails
        """
        try:
            # Get experiment
            experiment = self.get_experiment(experiment_id)

            # Check permissions if user_id provided
            if user_id is not None:
                user = User.query.get(user_id)
                if not user or not user.can_delete_resource(experiment):
                    raise PermissionError(f"User {user_id} does not have permission to delete experiment {experiment_id}")

            # Cannot delete running experiments
            if experiment.status == 'running':
                raise ValidationError("Cannot delete an experiment that is currently running")

            # Import models for cascading deletes (avoid circular imports)
            from app.models.experiment_document import ExperimentDocument
            from app.models.experiment_processing import (
                ExperimentDocumentProcessing,
                ProcessingArtifact,
                DocumentProcessingIndex
            )

            # Delete all processing artifacts first (most dependent)
            # Get all processing operations for this experiment's documents
            processing_ops = db.session.query(ExperimentDocumentProcessing).join(
                ExperimentDocument,
                ExperimentDocumentProcessing.experiment_document_id == ExperimentDocument.id
            ).filter(
                ExperimentDocument.experiment_id == experiment_id
            ).all()

            artifact_count = 0
            index_count = 0
            processing_count = len(processing_ops)

            for processing_op in processing_ops:
                # Delete all artifacts for this processing operation
                artifacts_deleted = ProcessingArtifact.query.filter_by(
                    processing_id=processing_op.id
                ).delete()
                artifact_count += artifacts_deleted

                # Delete index entries for this processing operation
                indices_deleted = DocumentProcessingIndex.query.filter_by(
                    processing_id=processing_op.id
                ).delete()
                index_count += indices_deleted

                # Delete the processing operation itself
                db.session.delete(processing_op)

            # Get all documents associated with this experiment BEFORE deleting associations
            from app.models.document import Document
            experiment_doc_ids = [ed.document_id for ed in ExperimentDocument.query.filter_by(
                experiment_id=experiment_id
            ).all()]

            # Delete all ExperimentDocument associations
            exp_docs_deleted = ExperimentDocument.query.filter_by(
                experiment_id=experiment_id
            ).delete()

            # Delete experimental version documents (they are specific to this experiment)
            # Must do this BEFORE clearing relationships to avoid constraint violation

            versions_to_delete = []

            # 1. Experimental versions (created specifically for this experiment)
            experimental_versions = Document.query.filter_by(
                experiment_id=experiment_id,
                version_type='experimental'
            ).all()
            versions_to_delete.extend(experimental_versions)

            # 2. Processed versions (e.g., cleaned with LLM) that are ONLY in this experiment
            # These should be deleted because they were created as part of this experiment's workflow
            for doc_id in experiment_doc_ids:
                doc = Document.query.get(doc_id)
                if doc and doc.version_type == 'processed' and doc.source_document_id:
                    # Check if this processed version is ONLY in this experiment
                    other_experiments = ExperimentDocument.query.filter(
                        ExperimentDocument.document_id == doc_id,
                        ExperimentDocument.experiment_id != experiment_id
                    ).count()

                    if other_experiments == 0:
                        # Only in this experiment, safe to delete
                        versions_to_delete.append(doc)
                        logger.info(f"Will delete processed version {doc_id} (only in experiment {experiment_id})")

            experimental_versions_count = len(versions_to_delete)

            # First, remove them from the experiment relationship
            # This prevents SQLAlchemy from trying to set experiment_id=NULL
            for exp_version in versions_to_delete:
                if exp_version in experiment.documents:
                    experiment.documents.remove(exp_version)

            # Now delete the documents themselves
            for exp_version in versions_to_delete:
                db.session.delete(exp_version)

            # Clear any remaining references (should just be original documents now)
            experiment.documents = []
            experiment.references = []
            self.flush()

            # Finally delete the experiment itself
            self.delete(experiment)

            # Commit all deletions
            self.commit()

            logger.info(
                f"Deleted experiment {experiment_id} with cascading deletes: "
                f"{processing_count} processing ops, {artifact_count} artifacts, "
                f"{index_count} indices, {exp_docs_deleted} experiment documents, "
                f"{experimental_versions_count} experimental version documents"
            )

            return True

        except (NotFoundError, PermissionError, ValidationError):
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

        Creates experimental version (v2) for each document BEFORE adding to experiment.
        Original documents (v1) stay pristine.

        Args:
            experiment: Experiment instance
            document_ids: List of document IDs
        """
        from app.services.inheritance_versioning_service import InheritanceVersioningService
        from flask_login import current_user

        for doc_id in document_ids:
            document = Document.query.filter_by(id=doc_id, document_type='document').first()
            if document:
                # Create experimental version (v2) BEFORE adding to experiment
                exp_version, created = InheritanceVersioningService.get_or_create_experiment_version(
                    original_document=document,
                    experiment_id=experiment.id,
                    user=current_user
                )

                # Add experimental version (v2) to experiment, NOT original (v1)
                experiment.add_document(exp_version)

                if created:
                    logger.info(f"Created experimental version {exp_version.id} (v{exp_version.version_number}) "
                               f"from document {document.id} for experiment {experiment.id}")
                else:
                    logger.debug(f"Using existing experimental version {exp_version.id} for experiment {experiment.id}")
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
