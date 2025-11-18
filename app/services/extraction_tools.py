"""
Tool registry for document processing orchestration.

Provides access to processing tools for experiment-level orchestration.
Connects orchestration layer to DocumentProcessor implementations.
"""

from typing import Dict, Any, Optional
from app.services.processing_tools import DocumentProcessor, ProcessingResult


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

    async def execute(self, document_text: str, **kwargs) -> Dict[str, Any]:
        """
        Execute the tool on document text.

        Args:
            document_text: Document content to process
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
