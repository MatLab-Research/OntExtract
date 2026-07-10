"""PROV-O entity lineage pages."""

from flask import abort, render_template
from flask_login import current_user, login_required

from app.services.base_service import NotFoundError, PermissionError, ValidationError
from app.services.provenance_visualization_service import (
    ProvenanceVisualizationService,
)

from . import bp


@bp.route('/entity/<entity_id>/lineage')
@login_required
def entity_lineage(entity_id):
    """
    Display full lineage of an entity (derivation chain).
    """
    try:
        context = ProvenanceVisualizationService.lineage_context(
            entity_id,
            current_user.id,
        )
    except ValidationError:
        abort(400)
    except PermissionError:
        abort(403)
    except NotFoundError:
        abort(404)
    return render_template('provenance/lineage.html', **context)
