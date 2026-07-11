"""Processing status routes grouped into pages and APIs."""

from app.services.processing_status_service import ProcessingStatusService


processing_status_service = ProcessingStatusService()

from . import api  # noqa: E402,F401
from . import pages  # noqa: E402,F401
