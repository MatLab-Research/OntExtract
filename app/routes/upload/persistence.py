"""Reviewed upload persistence route."""

import re

from flask import current_app, jsonify, request
from flask_login import current_user

from app import db
from app.services.base_service import ValidationError
from app.services.provenance_service import provenance_service
from app.services.upload_persistence_service import UploadPersistenceService
from app.services.upload_service import upload_service
from app.utils.auth_decorators import api_require_login_for_write

from . import upload_bp


@upload_bp.route('/save_document', methods=['POST'])
@api_require_login_for_write
def save_document():
    """Persist an uploaded document after metadata review."""
    service = UploadPersistenceService(
        upload_service,
        provenance_service,
        current_app.logger,
    )
    try:
        result = service.persist_reviewed_upload(
            request.get_json(silent=True),
            current_user,
            current_app.config.get('UPLOAD_FOLDER', 'uploads'),
        )
        return jsonify(result)
    except ValidationError as exc:
        return jsonify({'error': str(exc)}), 400
    except Exception as exc:
        db.session.rollback()
        current_app.logger.error(f'Error saving document: {exc}', exc_info=True)
        error_text = str(exc)
        if 'ix_documents_doi' in error_text or 'duplicate key' in error_text.lower():
            match = re.search(r'\(doi\)=\(([^)]+)\)', error_text)
            doi_value = match.group(1) if match else 'this DOI'
            return jsonify({
                'error': (
                    f'A document with DOI {doi_value} already exists in the '
                    'database. Please check the Documents page for the existing '
                    'document.'
                ),
            }), 409
        return jsonify({'error': error_text}), 500
