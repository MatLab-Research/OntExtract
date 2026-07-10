"""Document metadata viewing and editing APIs."""

from flask import current_app, jsonify, request
from flask_login import current_user

from app import db
from app.models.document import Document
from app.services.document_metadata_service import DocumentMetadataService
from app.services.provenance_service import provenance_service
from app.utils.auth_decorators import write_login_required

from .. import text_input_bp


@text_input_bp.route('/document/<uuid:document_uuid>/metadata', methods=['GET'])
def get_document_metadata(document_uuid):
    """Return normalized and custom metadata, inherited from the root document."""
    try:
        document = Document.query.filter_by(uuid=document_uuid).first_or_404()
        return jsonify({
            'success': True,
            **DocumentMetadataService.serialize_for_view(document)
        })
    except Exception as exc:
        return jsonify({'success': False, 'error': str(exc)}), 500


@text_input_bp.route('/document/<uuid:document_uuid>/metadata', methods=['PUT'])
@write_login_required
def update_document_metadata(document_uuid):
    """Update normalized bibliographic and custom document metadata."""
    try:
        document = Document.query.filter_by(uuid=document_uuid).first_or_404()
        if not current_user.can_edit_resource(document):
            return jsonify({'success': False, 'error': 'Permission denied'}), 403

        metadata = request.get_json()
        if not metadata:
            return jsonify({'success': False, 'error': 'No metadata provided'}), 400

        changes = DocumentMetadataService.apply_updates(document, metadata)
        db.session.commit()

        if changes:
            try:
                provenance_service.track_metadata_update(
                    document,
                    current_user,
                    changes,
                )
            except Exception as exc:
                current_app.logger.warning(
                    f"Failed to track metadata update provenance: {exc}"
                )

        return jsonify({
            'success': True,
            'message': 'Metadata updated successfully',
            'metadata': DocumentMetadataService.serialize_after_update(document)
        })
    except Exception as exc:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(exc)}), 500
