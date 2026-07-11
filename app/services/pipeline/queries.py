"""Status and artifact queries for experiment processing."""

import logging
from typing import Any, Dict
from uuid import UUID

from app.models.experiment_processing import ExperimentDocumentProcessing, ProcessingArtifact
from app.services.base_service import NotFoundError, PermissionError, ServiceError
from app.services.pipeline_access_service import PipelineAccessService

logger = logging.getLogger(__name__)


class PipelineQueryMixin:
    def get_processing_status(self, exp_doc_id: int, actor_id: int) -> Dict[str, Any]:
        """
        Get processing status for an experiment document

        Args:
            exp_doc_id: ID of the experiment document

        Returns:
            Dictionary containing processing status

        Raises:
            NotFoundError: If experiment document not found
            ServiceError: On other errors
        """
        try:
            PipelineAccessService.experiment_document(exp_doc_id, actor_id)

            # Get all processing operations
            processing_operations = ExperimentDocumentProcessing.query.filter_by(
                experiment_document_id=exp_doc_id
            ).order_by(ExperimentDocumentProcessing.created_at.desc()).all()

            return {
                'experiment_document_id': exp_doc_id,
                'processing_operations': [op.to_dict() for op in processing_operations]
            }

        except (NotFoundError, PermissionError):
            raise
        except Exception as e:
            logger.error(f"Error getting processing status: {e}", exc_info=True)
            raise ServiceError(f"Failed to get processing status: {str(e)}")

    def get_processing_artifacts(
        self,
        processing_id: UUID,
        actor_id: int,
    ) -> Dict[str, Any]:
        """
        Get artifacts for a specific processing operation

        Args:
            processing_id: UUID of the processing operation

        Returns:
            Dictionary containing artifacts

        Raises:
            NotFoundError: If processing operation not found
            ServiceError: On other errors
        """
        try:
            processing_op = PipelineAccessService.processing(
                processing_id,
                actor_id,
            )

            # Get all artifacts
            artifacts = ProcessingArtifact.query.filter_by(
                processing_id=processing_id
            ).order_by(ProcessingArtifact.artifact_index, ProcessingArtifact.created_at).all()

            return {
                'processing_id': str(processing_id),
                'processing_type': processing_op.processing_type,
                'processing_method': processing_op.processing_method,
                'artifacts': [artifact.to_dict() for artifact in artifacts]
            }

        except (NotFoundError, PermissionError):
            raise
        except Exception as e:
            logger.error(f"Error getting processing artifacts: {e}", exc_info=True)
            raise ServiceError(f"Failed to get processing artifacts: {str(e)}")
