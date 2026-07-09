"""Administrative routes grouped on a shared blueprint."""

from flask import Blueprint

admin_bp = Blueprint("admin", __name__)

from . import dashboard  # noqa: E402,F401
from . import data  # noqa: E402,F401
from . import errors  # noqa: E402,F401
from . import health  # noqa: E402,F401
from . import tasks  # noqa: E402,F401
from . import users  # noqa: E402,F401
