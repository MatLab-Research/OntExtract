"""API endpoints for listing processing methods (artifact groups) per document."""

from flask import Blueprint, jsonify
from flask_login import login_required
from app import db
from app.models.document import Document
from app.models.text_segment import TextSegment
from app.services.processing_registry_service import processing_registry_service

document_methods_bp = Blueprint(
    "document_methods_api", __name__, url_prefix="/api/documents"
)


@document_methods_bp.route("/<int:document_id>/methods", methods=["GET"])
@login_required
def list_document_methods(document_id: int):
    """Return list of processing artifact groups (methods) for a document.

    Response shape:
    {
      "success": true,
      "document_id": 123,
      "groups": [
         { id, artifact_type, method_key, segment_count, status, ... },
         ...
      ],
      "legacy_backfilled": N  # number of legacy segments linked during request
    }
    """
    doc = db.session.get(Document, document_id)
    if not doc:
        return jsonify({"success": False, "error": "Document not found"}), 404

    groups = processing_registry_service.list_groups_for_document(document_id)

    # Opportunistically backfill legacy segments without group linkage
    legacy_segments = (
        TextSegment.query.filter_by(document_id=document_id, group_id=None)
        .limit(2000)  # safety cap
        .all()
    )
    legacy_backfilled = 0
    for seg in legacy_segments:
        group = processing_registry_service.ensure_legacy_group_for_segment(seg)
        if group:
            legacy_backfilled += 1
            if group not in groups:
                groups.append(group)

    # Summarize for output
    payload = processing_registry_service.summarize_groups(groups)

    return jsonify(
        {
            "success": True,
            "document_id": document_id,
            "groups": payload,
            "legacy_backfilled": legacy_backfilled,
        }
    )
