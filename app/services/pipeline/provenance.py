"""PROV-O recording for completed pipeline operations."""

import logging

from app.models import ExperimentDocument
from app.models.experiment_processing import ExperimentDocumentProcessing

logger = logging.getLogger(__name__)


class PipelineProvenanceMixin:
    def _create_provenance_record(
        self,
        processing_op: ExperimentDocumentProcessing,
        exp_doc: ExperimentDocument,
        user_id: int
    ):
        """
        Create a provenance activity record using existing PROV-O system

        Args:
            processing_op: The completed processing operation
            exp_doc: The experiment document being processed
            user_id: ID of the user who initiated the processing
        """
        try:
            from app.services.provenance_service import ProvenanceService

            # Get results summary
            results = processing_op.get_results_summary() if hasattr(processing_op, 'get_results_summary') else {}

            # Track the processing operation using existing PROV-O infrastructure
            activity, entity = ProvenanceService.track_processing_operation(
                processing_type=processing_op.processing_type,
                processing_method=processing_op.processing_method,
                document=exp_doc.document,
                experiment_id=exp_doc.experiment_id,
                user_id=user_id,
                results=results
            )

            logger.info(
                f"Created PROV-O record for {processing_op.processing_type} processing "
                f"(activity_id: {activity.activity_id}, entity_id: {entity.entity_id})"
            )

        except Exception as e:
            # Log error but don't fail the processing
            logger.error(f"Failed to create provenance record: {e}", exc_info=True)
