"""PROV-O visualization, timeline, API, and administration routes."""

from flask import Blueprint

bp = Blueprint("provenance", __name__, url_prefix="/provenance")

from . import graphs  # noqa: E402,F401
from . import timeline  # noqa: E402,F401
from . import api  # noqa: E402,F401
from . import lineage  # noqa: E402,F401
from . import admin  # noqa: E402,F401
