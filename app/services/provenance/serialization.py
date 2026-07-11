"""JSON-safe provenance value serialization."""

import uuid
from datetime import datetime
from typing import Any


def _serialize_value(value: Any) -> Any:
    """
    Convert values to JSON-serializable format.
    Handles UUIDs, datetime objects, and nested structures.
    """
    if isinstance(value, uuid.UUID):
        return str(value)
    elif isinstance(value, datetime):
        return value.isoformat()
    elif isinstance(value, dict):
        return {k: _serialize_value(v) for k, v in value.items()}
    elif isinstance(value, (list, tuple)):
        return [_serialize_value(v) for v in value]
    else:
        return value
