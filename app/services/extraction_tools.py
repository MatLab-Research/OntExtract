"""
Tool registry for document processing orchestration.

Provides access to processing tools for experiment-level orchestration.
Connects orchestration layer to DocumentProcessor implementations.
"""

from typing import Dict, Any, Optional
from app.services.processing_tools import DocumentProcessor, ProcessingResult
from app.services.processing_registry_service import processing_registry_service
import logging

logger = logging.getLogger(__name__)


class ToolExecutor:
    """
    Tool executor that wraps DocumentProcessor methods.

    Provides async interface for orchestration while using synchronous
    DocumentProcessor implementations under the hood.
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

    async def execute(self, document_text: str, document_id: Optional[int] = None,
                      orchestration_run_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Execute the tool on document text.

        Automatically creates a ProcessingArtifactGroup record for successful operations
        to track what processing was done during orchestration.

        Args:
            document_text: Document content to process
            document_id: Optional document ID for creating ProcessingArtifactGroup
            orchestration_run_id: Optional orchestration run ID for provenance tracking
            **kwargs: Additional tool-specific parameters

        Returns:
            Processing results in standardized format
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
                "results": {}
            }

        # Execute the tool (synchronously)
        try:
            result: ProcessingResult = tool_method(document_text)

            # Create ProcessingArtifactGroup after successful execution
            if result.status == "success" and document_id is not None:
                try:
                    artifact_config = self._get_artifact_config(self.tool_name)

                    # Build metadata
                    metadata = {
                        'created_by': 'llm_orchestration',
                        'tool_name': self.tool_name,
                        'processing_params': kwargs
                    }

                    # Add orchestration run ID if provided
                    if orchestration_run_id:
                        metadata['orchestration_run_id'] = orchestration_run_id

                    # Merge with any metadata from the processing result
                    if result.metadata:
                        metadata.update(result.metadata)

                    # Create or get the artifact group
                    group = processing_registry_service.create_or_get_group(
                        document_id=document_id,
                        artifact_type=artifact_config['type'],
                        method_key=artifact_config['method_key'],
                        metadata=metadata,
                        include_in_composite=True
                    )

                    logger.info(
                        f"Created ProcessingArtifactGroup {group.id} for document {document_id}, "
                        f"tool {self.tool_name}, type {artifact_config['type']}, "
                        f"method {artifact_config['method_key']}"
                    )

                except Exception as group_error:
                    # Log error but don't fail the whole operation
                    logger.error(
                        f"Failed to create ProcessingArtifactGroup for document {document_id}, "
                        f"tool {self.tool_name}: {group_error}",
                        exc_info=True
                    )

            # Convert ProcessingResult to orchestration format
            return {
                "tool": self.tool_name,
                "status": result.status,
                "results": {
                    "data": result.data,
                    "metadata": result.metadata,
                    "provenance": result.provenance
                },
                "count": len(result.data) if isinstance(result.data, list) else 1,
                "success": result.status == "success"
            }

        except Exception as e:
            return {
                "tool": self.tool_name,
                "status": "error",
                "error": str(e),
                "results": {},
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
