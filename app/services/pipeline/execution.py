"""Pipeline operation creation, dispatch, and legacy embedding application."""

from datetime import datetime
import logging
from typing import Any, Dict

from app import db
from app.models.experiment_processing import ExperimentDocumentProcessing, DocumentProcessingIndex
from app.services.base_service import (
    NotFoundError,
    PermissionError,
    ServiceError,
    ValidationError,
)
from app.services.pipeline_access_service import PipelineAccessService
from .constants import SUPPORTED_PROCESSING_METHODS

logger = logging.getLogger(__name__)


class PipelineExecutionMixin:
    def apply_embeddings(
        self,
        experiment_id: int,
        document_id: int,
        user_id: int,
    ) -> Dict[str, Any]:
        """
        Apply embeddings to a document for a specific experiment

        Args:
            experiment_id: ID of the experiment
            document_id: ID of the document

        Returns:
            Dictionary containing embedding info and progress

        Raises:
            NotFoundError: If experiment or document not found
            ValidationError: If document has no content
            ServiceError: On embedding generation errors
        """
        try:
            # Get the experiment-document association
            exp_doc = PipelineAccessService.document_in_experiment(
                experiment_id,
                document_id,
                user_id,
            )

            document = exp_doc.document

            if not document.content:
                raise ValidationError('Document has no content to process')

            # Initialize embedding service
            try:
                from shared_services.embedding.embedding_service import EmbeddingService
                embedding_service = EmbeddingService()
            except ImportError:
                raise ServiceError('Embedding service not available')

            # Generate embeddings
            content = document.content
            max_length = 8000  # Conservative limit for most embedding models

            if len(content) > max_length:
                # Split into chunks and embed each
                chunks = [content[i:i+max_length] for i in range(0, len(content), max_length)]
                embeddings = []
                for chunk in chunks:
                    chunk_embedding = embedding_service.get_embedding(chunk)
                    embeddings.append(chunk_embedding)

                # Store metadata about chunked processing
                embedding_info = {
                    'type': 'chunked',
                    'chunks': len(chunks),
                    'chunk_size': max_length,
                    'model': embedding_service.get_model_name(),
                    'dimension': embedding_service.get_dimension(),
                    'experiment_id': experiment_id
                }
            else:
                # Single embedding for short documents
                embeddings = [embedding_service.get_embedding(content)]
                embedding_info = {
                    'type': 'single',
                    'model': embedding_service.get_model_name(),
                    'dimension': embedding_service.get_dimension(),
                    'experiment_id': experiment_id
                }

            # Mark embeddings as applied for this experiment
            exp_doc.mark_embeddings_applied(embedding_info)

            # Update word count if not set
            if not document.word_count:
                document.word_count = len(content.split())
                document.updated_at = datetime.utcnow()

            db.session.commit()

            logger.info(f"Applied embeddings to document {document_id} for experiment {experiment_id}: {embedding_info['type']}")

            return {
                'embedding_info': embedding_info,
                'processing_progress': exp_doc.processing_progress
            }

        except (NotFoundError, PermissionError, ValidationError):
            raise
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error applying embeddings: {e}", exc_info=True)
            raise ServiceError(f"Failed to generate embeddings: {str(e)}")

    def start_processing(
        self,
        experiment_document_id: int,
        processing_type: str,
        processing_method: str,
        user_id: int
    ) -> Dict[str, Any]:
        """
        Start a new processing operation

        Args:
            experiment_document_id: ID of the experiment document
            processing_type: Type of processing (embeddings, segmentation, entities)
            processing_method: Processing method
            user_id: ID of the user starting the processing

        Returns:
            Dictionary containing processing ID and status

        Raises:
            NotFoundError: If experiment document not found
            ValidationError: If processing already completed
            ServiceError: On processing errors
        """
        try:
            # Get the experiment document
            exp_doc = PipelineAccessService.experiment_document(
                experiment_document_id,
                user_id,
            )
            if (
                processing_type not in SUPPORTED_PROCESSING_METHODS
                or processing_method
                not in SUPPORTED_PROCESSING_METHODS[processing_type]
            ):
                raise ValidationError(
                    f'Unsupported method {processing_method} for {processing_type}'
                )

            # Check if processing already exists
            existing_processing = ExperimentDocumentProcessing.query.filter_by(
                experiment_document_id=experiment_document_id,
                processing_type=processing_type,
                processing_method=processing_method
            ).first()

            if existing_processing and existing_processing.status == 'completed':
                raise ValidationError(f'{processing_type} with {processing_method} method already completed')

            # Create new processing operation
            processing_op = ExperimentDocumentProcessing(
                experiment_document_id=experiment_document_id,
                processing_type=processing_type,
                processing_method=processing_method,
                status='pending'
            )

            # Set configuration
            config = {
                'method': processing_method,
                'created_by': user_id,
                'experiment_id': exp_doc.experiment_id,
                'document_id': exp_doc.document_id
            }
            processing_op.set_configuration(config)

            db.session.add(processing_op)
            db.session.flush()  # Assigns ID to processing_op

            # Create index entry
            index_entry = DocumentProcessingIndex(
                document_id=exp_doc.document_id,
                experiment_id=exp_doc.experiment_id,
                processing_id=processing_op.id,
                processing_type=processing_type,
                processing_method=processing_method,
                status='pending'
            )

            db.session.add(index_entry)
            db.session.commit()

            # Start processing
            processing_op.mark_started()
            index_entry.status = 'running'

            # Execute processing based on type
            try:
                if processing_type == 'embeddings':
                    self._process_embeddings(processing_op, index_entry, exp_doc, processing_method)
                elif processing_type == 'segmentation':
                    self._process_segmentation(processing_op, index_entry, exp_doc, processing_method)
                elif processing_type == 'entities':
                    self._process_entities(processing_op, index_entry, exp_doc, processing_method)
                elif processing_type == 'temporal':
                    self._process_temporal(processing_op, index_entry, exp_doc, processing_method)
                elif processing_type == 'definitions':
                    self._process_definitions(processing_op, index_entry, exp_doc, processing_method)
                elif processing_type == 'enhanced_processing':
                    self._process_enhanced(processing_op, index_entry, exp_doc, processing_method)
                else:
                    raise ValidationError(f'Unsupported processing type: {processing_type}')

                # Create provenance record for completed processing
                if processing_op.status == 'completed':
                    self._create_provenance_record(processing_op, exp_doc, user_id)

                db.session.commit()

                logger.info(f"Processing {processing_type} completed for exp_doc {experiment_document_id} with method {processing_method}")

                return {
                    'processing_id': str(processing_op.id),
                    'status': processing_op.status
                }

            except Exception as proc_error:
                # Mark processing as failed
                error_message = f"Processing failed: {str(proc_error)}"
                processing_op.mark_failed(error_message)
                index_entry.status = 'failed'
                db.session.commit()

                logger.error(f"Processing failed: {proc_error}", exc_info=True)

                return {
                    'processing_id': str(processing_op.id),
                    'status': 'failed',
                    'error': error_message
                }

        except (NotFoundError, PermissionError, ValidationError):
            raise
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error starting processing: {e}", exc_info=True)
            raise ServiceError(f"Failed to start processing: {str(e)}")
