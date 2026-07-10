"""
Experiment Service

Business logic for experiment operations.
Handles CRUD operations, validation, and document/reference management.
"""

import json
import logging
from uuid import UUID
from typing import List, Optional
from datetime import datetime

from app import db
from app.models import Document, Experiment
from app.models.experiment import experiment_references
from app.models.term import Term
from app.models.user import User
from app.services.base_service import (
    BaseService,
    NotFoundError,
    PermissionError,
    ServiceError,
    ValidationError,
)
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
            actor = db.session.get(User, user_id)
            if not actor:
                raise PermissionError('Permission denied')
            documents = self._resolve_creation_documents(
                data.document_uuids,
                data.document_ids,
                'document',
                actor,
            )
            references = self._resolve_creation_documents(
                data.reference_uuids,
                data.reference_ids,
                'reference',
                actor,
            )
            term = self._resolve_creation_term(data.term_id, actor)

            with db.session.begin_nested():
                experiment = Experiment(
                    name=data.name,
                    description=data.description or '',
                    experiment_type=data.experiment_type,
                    user_id=user_id,
                    term_id=term.id if term else None,
                    configuration=json.dumps(data.configuration),
                )
                self.add(experiment)
                self.flush()

                logger.info(
                    "Created experiment '%s' (ID: %s)",
                    experiment.name,
                    experiment.id,
                )

                if documents:
                    self._add_creation_documents(experiment, documents, actor)
                if references:
                    self._add_creation_references(experiment, references)

            # Commit transaction
            self.commit()

            logger.info(
                f"Experiment {experiment.id} created with "
                f"{len(documents)} documents and {len(references)} references"
            )

            return experiment

        except (NotFoundError, PermissionError, ValidationError):
            raise
        except Exception as e:
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
                # Clear existing ExperimentDocument records (v2 table)
                from app.models.experiment_document import ExperimentDocument
                ExperimentDocument.query.filter_by(experiment_id=experiment.id).delete()
                # Clear existing documents from many-to-many and add new ones
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
            from app.models.processing_artifact_group import ProcessingArtifactGroup

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
            experiment_doc_entries = ExperimentDocument.query.filter_by(
                experiment_id=experiment_id
            ).all()
            experiment_doc_ids = [ed.document_id for ed in experiment_doc_entries]

            # Identify versions to delete BEFORE we delete associations
            # (need to check other_experiments while associations still exist)
            versions_to_delete = []

            # 1. Experimental versions (created specifically for this experiment via experiment_id field)
            experimental_versions = Document.query.filter_by(
                experiment_id=experiment_id,
                version_type='experimental'
            ).all()
            versions_to_delete.extend(experimental_versions)

            # 2. Non-original versions that were associated with this experiment
            # These include 'processed' and 'experimental' versions that may not have experiment_id set
            for doc_id in experiment_doc_ids:
                doc = Document.query.get(doc_id)
                if doc and doc.version_type != 'original' and doc not in versions_to_delete:
                    # Check if this version is ONLY in this experiment (not shared)
                    other_experiments = ExperimentDocument.query.filter(
                        ExperimentDocument.document_id == doc_id,
                        ExperimentDocument.experiment_id != experiment_id
                    ).count()

                    if other_experiments == 0:
                        # Only in this experiment, safe to delete
                        versions_to_delete.append(doc)
                        logger.info(f"Will delete {doc.version_type} version {doc_id} (only in experiment {experiment_id})")

            # NOW delete all ExperimentDocument associations (after we've identified versions to delete)
            exp_docs_deleted = ExperimentDocument.query.filter_by(
                experiment_id=experiment_id
            ).delete()

            # Also delete from experiment_documents_v2 table (has separate FK constraint)
            from sqlalchemy import text
            result = db.session.execute(
                text("DELETE FROM experiment_documents_v2 WHERE experiment_id = :exp_id"),
                {"exp_id": experiment_id}
            )
            exp_docs_v2_deleted = result.rowcount
            logger.info(f"Deleted {exp_docs_v2_deleted} experiment_documents_v2 records")

            experimental_versions_count = len(versions_to_delete)

            # Handle provenance records (purge or invalidate based on settings)
            # Only handle provenance for documents being deleted, not original documents
            from app.services.provenance_service import provenance_service
            doc_ids_to_delete = [v.id for v in versions_to_delete]
            prov_result = provenance_service.delete_or_invalidate_experiment_provenance(
                experiment_id=experiment_id,
                document_ids=doc_ids_to_delete
            )
            logger.info(f"Provenance handling for experiment {experiment_id}: {prov_result}")

            # Delete ProcessingArtifactGroups for documents being deleted
            # Must do this BEFORE deleting documents to avoid FK constraint violation
            artifact_groups_deleted = 0
            for exp_version in versions_to_delete:
                groups_deleted = ProcessingArtifactGroup.query.filter_by(
                    document_id=exp_version.id
                ).delete()
                artifact_groups_deleted += groups_deleted

            if artifact_groups_deleted > 0:
                logger.info(f"Deleted {artifact_groups_deleted} processing artifact groups for experiment {experiment_id}")

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
                f"{index_count} indices, {artifact_groups_deleted} artifact groups, "
                f"{exp_docs_deleted} experiment documents, {exp_docs_v2_deleted} v2 docs, "
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

    @staticmethod
    def _resolve_creation_documents(values, ids, document_type, actor):
        values = list(dict.fromkeys(values or []))
        resolved = []
        for value in values:
            try:
                normalized = UUID(str(value))
            except (TypeError, ValueError, AttributeError) as exc:
                raise NotFoundError(
                    f'{document_type.title()} not found'
                ) from exc
            document = Document.query.filter_by(
                uuid=normalized,
                document_type=document_type,
            ).first()
            if not document:
                raise NotFoundError(f'{document_type.title()} not found')
            root = document.get_root_document()
            if not actor.can_edit_resource(root):
                raise PermissionError('Permission denied')
            if root.id not in {item.id for item in resolved}:
                resolved.append(root)
        for value in dict.fromkeys(ids or []):
            document = db.session.get(Document, value)
            if not document or document.document_type != document_type:
                raise NotFoundError(f'{document_type.title()} not found')
            root = document.get_root_document()
            if not actor.can_edit_resource(root):
                raise PermissionError('Permission denied')
            if root.id not in {item.id for item in resolved}:
                resolved.append(root)
        return resolved

    @staticmethod
    def _resolve_creation_term(term_id, actor):
        if not term_id:
            return None
        try:
            normalized = UUID(str(term_id))
        except (TypeError, ValueError, AttributeError) as exc:
            raise NotFoundError('Term not found') from exc
        term = db.session.get(Term, normalized)
        if not term:
            raise NotFoundError('Term not found')
        if (
            not actor.is_admin
            and term.created_by is not None
            and term.created_by != actor.id
        ):
            raise PermissionError('Permission denied')
        return term

    @staticmethod
    def _add_creation_documents(experiment, documents, actor):
        from app.services.inheritance_versioning_service import InheritanceVersioningService

        for document in documents:
            version, created = (
                InheritanceVersioningService.get_or_create_experiment_version(
                    original_document=document,
                    experiment_id=experiment.id,
                    user=actor,
                    commit=False,
                )
            )
            experiment.add_document(version)
            logger.info(
                'Using experimental version %s for document %s and experiment '
                '%s (%s)',
                version.id,
                document.uuid,
                experiment.id,
                'created' if created else 'existing',
            )

    @staticmethod
    def _add_creation_references(experiment, references):
        for reference in references:
            db.session.execute(experiment_references.insert().values(
                experiment_id=experiment.id,
                reference_id=reference.id,
                include_in_analysis=True,
            ))


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
