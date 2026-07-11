"""Compatibility shim for constructing unsaved OED reference documents."""

from app.services.oed_reference_creation_service import (
    OEDLookupError,
    OEDReferenceCreationService,
)
from app.services.oed_service import OEDService


def _build_oed_reference(
    entry_id,
    user_id,
    selected_sense_ids=None,
    title_override=None,
):
    try:
        document = OEDReferenceCreationService(OEDService()).build_unsaved(
            entry_id,
            user_id,
            selected_sense_ids,
            title_override,
        )
        return document, None
    except OEDLookupError as exc:
        return None, str(exc)
