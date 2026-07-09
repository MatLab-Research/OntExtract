"""Standard result type returned by document processing tools."""

from dataclasses import asdict, dataclass
from typing import Any, Dict


@dataclass
class ProcessingResult:
    """Standardized tool output with PROV-O provenance metadata."""

    tool_name: str
    status: str
    data: Any
    metadata: Dict[str, Any]
    provenance: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a JSON-serializable dictionary."""
        return asdict(self)
