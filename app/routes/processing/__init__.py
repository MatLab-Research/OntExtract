"""Processing routes grouped by responsibility on a shared blueprint."""

from flask import Blueprint

processing_bp = Blueprint("processing", __name__)

# Import route modules after creating the shared blueprint.
from . import batch  # noqa: E402,F401
from . import cleanup  # noqa: E402,F401
from . import embeddings  # noqa: E402,F401
from . import enhanced  # noqa: E402,F401
from . import entities  # noqa: E402,F401
from . import metadata  # noqa: E402,F401
from . import pipeline  # noqa: E402,F401
from . import results  # noqa: E402,F401
from . import segmentation  # noqa: E402,F401
from . import status  # noqa: E402,F401
from . import text_cleanup  # noqa: E402,F401
from . import validation  # noqa: E402,F401
