"""Read models for pipeline overview and per-document processing pages."""

import logging
from typing import Any, Dict

from app.models import Document, Experiment, ExperimentDocument, ExperimentOrchestrationRun
from app.models.experiment_processing import ExperimentDocumentProcessing, DocumentProcessingIndex
from app.services.base_service import NotFoundError, ServiceError, ValidationError

from .constants import LLM_TOOL_TO_OPERATION_MAP

logger = logging.getLogger(__name__)


class PipelineOverviewMixin:
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

                # Check if a cleaned version exists in the document family
                # This checks for version_type='cleaned' in the family, not just ProcessingJob
                root_doc = doc.get_root_document()
                has_cleanup = Document.query.filter_by(
                    source_document_id=root_doc.id,
                    version_type='cleaned'
                ).first() is not None

                # Also check for cleanup processing record
                if not has_cleanup:
                    cleanup_record = ExperimentDocumentProcessing.query.filter_by(
                        experiment_document_id=exp_doc.id,
                        processing_type='cleanup',
                        status='completed'
                    ).first()
                    has_cleanup = cleanup_record is not None

                # Add LLM cleanup to operations if a cleaned version exists
                # (but only if cleanup isn't already in operations_list)
                cleanup_already_added = any(op['type'] == 'cleanup' for op in operations_list)
                if has_cleanup and not cleanup_already_added:
                    operations_list.append({
                        'type': 'cleanup',
                        'method': 'llm',
                        'source': 'llm'
                    })

                # Calculate total operations from both systems
                total_ops = len(manual_ops) + len(index_entries)
                completed_ops = sum(1 for op in manual_ops if op.status == 'completed') + \
                                sum(1 for entry in index_entries if entry.status == 'completed')

                # Extract content source info from processing_metadata (for experimental versions)
                derived_from = None
                if doc.processing_metadata and isinstance(doc.processing_metadata, dict):
                    derived_from = doc.processing_metadata.get('derived_from')

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
                    'version_type': doc.version_type,  # Track version type (processed, experimental, etc.)
                    'derived_from': derived_from  # Source version info (cleaned v2, original v1, etc.)
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

            # Check if a cleaned version exists in the document family
            # This checks for version_type='cleaned' in the family
            root_doc = document.get_root_document()
            has_cleanup = Document.query.filter_by(
                source_document_id=root_doc.id,
                version_type='cleaned'
            ).first() is not None

            # Also check for cleanup processing record
            if not has_cleanup:
                cleanup_record = ExperimentDocumentProcessing.query.filter_by(
                    experiment_document_id=exp_doc.id,
                    processing_type='cleanup',
                    status='completed'
                ).first()
                has_cleanup = cleanup_record is not None

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
