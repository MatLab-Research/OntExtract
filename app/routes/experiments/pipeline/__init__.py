"""Experiment pipeline routes grouped by HTTP responsibility."""

from app.services.pipeline_service import get_pipeline_service


pipeline_service = get_pipeline_service()

from . import execution  # noqa: E402,F401
from . import pages  # noqa: E402,F401
from . import queries  # noqa: E402,F401
