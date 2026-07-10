"""PROV-O entity lineage pages."""

from flask import render_template
from flask_login import login_required

from app.services.provenance_service import provenance_service

from . import bp


@bp.route('/entity/<entity_id>/lineage')
@login_required
def entity_lineage(entity_id):
    """
    Display full lineage of an entity (derivation chain).
    """
    from app.models.prov_o_models import ProvEntity
    import uuid

    try:
        entity_uuid = uuid.UUID(entity_id)
    except ValueError:
        return "Invalid entity ID", 400

    entity = ProvEntity.query.get_or_404(entity_uuid)
    lineage = provenance_service.get_entity_lineage(entity_uuid)

    return render_template(
        'provenance/lineage.html',
        entity=entity,
        lineage=lineage
    )
