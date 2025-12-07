"""
Pipeline Service

Handles business logic for document processing pipeline operations.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import UUID
import logging

from app import db
from app.models import Document, Experiment, ExperimentDocument, ExperimentOrchestrationRun
from app.models.experiment_processing import ExperimentDocumentProcessing, ProcessingArtifact, DocumentProcessingIndex
from app.services.base_service import BaseService, ServiceError, NotFoundError, ValidationError

logger = logging.getLogger(__name__)

# Mapping from LLM tool names to standard operation types/methods
# This ensures consistent display between LLM orchestration and manual processing
# NOTE: Methods should match the display labels in app/__init__.py format_tool_name filter
LLM_TOOL_TO_OPERATION_MAP = {
    "extract_entities_spacy": {"type": "entities", "method": "spacy"},
    "extract_temporal": {"type": "temporal", "method": "spacy"},
    "extract_definitions": {"type": "definitions", "method": "pattern"},
    "extract_causal": {"type": "causal", "method": "spacy"},
    "period_aware_embedding": {"type": "embeddings", "method": "period_aware"},
    "segment_paragraph": {"type": "segmentation", "method": "paragraph"},
    "segment_sentence": {"type": "segmentation", "method": "sentence"},
}


class PipelineService(BaseService):
    """Service for managing document processing pipeline"""

    def get_pipeline_overview(self, experiment_id: int) -> Dict[str, Any]:
        """
        Get pipeline overview data

        Args:
            experiment_id: ID of the experiment

        Returns:
            Dictionary containing pipeline overview data

        Raises:
            NotFoundError: If experiment not found
            ServiceError: On other errors
        """
        try:
            experiment = Experiment.query.filter_by(id=experiment_id).first()
            if not experiment:
                raise NotFoundError(f"Experiment {experiment_id} not found")

            # Get most recent orchestration run for this experiment
            orchestration_run = ExperimentOrchestrationRun.query.filter_by(
                experiment_id=experiment_id
            ).order_by(ExperimentOrchestrationRun.started_at.desc()).first()

            # Extract orchestration results (JSONB field with document_id -> {tool_name -> results})
            orchestration_results = {}
            if orchestration_run and orchestration_run.processing_results:
                orchestration_results = orchestration_run.processing_results

            # Get experiment documents
            exp_docs = ExperimentDocument.query.filter_by(experiment_id=experiment_id).all()

            # Group documents by root to show only latest version
            # Key: root_document_id, Value: list of (exp_doc, document) tuples
            doc_families = {}
            for exp_doc in exp_docs:
                doc = exp_doc.document
                # Get root document ID (either the document itself or its source)
                root_id = doc.source_document_id if doc.source_document_id else doc.id

                if root_id not in doc_families:
                    doc_families[root_id] = []
                doc_families[root_id].append((exp_doc, doc))

            # For each family, select only the latest version
            latest_exp_docs = []
            for root_id, family_members in doc_families.items():
                # Sort by version_number (desc) and pick the first one
                family_members.sort(key=lambda x: x[1].version_number or 0, reverse=True)
                latest_exp_docs.append(family_members[0])  # (exp_doc, doc) tuple

            # Build processed documents list
            processed_docs = []
            for exp_doc, doc in latest_exp_docs:
                # Get processing operations - collect as list with methods
                operations_list = []

                # 1. Check manual processing operations (from process_document page buttons)
                manual_ops = ExperimentDocumentProcessing.query.filter_by(
                    experiment_document_id=exp_doc.id
                ).all()

                for op in manual_ops:
                    if op.status == 'completed':
                        operations_list.append({
                            'type': op.processing_type,
                            'method': op.processing_method,
                            'source': 'manual'
                        })

                # 2. Check new experiment processing system (DocumentProcessingIndex)
                index_entries = DocumentProcessingIndex.query.filter_by(
                    document_id=doc.id,
                    experiment_id=exp_doc.experiment_id
                ).all()

                for entry in index_entries:
                    if entry.status == 'completed':
                        operations_list.append({
                            'type': entry.processing_type,
                            'method': entry.processing_method,
                            'source': 'experiment'
                        })

                # 3. Merge orchestration results (LLM processing)
                # Map LLM tool names to standard operation types for consistent display
                doc_id_str = str(doc.id)
                if doc_id_str in orchestration_results:
                    llm_ops = orchestration_results[doc_id_str]
                    for tool_name, tool_result in llm_ops.items():
                        if tool_result.get('status') == 'executed':
                            # Map LLM tool name to standard operation type/method
                            op_mapping = LLM_TOOL_TO_OPERATION_MAP.get(tool_name)
                            if op_mapping:
                                operations_list.append({
                                    'type': op_mapping['type'],
                                    'method': op_mapping['method'],
                                    'source': 'llm'
                                })
                            else:
                                # Fallback for unknown tools
                                operations_list.append({
                                    'type': tool_name,
                                    'method': 'llm',
                                    'source': 'llm'
                                })

                # Deduplicate operations by (type, method) combination
                seen = set()
                unique_operations = []
                for op in operations_list:
                    key = (op['type'], op['method'])
                    if key not in seen:
                        seen.add(key)
                        unique_operations.append(op)
                operations_list = unique_operations

                # Calculate processing progress based on unique operation types completed
                # Only count the 5 standard processing types for progress
                STANDARD_OPERATION_TYPES = {'segmentation', 'entities', 'temporal', 'embeddings', 'definitions'}
                unique_types = set(op['type'] for op in operations_list)
                completed_standard_types = unique_types & STANDARD_OPERATION_TYPES
                total_operation_types = len(STANDARD_OPERATION_TYPES)
                completed_operation_types = len(completed_standard_types)
                processing_progress = int((completed_operation_types / total_operation_types) * 100) if total_operation_types > 0 else 0

                # Determine overall status
                if completed_operation_types == total_operation_types:
                    status = 'completed'
                elif completed_operation_types > 0:
                    status = 'processing'
                else:
                    status = 'pending'

                # Check if document has completed LLM cleanup
                from app.models import ProcessingJob
                has_cleanup = ProcessingJob.query.filter_by(
                    document_id=doc.id,
                    job_type='clean_text',
                    status='completed'
                ).first() is not None

                # Add LLM cleanup to operations if completed
                if has_cleanup:
                    operations_list.append({
                        'type': 'cleanup',
                        'method': 'llm',
                        'source': 'llm'
                    })

                # Calculate total operations from both systems
                total_ops = len(manual_ops) + len(index_entries)
                completed_ops = sum(1 for op in manual_ops if op.status == 'completed') + \
                                sum(1 for entry in index_entries if entry.status == 'completed')

                processed_docs.append({
                    'id': doc.id,
                    'uuid': doc.uuid,  # Add UUID for template URL generation
                    'exp_doc_id': exp_doc.id,
                    'name': doc.original_filename or doc.title,
                    'file_type': doc.file_type or doc.content_type,
                    'word_count': doc.word_count or 0,
                    'status': status,
                    'processing_progress': processing_progress,
                    'created_at': doc.created_at,
                    'operations': operations_list,  # List of completed operations with methods
                    'total_operations': total_ops,
                    'completed_operations': completed_ops,
                    'has_cleanup': has_cleanup,  # Track if LLM cleanup has been done
                    'version_number': doc.version_number or 1,  # Track version
                    'version_type': doc.version_type  # Track version type (processed, experimental, etc.)
                })

            # Calculate overall progress
            completed_count = sum(1 for doc in processed_docs if doc['status'] == 'completed')
            total_count = len(processed_docs)
            progress_percentage = (completed_count / total_count * 100) if total_count > 0 else 0

            logger.info(f"Pipeline overview for experiment {experiment_id}: {completed_count}/{total_count} documents completed")

            return {
                'experiment': experiment,
                'documents': processed_docs,
                'total_count': total_count,
                'completed_count': completed_count,
                'progress_percentage': progress_percentage,
                'orchestration_run': orchestration_run  # Include for attribution/display
            }

        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error getting pipeline overview for experiment {experiment_id}: {e}", exc_info=True)
            raise ServiceError(f"Failed to get pipeline overview: {str(e)}")

    def get_process_document_data(self, experiment_id: int, document_id: int) -> Dict[str, Any]:
        """
        Get data for processing a specific document

        Args:
            experiment_id: ID of the experiment
            document_id: ID of the document

        Returns:
            Dictionary containing document processing data

        Raises:
            NotFoundError: If experiment or document not found
            ValidationError: If document not in experiment
            ServiceError: On other errors
        """
        try:
            experiment = Experiment.query.filter_by(id=experiment_id).first()
            if not experiment:
                raise NotFoundError(f"Experiment {experiment_id} not found")

            # Get the experiment-document association
            exp_doc = ExperimentDocument.query.filter_by(
                experiment_id=experiment_id,
                document_id=document_id
            ).first()
            if not exp_doc:
                raise NotFoundError(f"Document {document_id} not found in experiment {experiment_id}")

            document = exp_doc.document

            # CRITICAL: If this is the original document, check if an experiment version exists
            # We want to show the experiment version (with processing) instead of the original
            if not document.experiment_id:  # Original documents don't have experiment_id
                experiment_version = Document.query.filter_by(
                    source_document_id=document.id,
                    experiment_id=experiment_id,
                    version_type='experimental'
                ).first()

                if experiment_version:
                    logger.info(f"Switching from original document {document.id} to experiment version {experiment_version.id} for experiment {experiment_id}")
                    document = experiment_version
                    # Note: exp_doc still points to the original document's association, which is correct

            # Get processing operations (manual/user processing)
            manual_operations = ExperimentDocumentProcessing.query.filter_by(
                experiment_document_id=exp_doc.id
            ).order_by(ExperimentDocumentProcessing.created_at.desc()).all()

            # Get orchestration results for LLM-processed operations
            orchestration_run = ExperimentOrchestrationRun.query.filter_by(
                experiment_id=experiment_id
            ).order_by(ExperimentOrchestrationRun.started_at.desc()).first()

            llm_operations = {}
            if orchestration_run and orchestration_run.processing_results:
                doc_id_str = str(document_id)
                if doc_id_str in orchestration_run.processing_results:
                    llm_operations = orchestration_run.processing_results[doc_id_str]

            # Get ProcessingArtifactGroups for this document (includes LLM orchestration artifacts)
            from app.models.processing_artifact_group import ProcessingArtifactGroup
            artifact_groups = ProcessingArtifactGroup.query.filter_by(
                document_id=document.id
            ).order_by(ProcessingArtifactGroup.created_at.desc()).all()

            # Create a unified list of processing operations
            # Convert artifact groups to operation-like objects for template compatibility
            processing_operations = list(manual_operations)

            # Track what we already have to avoid duplicates
            existing_ops = {(op.processing_type, op.processing_method) for op in manual_operations}

            # Add artifact groups that aren't already in manual_operations
            for group in artifact_groups:
                # Map artifact_type to processing_type (they should match)
                processing_type = group.artifact_type
                processing_method = group.method_key

                if (processing_type, processing_method) not in existing_ops:
                    # Create a simple object that mimics ExperimentDocumentProcessing attributes
                    class ArtifactGroupOp:
                        def __init__(self, group):
                            self.id = group.id
                            self.processing_type = group.artifact_type
                            self.processing_method = group.method_key
                            self.status = group.status
                            self.started_at = group.created_at
                            self.completed_at = group.updated_at if group.status == 'completed' else None
                            self.created_at = group.created_at
                            self.metadata = group.metadata_json or {}
                            self.source = 'llm_orchestration' if self.metadata.get('created_by') == 'llm_orchestration' else 'artifact_group'

                    processing_operations.append(ArtifactGroupOp(group))
                    existing_ops.add((processing_type, processing_method))

            # Get all experiment documents for navigation
            all_exp_docs = ExperimentDocument.query.filter_by(experiment_id=experiment_id).all()
            all_doc_ids = [ed.document_id for ed in all_exp_docs]

            try:
                doc_index = all_doc_ids.index(document_id)
            except ValueError:
                raise ValidationError('Document not found in this experiment')

            # Prepare navigation info
            has_previous = doc_index > 0
            has_next = doc_index < len(all_doc_ids) - 1
            previous_doc_id = all_doc_ids[doc_index - 1] if has_previous else None
            next_doc_id = all_doc_ids[doc_index + 1] if has_next else None

            # Calculate processing progress - use same 5 standard types as document_pipeline
            STANDARD_OPERATION_TYPES = {'segmentation', 'entities', 'temporal', 'embeddings', 'definitions'}
            completed_types = set()
            for op in processing_operations:
                if op.status == 'completed':
                    completed_types.add(op.processing_type)

            # Only count standard types for progress
            completed_standard_types = completed_types & STANDARD_OPERATION_TYPES
            total_processing_types = len(STANDARD_OPERATION_TYPES)
            processing_progress = int((len(completed_standard_types) / total_processing_types) * 100)

            logger.info(f"Document {document_id} progress: {processing_progress}% ({len(completed_standard_types)}/{total_processing_types} types)")

            # In experiment context, we only show the experiment version (no version switcher)
            # The general document route (/input/document/{uuid}) shows all versions
            all_versions = []
            is_latest_version = True

            # Check if document has completed LLM cleanup
            from app.models import ProcessingJob
            has_cleanup = ProcessingJob.query.filter_by(
                document_id=document.id,
                job_type='clean_text',
                status='completed'
            ).first() is not None

            return {
                'experiment': experiment,
                'document': document,
                'experiment_document': exp_doc,
                'processing_operations': processing_operations,
                'llm_operations': llm_operations,  # Add LLM processing operations
                'processing_progress': processing_progress,
                'doc_index': doc_index,
                'total_docs': len(all_doc_ids),
                'has_previous': has_previous,
                'has_next': has_next,
                'previous_doc_id': previous_doc_id,
                'next_doc_id': next_doc_id,
                'all_versions': all_versions,
                'is_latest_version': is_latest_version,
                'has_cleanup': has_cleanup
            }

        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Error getting document processing data: {e}", exc_info=True)
            raise ServiceError(f"Failed to get document processing data: {str(e)}")

    def apply_embeddings(self, experiment_id: int, document_id: int) -> Dict[str, Any]:
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
            exp_doc = ExperimentDocument.query.filter_by(
                experiment_id=experiment_id,
                document_id=document_id
            ).first()
            if not exp_doc:
                raise NotFoundError(f"Document {document_id} not found in experiment {experiment_id}")

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

        except (NotFoundError, ValidationError):
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
            exp_doc = ExperimentDocument.query.filter_by(id=experiment_document_id).first()
            if not exp_doc:
                raise NotFoundError(f"Experiment document {experiment_document_id} not found")

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

        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error starting processing: {e}", exc_info=True)
            raise ServiceError(f"Failed to start processing: {str(e)}")

    def get_processing_status(self, exp_doc_id: int) -> Dict[str, Any]:
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
            exp_doc = ExperimentDocument.query.filter_by(id=exp_doc_id).first()
            if not exp_doc:
                raise NotFoundError(f"Experiment document {exp_doc_id} not found")

            # Get all processing operations
            processing_operations = ExperimentDocumentProcessing.query.filter_by(
                experiment_document_id=exp_doc_id
            ).order_by(ExperimentDocumentProcessing.created_at.desc()).all()

            return {
                'experiment_document_id': exp_doc_id,
                'processing_operations': [op.to_dict() for op in processing_operations]
            }

        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error getting processing status: {e}", exc_info=True)
            raise ServiceError(f"Failed to get processing status: {str(e)}")

    def get_processing_artifacts(self, processing_id: UUID) -> Dict[str, Any]:
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
            processing_op = ExperimentDocumentProcessing.query.filter_by(id=processing_id).first()
            if not processing_op:
                raise NotFoundError(f"Processing operation {processing_id} not found")

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

        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error getting processing artifacts: {e}", exc_info=True)
            raise ServiceError(f"Failed to get processing artifacts: {str(e)}")

    # Private helper methods for each processing type

    def _process_embeddings(
        self,
        processing_op: ExperimentDocumentProcessing,
        index_entry: DocumentProcessingIndex,
        exp_doc: ExperimentDocument,
        processing_method: str
    ):
        """
        Process embeddings for a document - hierarchical approach

        Creates:
        1. Document-level embedding (always) - for document similarity/clustering
        2. Segment-level embeddings (if segments exist) - for fine-grained search
        """
        from app.services.experiment_embedding_service import ExperimentEmbeddingService
        embedding_service = ExperimentEmbeddingService()

        # Check if method is available
        if not embedding_service.is_method_available(processing_method):
            raise RuntimeError(f"Embedding method '{processing_method}' not available")

        content = exp_doc.document.content or "No content available"
        embeddings_created = 0
        total_tokens = 0

        # Get document year for period-aware embeddings
        doc_year = None
        if exp_doc.document.publication_date:
            try:
                doc_year = exp_doc.document.publication_date.year
            except AttributeError:
                pass

        # STEP 1: Always create document-level embedding
        text_to_embed = content[:2000]  # First 2000 chars represents the document
        doc_embedding_result = embedding_service.generate_embeddings(text_to_embed, processing_method, year=doc_year)

        doc_embedding_artifact = ProcessingArtifact(
            processing_id=processing_op.id,
            document_id=exp_doc.document_id,
            artifact_type='embedding_vector',
            artifact_index=-1  # -1 indicates document-level embedding
        )
        doc_embedding_artifact.set_content({
            'text': text_to_embed,
            'vector': doc_embedding_result['vector'],
            'model': doc_embedding_result['model'],
            'embedding_level': 'document'
        })
        doc_metadata = {
            'dimensions': doc_embedding_result['dimensions'],
            'method': processing_method,
            'chunk_size': len(text_to_embed),
            'original_length': len(content),
            'tokens_used': doc_embedding_result.get('tokens_used', 'N/A'),
            'embedding_level': 'document'
        }
        # Add period-aware metadata if available
        if doc_embedding_result.get('period_category'):
            doc_metadata['period_category'] = doc_embedding_result['period_category']
            doc_metadata['document_year'] = doc_embedding_result.get('document_year')
            doc_metadata['selection_reason'] = doc_embedding_result.get('selection_reason')
            doc_metadata['selection_confidence'] = doc_embedding_result.get('selection_confidence')
            # Extended period-aware metadata
            doc_metadata['model_full'] = doc_embedding_result.get('model_full')
            doc_metadata['model_description'] = doc_embedding_result.get('model_description')
            doc_metadata['expected_dimension'] = doc_embedding_result.get('expected_dimension')
            doc_metadata['handles_archaic'] = doc_embedding_result.get('handles_archaic')
            doc_metadata['era'] = doc_embedding_result.get('era')
            doc_metadata['intended_model'] = doc_embedding_result.get('intended_model')
            doc_metadata['fallback_used'] = doc_embedding_result.get('fallback_used', False)
        doc_embedding_artifact.set_metadata(doc_metadata)
        db.session.add(doc_embedding_artifact)
        db.session.flush()  # Get the ID for linking

        embeddings_created += 1
        total_tokens += doc_embedding_result.get('tokens_used', 0) if isinstance(doc_embedding_result.get('tokens_used'), int) else 0

        document_embedding_id = str(doc_embedding_artifact.id)

        # STEP 2: Create segment-level embeddings if segments exist
        existing_segments = ProcessingArtifact.query.filter(
            ProcessingArtifact.document_id == exp_doc.document_id,
            ProcessingArtifact.artifact_type == 'text_segment'
        ).order_by(ProcessingArtifact.artifact_index).all()

        segment_embeddings_created = 0

        if existing_segments:
            for idx, segment_artifact in enumerate(existing_segments):
                segment_data = segment_artifact.get_content()
                text_to_embed = segment_data.get('text', '')[:2000]

                if not text_to_embed:
                    continue

                # Generate embedding for this segment
                embedding_result = embedding_service.generate_embeddings(text_to_embed, processing_method, year=doc_year)

                # Create segment embedding artifact
                embedding_artifact = ProcessingArtifact(
                    processing_id=processing_op.id,
                    document_id=exp_doc.document_id,
                    artifact_type='embedding_vector',
                    artifact_index=idx
                )
                embedding_artifact.set_content({
                    'text': text_to_embed,
                    'vector': embedding_result['vector'],
                    'model': embedding_result['model'],
                    'segment_index': idx,
                    'embedding_level': 'segment'
                })
                segment_metadata = {
                    'dimensions': embedding_result['dimensions'],
                    'method': processing_method,
                    'chunk_size': len(text_to_embed),
                    'tokens_used': embedding_result.get('tokens_used', 'N/A'),
                    'source_segment_id': str(segment_artifact.id),
                    'document_embedding_id': document_embedding_id,  # Link to parent
                    'embedding_level': 'segment'
                }
                # Add period-aware metadata if available
                if embedding_result.get('period_category'):
                    segment_metadata['period_category'] = embedding_result['period_category']
                    segment_metadata['document_year'] = embedding_result.get('document_year')
                    segment_metadata['selection_reason'] = embedding_result.get('selection_reason')
                    segment_metadata['selection_confidence'] = embedding_result.get('selection_confidence')
                    # Extended period-aware metadata
                    segment_metadata['model_full'] = embedding_result.get('model_full')
                    segment_metadata['model_description'] = embedding_result.get('model_description')
                    segment_metadata['expected_dimension'] = embedding_result.get('expected_dimension')
                    segment_metadata['handles_archaic'] = embedding_result.get('handles_archaic')
                    segment_metadata['era'] = embedding_result.get('era')
                    segment_metadata['intended_model'] = embedding_result.get('intended_model')
                    segment_metadata['fallback_used'] = embedding_result.get('fallback_used', False)
                embedding_artifact.set_metadata(segment_metadata)
                db.session.add(embedding_artifact)
                embeddings_created += 1
                segment_embeddings_created += 1
                total_tokens += embedding_result.get('tokens_used', 0) if isinstance(embedding_result.get('tokens_used'), int) else 0

        # Mark processing as completed
        processing_op.mark_completed({
            'embedding_method': processing_method,
            'dimensions': doc_embedding_result['dimensions'],
            'total_embeddings': embeddings_created,
            'document_embeddings': 1,
            'segment_embeddings': segment_embeddings_created,
            'total_tokens': total_tokens if total_tokens > 0 else 'N/A',
            'model_used': doc_embedding_result['model'],
            'note': f'Hierarchical: 1 document + {segment_embeddings_created} segment embeddings'
        })
        index_entry.status = 'completed'

    def _process_segmentation(
        self,
        processing_op: ExperimentDocumentProcessing,
        index_entry: DocumentProcessingIndex,
        exp_doc: ExperimentDocument,
        processing_method: str
    ):
        """Process segmentation for a document"""
        if not exp_doc.document.content:
            processing_op.mark_completed({'segments_created': 0})
            index_entry.status = 'completed'
            return

        import nltk
        from nltk.tokenize import sent_tokenize
        import re

        # Ensure NLTK data is available
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt_tab', quiet=True)

        content = exp_doc.document.content
        segments = []

        if processing_method == 'paragraph':
            # Enhanced paragraph splitting
            normalized_content = re.sub(r'\r\n|\r', '\n', content.strip())
            normalized_content = re.sub(r'\n{3,}', '\n\n', normalized_content)
            initial_paragraphs = re.split(r'\n\s*\n', normalized_content)

            processed_paragraphs = []
            for para in initial_paragraphs:
                para = para.strip()
                if len(para) < 20:
                    continue

                sentences_in_para = sent_tokenize(para)

                if len(sentences_in_para) > 1 or len(para) > 100:
                    processed_paragraphs.append(para)
                elif len(para) > 50:
                    processed_paragraphs.append(para)

            segments = processed_paragraphs

        elif processing_method == 'sentence':
            # NLTK sentence tokenization
            segments = sent_tokenize(content)
            segments = [s.strip() for s in segments if len(s.strip()) > 15]

        else:  # semantic
            # spaCy semantic chunking
            import spacy
            nlp = spacy.load('en_core_web_sm')
            doc = nlp(content)

            current_chunk = []
            chunks = []

            for sent in doc.sents:
                current_chunk.append(sent.text.strip())
                if len(current_chunk) >= 3 or (sent.ents and len(current_chunk) >= 2):
                    chunks.append(' '.join(current_chunk))
                    current_chunk = []

            if current_chunk:
                chunks.append(' '.join(current_chunk))

            segments = [c for c in chunks if len(c.strip()) > 20]

        # Create artifacts for all segments
        for i, segment in enumerate(segments):
            if segment.strip():
                artifact = ProcessingArtifact(
                    processing_id=processing_op.id,
                    document_id=exp_doc.document_id,
                    artifact_type='text_segment',
                    artifact_index=i
                )
                artifact.set_content({
                    'text': segment.strip(),
                    'segment_type': processing_method,
                    'position': i
                })
                artifact.set_metadata({
                    'method': processing_method,
                    'length': len(segment),
                    'word_count': len(segment.split())
                })
                db.session.add(artifact)

        # Calculate metrics
        if segments:
            avg_length = sum(len(seg) for seg in segments) // len(segments)
            total_words = sum(len(seg.split()) for seg in segments)
            avg_words = total_words // len(segments)
        else:
            avg_length = 0
            avg_words = 0

        # Determine service used
        if processing_method == 'paragraph':
            service_used = "NLTK-Enhanced Paragraph Detection"
            model_info = "Punkt tokenizer + smart filtering"
        elif processing_method == 'sentence':
            service_used = "NLTK Punkt Tokenizer"
            model_info = "Pre-trained sentence boundary detection"
        else:
            service_used = "spaCy NLP + NLTK"
            model_info = "en_core_web_sm + punkt tokenizer"

        processing_op.mark_completed({
            'segmentation_method': processing_method,
            'segments_created': len(segments),
            'avg_segment_length': avg_length,
            'avg_words_per_segment': avg_words,
            'total_tokens': sum(len(seg.split()) for seg in segments),
            'service_used': service_used,
            'model_info': model_info
        })
        index_entry.status = 'completed'

    def _process_entities(
        self,
        processing_op: ExperimentDocumentProcessing,
        index_entry: DocumentProcessingIndex,
        exp_doc: ExperimentDocument,
        processing_method: str
    ):
        """Process entity extraction for a document"""
        content = exp_doc.document.content
        extracted_entities = []

        if processing_method == 'spacy':
            extracted_entities = self._extract_entities_spacy(content)
        elif processing_method == 'nltk':
            extracted_entities = self._extract_entities_nltk(content)
        else:  # llm method
            extracted_entities = self._extract_entities_llm(content, exp_doc)

        # Remove duplicates
        unique_entities = []
        seen_texts = set()

        for entity in extracted_entities:
            entity_key = entity['entity'].lower().strip()
            if entity_key not in seen_texts and len(entity_key) > 1:
                seen_texts.add(entity_key)
                unique_entities.append(entity)

        # Sort by confidence and position
        unique_entities.sort(key=lambda x: (-x['confidence'], x['start_char']))

        # Create artifacts
        for i, entity_data in enumerate(unique_entities):
            artifact = ProcessingArtifact(
                processing_id=processing_op.id,
                document_id=exp_doc.document_id,
                artifact_type='extracted_entity',
                artifact_index=i
            )
            artifact.set_content({
                'entity': entity_data['entity'],
                'entity_type': entity_data['type'],
                'confidence': entity_data['confidence'],
                'context': entity_data['context'],
                'start_char': entity_data['start_char'],
                'end_char': entity_data['end_char']
            })
            artifact.set_metadata({
                'method': processing_method,
                'extraction_confidence': entity_data['confidence'],
                'character_position': f"{entity_data['start_char']}-{entity_data['end_char']}"
            })
            db.session.add(artifact)

        # Determine service info
        if processing_method == 'spacy':
            service_used = "spaCy NLP + Enhanced Extraction"
            model_info = "en_core_web_sm + noun phrase extraction"
        elif processing_method == 'nltk':
            service_used = "NLTK Named Entity Chunker"
            model_info = "maxent_ne_chunker + POS tagging"
        else:
            service_used = "LangExtract + Gemini Integration"
            model_info = "Google Gemini-1.5-flash with character-level positioning"

        # Extract unique entity types
        entity_types = list(set([e['type'] for e in unique_entities]))

        processing_op.mark_completed({
            'extraction_method': processing_method,
            'entities_found': len(unique_entities),
            'entity_types': entity_types,
            'service_used': service_used,
            'model_info': model_info,
            'avg_confidence': sum(e['confidence'] for e in unique_entities) / len(unique_entities) if unique_entities else 0
        })
        index_entry.status = 'completed'

    def _extract_entities_spacy(self, content: str) -> List[Dict[str, Any]]:
        """Extract entities using spaCy"""
        import spacy
        from collections import defaultdict

        nlp = spacy.load('en_core_web_sm')
        doc = nlp(content)

        extracted_entities = []
        seen_entities = set()

        # Extract named entities
        for ent in doc.ents:
            entity_text = ent.text.strip()
            entity_key = (entity_text.lower(), ent.label_)

            if len(entity_text) < 2 or entity_key in seen_entities:
                continue

            seen_entities.add(entity_key)

            sent_text = ent.sent.text.strip()
            ent_start_in_sent = ent.start_char - ent.sent.start_char
            ent_end_in_sent = ent.end_char - ent.sent.start_char

            context_start = max(0, ent_start_in_sent - 50)
            context_end = min(len(sent_text), ent_end_in_sent + 50)
            context = sent_text[context_start:context_end].strip()

            extracted_entities.append({
                'entity': entity_text,
                'type': ent.label_,
                'confidence': 0.85,
                'context': context,
                'start_char': ent.start_char,
                'end_char': ent.end_char
            })

        # Extract noun phrases as concepts
        for np in doc.noun_chunks:
            np_text = np.text.strip()
            np_key = np_text.lower()

            if (len(np_text) < 3 or len(np_text) > 100 or
                any(np_key in seen_ent[0] for seen_ent in seen_entities)):
                continue

            if (any(token.pos_ in ['PROPN', 'NOUN'] for token in np) and
                not all(token.is_stop for token in np)):

                context_start = max(0, np.start_char - 50)
                context_end = min(len(content), np.end_char + 50)
                context = content[context_start:context_end].strip()

                extracted_entities.append({
                    'entity': np_text,
                    'type': 'CONCEPT',
                    'confidence': 0.65,
                    'context': context,
                    'start_char': np.start_char,
                    'end_char': np.end_char
                })

        return extracted_entities

    def _extract_entities_nltk(self, content: str) -> List[Dict[str, Any]]:
        """Extract entities using NLTK"""
        import nltk
        from nltk.tokenize import sent_tokenize, word_tokenize
        from nltk.tag import pos_tag
        from nltk.chunk import ne_chunk
        from nltk.tree import Tree

        # Ensure NLTK data
        for resource in ['punkt', 'averaged_perceptron_tagger', 'maxent_ne_chunker', 'words']:
            try:
                nltk.data.find(f'tokenizers/{resource}' if resource == 'punkt' else f'taggers/{resource}' if 'tagger' in resource else f'chunkers/{resource}' if 'chunker' in resource else f'corpora/{resource}')
            except LookupError:
                nltk.download(resource if resource != 'punkt' else 'punkt_tab', quiet=True)

        extracted_entities = []
        sentences = sent_tokenize(content)
        char_offset = 0

        for sent in sentences:
            words = word_tokenize(sent)
            pos_tags = pos_tag(words)
            chunks = ne_chunk(pos_tags, binary=False)

            word_offset = 0
            for chunk in chunks:
                if isinstance(chunk, Tree):
                    entity_words = [word for word, pos in chunk.leaves()]
                    entity_text = ' '.join(entity_words)
                    entity_type = chunk.label()

                    entity_start = sent.find(entity_text, word_offset)
                    if entity_start != -1:
                        context_start = max(0, entity_start - 50)
                        context_end = min(len(sent), entity_start + len(entity_text) + 50)
                        context = sent[context_start:context_end].strip()

                        extracted_entities.append({
                            'entity': entity_text,
                            'type': entity_type,
                            'confidence': 0.70,
                            'context': context,
                            'start_char': char_offset + entity_start,
                            'end_char': char_offset + entity_start + len(entity_text)
                        })
                        word_offset = entity_start + len(entity_text)

            char_offset += len(sent) + 1

        return extracted_entities

    def _extract_entities_llm(self, content: str, exp_doc: ExperimentDocument) -> List[Dict[str, Any]]:
        """Extract entities using LLM (LangExtract)"""
        try:
            from app.services.integrated_langextract import IntegratedLangExtractService

            langextract_service = IntegratedLangExtractService()

            if not langextract_service.service_ready:
                raise Exception(f"LangExtract service not ready: {langextract_service.initialization_error}")

            analysis_result = langextract_service.analyze_document_for_entities(
                text=content,
                document_metadata={
                    'document_id': exp_doc.document_id,
                    'experiment_id': exp_doc.experiment_id,
                    'title': exp_doc.document.title
                }
            )

            extracted_entities = []

            # Extract entities
            if 'entities' in analysis_result:
                for entity_data in analysis_result['entities']:
                    extracted_entities.append({
                        'entity': entity_data.get('text', ''),
                        'type': entity_data.get('type', 'ENTITY'),
                        'confidence': entity_data.get('confidence', 0.85),
                        'context': entity_data.get('context', ''),
                        'start_char': entity_data.get('start_pos', 0),
                        'end_char': entity_data.get('end_pos', 0)
                    })

            # Extract key concepts
            if 'key_concepts' in analysis_result:
                for concept in analysis_result['key_concepts']:
                    extracted_entities.append({
                        'entity': concept.get('term', ''),
                        'type': 'CONCEPT',
                        'confidence': concept.get('confidence', 0.80),
                        'context': concept.get('context', ''),
                        'start_char': concept.get('position', [0, 0])[0],
                        'end_char': concept.get('position', [0, 0])[1]
                    })

            return extracted_entities

        except Exception as e:
            logger.warning(f"LangExtract extraction failed, falling back to pattern-based: {e}")

            # Fallback to pattern-based extraction
            import re
            patterns = [
                r'\b[A-Z][a-z]+ [A-Z][a-z]+\b',  # Proper names
                r'\b[A-Z]{2,}\b',  # Acronyms
                r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Inc|Corp|LLC|Ltd|Company|University|Institute)\b',
                r'\b(?:Dr|Prof|Mr|Ms|Mrs)\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b',
            ]

            extracted_entities = []
            for pattern in patterns:
                matches = re.finditer(pattern, content)
                for match in matches:
                    entity_text = match.group().strip()
                    start_pos = match.start()
                    end_pos = match.end()
                    context_start = max(0, start_pos - 50)
                    context_end = min(len(content), end_pos + 50)
                    context = content[context_start:context_end].strip()

                    extracted_entities.append({
                        'entity': entity_text,
                        'type': 'ENTITY',
                        'confidence': 0.60,
                        'context': context,
                        'start_char': start_pos,
                        'end_char': end_pos
                    })

            return extracted_entities

    def _process_temporal(
        self,
        processing_op: ExperimentDocumentProcessing,
        index_entry: DocumentProcessingIndex,
        exp_doc: ExperimentDocument,
        processing_method: str
    ):
        """Process temporal extraction for a document"""
        from app.services.processing_tools import DocumentProcessor

        config = processing_op.get_configuration()
        processor = DocumentProcessor(
            user_id=config.get('created_by'),
            experiment_id=exp_doc.experiment_id
        )

        content = exp_doc.document.content
        if not content:
            processing_op.mark_completed({'temporal_expressions': 0})
            index_entry.status = 'completed'
            return

        # Run temporal extraction
        result = processor.extract_temporal(content)

        if result.status == 'success':
            # Create artifacts for each temporal expression
            for i, expr in enumerate(result.data):
                artifact = ProcessingArtifact(
                    processing_id=processing_op.id,
                    document_id=exp_doc.document_id,
                    artifact_type='temporal_marker',  # Must match extraction_tools.py ARTIFACT_TYPE_MAP
                    artifact_index=i
                )
                artifact.set_content({
                    'text': expr['text'],
                    'type': expr['type'],
                    'normalized': expr.get('normalized'),
                    'confidence': expr['confidence']
                })
                artifact.set_metadata({
                    'method': processing_method,
                    'start_char': expr['start'],
                    'end_char': expr['end']
                })
                db.session.add(artifact)

            processing_op.mark_completed({
                'temporal_method': processing_method,
                'expressions_found': result.metadata.get('total_expressions', 0),
                'expression_types': result.metadata.get('expression_types', {}),
                'service_used': result.metadata.get('method', 'spacy_ner_plus_regex')
            })
            index_entry.status = 'completed'
        else:
            raise RuntimeError(f"Temporal extraction failed: {result.metadata.get('error', 'Unknown error')}")

    def _process_definitions(
        self,
        processing_op: ExperimentDocumentProcessing,
        index_entry: DocumentProcessingIndex,
        exp_doc: ExperimentDocument,
        processing_method: str
    ):
        """Process definition extraction for a document"""
        from app.services.processing_tools import DocumentProcessor

        config = processing_op.get_configuration()
        processor = DocumentProcessor(
            user_id=config.get('created_by'),
            experiment_id=exp_doc.experiment_id
        )

        content = exp_doc.document.content
        if not content:
            processing_op.mark_completed({'definitions': 0})
            index_entry.status = 'completed'
            return

        # Run definition extraction
        result = processor.extract_definitions(content)

        if result.status == 'success':
            # Create artifacts for each definition
            for i, definition in enumerate(result.data):
                artifact = ProcessingArtifact(
                    processing_id=processing_op.id,
                    document_id=exp_doc.document_id,
                    artifact_type='term_definition',
                    artifact_index=i
                )
                artifact.set_content({
                    'term': definition['term'],
                    'definition': definition['definition'],
                    'pattern': definition['pattern'],
                    'confidence': definition['confidence'],
                    'sentence': definition.get('sentence', '')
                })
                artifact.set_metadata({
                    'method': processing_method,
                    'start_char': definition['start'],
                    'end_char': definition['end']
                })
                db.session.add(artifact)

            processing_op.mark_completed({
                'definitions_method': processing_method,
                'definitions_found': result.metadata.get('total_definitions', 0),
                'pattern_types': result.metadata.get('pattern_types', {}),
                'service_used': result.metadata.get('method', 'pattern_matching')
            })
            index_entry.status = 'completed'
        else:
            raise RuntimeError(f"Definition extraction failed: {result.metadata.get('error', 'Unknown error')}")

    def _process_enhanced(
        self,
        processing_op: ExperimentDocumentProcessing,
        index_entry: DocumentProcessingIndex,
        exp_doc: ExperimentDocument,
        processing_method: str
    ):
        """
        Process enhanced extraction (term extraction + OED enrichment)

        This is a placeholder implementation that will be expanded to include:
        - Term extraction from document
        - OED API integration for historical definitions
        - Period-aware analysis
        """
        content = exp_doc.document.content
        if not content:
            processing_op.mark_completed({'terms_extracted': 0})
            index_entry.status = 'completed'
            return

        try:
            # For now, create a simple stub that marks processing as completed
            # TODO: Implement actual term extraction and OED enrichment
            # This should call term_extraction_service and oed_period_service

            # Placeholder: Extract basic terms (simple implementation)
            import re
            words = re.findall(r'\b[A-Za-z]{4,}\b', content)
            unique_terms = list(set(words[:50]))  # Limit to 50 unique terms

            # Create artifacts for extracted terms
            for i, term in enumerate(unique_terms):
                artifact = ProcessingArtifact(
                    processing_id=processing_op.id,
                    document_id=exp_doc.document_id,
                    artifact_type='extracted_term',
                    artifact_index=i
                )
                artifact.set_content({
                    'term': term,
                    'oed_enriched': False,  # Not yet implemented
                    'note': 'Basic term extraction - OED enrichment pending implementation'
                })
                artifact.set_metadata({
                    'method': processing_method,
                    'extraction_type': 'basic'
                })
                db.session.add(artifact)

            processing_op.mark_completed({
                'enhanced_method': processing_method,
                'terms_extracted': len(unique_terms),
                'oed_enriched': 0,  # Not yet implemented
                'service_used': 'Basic regex term extraction (placeholder)',
                'note': 'Full implementation pending - includes OED integration'
            })
            index_entry.status = 'completed'

        except Exception as e:
            raise RuntimeError(f"Enhanced processing failed: {str(e)}")

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


# Singleton instance
_pipeline_service = None


def get_pipeline_service() -> PipelineService:
    """Get the singleton PipelineService instance"""
    global _pipeline_service
    if _pipeline_service is None:
        _pipeline_service = PipelineService()
    return _pipeline_service
