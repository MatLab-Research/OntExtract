"""
Tool registry for document processing orchestration.

Provides access to processing tools for experiment-level orchestration.
"""

from typing import Dict, Any


class ToolExecutor:
    """Base class for tool executors."""

    def __init__(self, tool_name: str):
        self.tool_name = tool_name

    async def execute(self, document_text: str) -> Dict[str, Any]:
        """
        Execute the tool on document text.

        Args:
            document_text: Document content to process

        Returns:
            Processing results
        """
        # Stub implementation - actual tools would be implemented here
        return {
            "tool": self.tool_name,
            "status": "executed",
            "results": {}
        }


def get_tool_registry() -> Dict[str, ToolExecutor]:
    """
    Get registry of available processing tools.

    Returns:
        Dictionary mapping tool names to ToolExecutor instances
    """

    tools = {
        "segment_paragraph": ToolExecutor("segment_paragraph"),
        "segment_sentence": ToolExecutor("segment_sentence"),
        "extract_entities_spacy": ToolExecutor("extract_entities_spacy"),
        "extract_temporal": ToolExecutor("extract_temporal"),
        "extract_causal": ToolExecutor("extract_causal"),
        "extract_definitions": ToolExecutor("extract_definitions"),
        "period_aware_embedding": ToolExecutor("period_aware_embedding")
    }

    return tools
