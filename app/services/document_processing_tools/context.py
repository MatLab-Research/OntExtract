"""Shared execution context and provenance generation for processing tools."""

from datetime import datetime
from typing import Any, Dict, Optional
import uuid


class ProcessorContext:
    def __init__(self, user_id: Optional[int] = None, experiment_id: Optional[int] = None):
        """
        Initialize processor with optional context.

        Args:
            user_id: ID of user running the tool (for provenance)
            experiment_id: ID of experiment (for provenance)
        """
        self.user_id = user_id
        self.experiment_id = experiment_id

    def _generate_provenance(self, tool_name: str, input_data: Any = None) -> Dict[str, Any]:
        """
        Generate PROV-O provenance record for tool execution.

        Args:
            tool_name: Name of the tool
            input_data: Optional input data description

        Returns:
            PROV-O compatible provenance dictionary
        """
        execution_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()

        return {
            "activity_id": f"urn:ontextract:activity:{execution_id}",
            "tool": tool_name,
            "started_at": timestamp,
            "ended_at": timestamp,
            "agent": f"urn:ontextract:user:{self.user_id}" if self.user_id else "urn:ontextract:agent:system",
            "experiment": f"urn:ontextract:experiment:{self.experiment_id}" if self.experiment_id else None,
            "input_summary": str(input_data)[:200] if input_data else None
        }
