"""
Tool registry for document processing orchestration.

Provides access to processing tools for experiment-level orchestration.
Connects orchestration layer to DocumentProcessor implementations.

All processing results are stored in the ProcessingArtifact table for unified
storage regardless of whether processing was triggered manually or via LLM orchestration.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from app.services.processing_tools import DocumentProcessor, ProcessingResult
from app.services.processing_registry_service import processing_registry_service
from app import db
import logging

logger = logging.getLogger(__name__)


# Artifact type mapping for each tool
# These must match the artifact_type values used in manual processing routes
ARTIFACT_TYPE_MAP = {
    "segment_paragraph": "text_segment",
    "segment_sentence": "text_segment",
    "extract_entities_spacy": "extracted_entity",
    "extract_temporal": "temporal_marker",
    "extract_causal": "causal_relation",
    "extract_definitions": "term_definition",  # Must match pipeline.py/pipeline_service.py
    "period_aware_embedding": "embedding_vector"
}


class ToolExecutor:
    """
    Tool executor that wraps DocumentProcessor methods.

    Provides async interface for orchestration while using synchronous
    DocumentProcessor implementations under the hood.

    All results are stored in ProcessingArtifact table for unified storage.
    """

    def __init__(self, tool_name: str, user_id: Optional[int] = None, experiment_id: Optional[int] = None):
        self.tool_name = tool_name
        self.user_id = user_id
        self.experiment_id = experiment_id
        self._processor = None

    def _get_processor(self) -> DocumentProcessor:
        """Lazy-load the DocumentProcessor"""
        if self._processor is None:
            self._processor = DocumentProcessor(
                user_id=self.user_id,
                experiment_id=self.experiment_id
            )
        return self._processor

    def _get_artifact_config(self, tool_name: str) -> Dict[str, str]:
        """
        Map tool names to ProcessingArtifactGroup configuration.

        Returns:
            Dictionary with 'type' and 'method_key' for the tool
        """
        artifact_configs = {
            "segment_paragraph": {
                "type": "segmentation",
                "method_key": "paragraph"
            },
            "segment_sentence": {
                "type": "segmentation",
                "method_key": "sentence"
            },
            "extract_entities_spacy": {
                "type": "entities",
                "method_key": "spacy_ner"
            },
            "extract_temporal": {
                "type": "temporal",
                "method_key": "temporal_extraction"
            },
            "extract_causal": {
                "type": "causal",
                "method_key": "causal_extraction"
            },
            "extract_definitions": {
                "type": "definitions",
                "method_key": "definition_extraction"
            },
            "period_aware_embedding": {
                "type": "embeddings",
                "method_key": "period_aware"
            }
        }
        return artifact_configs.get(tool_name, {"type": "unknown", "method_key": tool_name})

    def _store_artifacts(self, document_id: int, processing_id, result_data: List[Dict],
                        artifact_type: str, metadata: Dict) -> int:
        """
        Store processing results as ProcessingArtifact records.

        Args:
            document_id: The document ID
            processing_id: The ExperimentDocumentProcessing ID
            result_data: List of result items from the processing tool
            artifact_type: The type of artifact (text_segment, extracted_entity, etc.)
            metadata: Base metadata to include with each artifact

        Returns:
            Number of artifacts created
        """
        from app.models.experiment_processing import ProcessingArtifact

        count = 0
        for idx, item in enumerate(result_data):
            artifact = ProcessingArtifact(
                processing_id=processing_id,
                document_id=document_id,
                artifact_type=artifact_type,
                artifact_index=idx
            )

            # Set content based on artifact type
            artifact.set_content(item)

            # Set metadata (include base metadata plus any item-specific metadata)
            item_metadata = metadata.copy()
            if isinstance(item, dict):
                # Extract specific metadata fields from the item
                for key in ['confidence', 'method', 'model', 'dimensions', 'start', 'end']:
                    if key in item:
                        item_metadata[key] = item[key]
            artifact.set_metadata(item_metadata)

            db.session.add(artifact)
            count += 1

        return count

    async def execute(self, document_text: str, document_id: Optional[int] = None,
                      orchestration_run_id: Optional[str] = None,
                      experiment_document_id: Optional[int] = None,
                      **kwargs) -> Dict[str, Any]:
        """
        Execute the tool on document text and store results in database.

        Results are stored in ProcessingArtifact table for unified storage,
        whether called from LLM orchestration or manual processing.

        Args:
            document_text: Document content to process
            document_id: Document ID for storing artifacts
            orchestration_run_id: Optional orchestration run ID for provenance tracking
            experiment_document_id: Optional ExperimentDocument ID for linking processing
            **kwargs: Additional tool-specific parameters

        Returns:
            Processing results summary (data is stored in DB, not returned in full)
        """
        processor = self._get_processor()

        # Map tool name to processor method
        tool_method_map = {
            "segment_paragraph": processor.segment_paragraph,
            "segment_sentence": processor.segment_sentence,
            "extract_entities_spacy": processor.extract_entities_spacy,
            "extract_temporal": processor.extract_temporal,
            "extract_causal": processor.extract_causal,
            "extract_definitions": processor.extract_definitions,
            "period_aware_embedding": lambda text: processor.period_aware_embedding(
                text, period=kwargs.get('period')
            )
        }

        # Get the appropriate method
        tool_method = tool_method_map.get(self.tool_name)

        if tool_method is None:
            return {
                "tool": self.tool_name,
                "status": "error",
                "error": f"Unknown tool: {self.tool_name}",
                "count": 0
            }

        # Execute the tool (synchronously)
        try:
            result: ProcessingResult = tool_method(document_text)
            artifact_config = self._get_artifact_config(self.tool_name)
            artifact_type = ARTIFACT_TYPE_MAP.get(self.tool_name, "unknown")
            artifacts_created = 0
            processing_id = None

            # Store results in database if we have a document_id
            if result.status == "success" and document_id is not None:
                try:
                    from app.models.experiment_processing import ExperimentDocumentProcessing

                    # Build metadata for the processing operation
                    operation_metadata = {
                        'tool_name': self.tool_name,
                        'processing_params': kwargs
                    }
                    if orchestration_run_id:
                        operation_metadata['orchestration_run_id'] = orchestration_run_id
                    if result.metadata:
                        operation_metadata.update(result.metadata)

                    # Create ExperimentDocumentProcessing record if we have experiment_document_id
                    if experiment_document_id:
                        processing_record = ExperimentDocumentProcessing(
                            experiment_document_id=experiment_document_id,
                            processing_type=artifact_config['type'],
                            processing_method=artifact_config['method_key'],
                            status='completed',
                            started_at=datetime.utcnow(),
                            completed_at=datetime.utcnow()
                        )
                        processing_record.set_configuration(operation_metadata)

                        # Set results summary
                        result_count = len(result.data) if isinstance(result.data, list) else 1
                        processing_record.set_results_summary({
                            'count': result_count,
                            'artifact_type': artifact_type,
                            'method': artifact_config['method_key']
                        })

                        db.session.add(processing_record)
                        db.session.flush()  # Get the ID
                        processing_id = processing_record.id

                        # Store individual artifacts
                        if isinstance(result.data, list) and result.data:
                            artifacts_created = self._store_artifacts(
                                document_id=document_id,
                                processing_id=processing_id,
                                result_data=result.data,
                                artifact_type=artifact_type,
                                metadata=operation_metadata
                            )

                        db.session.commit()
                        logger.info(
                            f"Stored {artifacts_created} {artifact_type} artifacts for document {document_id}, "
                            f"tool {self.tool_name}"
                        )

                    # Also create ProcessingArtifactGroup for backward compatibility
                    try:
                        group = processing_registry_service.create_or_get_group(
                            document_id=document_id,
                            artifact_type=artifact_config['type'],
                            method_key=artifact_config['method_key'],
                            metadata=operation_metadata,
                            include_in_composite=True
                        )
                        logger.debug(f"Created ProcessingArtifactGroup {group.id}")
                    except Exception as group_error:
                        logger.warning(f"Failed to create ProcessingArtifactGroup: {group_error}")

                except Exception as store_error:
                    logger.error(
                        f"Failed to store artifacts for document {document_id}, "
                        f"tool {self.tool_name}: {store_error}",
                        exc_info=True
                    )
                    db.session.rollback()

            # Return summary (data is in DB, not returned in full to avoid JSON blob storage)
            result_count = len(result.data) if isinstance(result.data, list) else 1
            return {
                "tool": self.tool_name,
                "status": result.status,
                "count": result_count,
                "artifacts_stored": artifacts_created,
                "processing_id": str(processing_id) if processing_id else None,
                "metadata": result.metadata,
                "success": result.status == "success"
            }

        except Exception as e:
            logger.error(f"Error executing tool {self.tool_name}: {e}", exc_info=True)
            return {
                "tool": self.tool_name,
                "status": "error",
                "error": str(e),
                "count": 0,
                "success": False
            }


def get_tool_registry(user_id: Optional[int] = None, experiment_id: Optional[int] = None) -> Dict[str, ToolExecutor]:
    """
    Get registry of available processing tools.

    Args:
        user_id: Optional user ID for provenance tracking
        experiment_id: Optional experiment ID for provenance tracking

    Returns:
        Dictionary mapping tool names to ToolExecutor instances
    """

    tools = {
        "segment_paragraph": ToolExecutor("segment_paragraph", user_id, experiment_id),
        "segment_sentence": ToolExecutor("segment_sentence", user_id, experiment_id),
        "extract_entities_spacy": ToolExecutor("extract_entities_spacy", user_id, experiment_id),
        "extract_temporal": ToolExecutor("extract_temporal", user_id, experiment_id),
        "extract_causal": ToolExecutor("extract_causal", user_id, experiment_id),
        "extract_definitions": ToolExecutor("extract_definitions", user_id, experiment_id),
        "period_aware_embedding": ToolExecutor("period_aware_embedding", user_id, experiment_id)
    }

    return tools
