"""Upload routes grouped on a shared blueprint."""

from flask import Blueprint

upload_bp = Blueprint("upload", __name__, url_prefix="/upload")

from . import legacy  # noqa: E402,F401
from . import metadata  # noqa: E402,F401
from . import pages  # noqa: E402,F401
from . import persistence  # noqa: E402,F401
from . import references  # noqa: E402,F401
from . import streaming  # noqa: E402,F401
