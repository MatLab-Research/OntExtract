"""Synchronous document metadata extraction route."""

from flask import current_app, jsonify, request

from app.services.upload_metadata_workflow import UploadMetadataWorkflow
from app.services.upload_service import upload_service
from app.utils.auth_decorators import api_require_login_for_write

from . import upload_bp


@upload_bp.route('/extract_metadata', methods=['POST'])
@api_require_login_for_write
def extract_metadata():
    """Extract reviewable metadata from a DOI or uploaded document."""
    try:
        workflow = UploadMetadataWorkflow(upload_service, current_app.logger)
        payload, status = workflow.run(
            request.form.get('source_type'),
            request.form,
            request.files,
        )
        return jsonify(payload), status
    except Exception as exc:
        current_app.logger.error(f"Error extracting metadata: {exc}")
        return jsonify({'error': str(exc)}), 500
