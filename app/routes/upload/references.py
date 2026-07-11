"""Quick dictionary-reference creation JSON adapter."""

from flask import current_app, jsonify, request
from flask_login import current_user, login_required

from app.services.base_service import (
    NotFoundError,
    PermissionError,
    ServiceError,
    ValidationError,
)
from app.services.dictionary_reference_creation_service import (
    DictionaryReferenceCreationService,
)
from app.services.provenance_service import provenance_service

from . import upload_bp


def _service():
    return DictionaryReferenceCreationService(
        provenance_service=provenance_service,
        workflow_logger=current_app.logger,
    )


@upload_bp.route('/create_reference', methods=['POST'])
@login_required
def create_reference():
    try:
        result = _service().create_quick(
            request.get_json(silent=True),
            current_user.id,
        )
    except ValidationError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    except PermissionError:
        return jsonify({'success': False, 'error': 'Permission denied'}), 403
    except NotFoundError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 404
    except ServiceError as exc:
        current_app.logger.error(
            'Quick reference creation failed: %s',
            exc,
            exc_info=True,
        )
        return jsonify({
            'success': False,
            'error': 'Failed to create reference',
        }), 500

    document = result.document
    return jsonify({
        'success': True,
        'document_id': document.id,
        'document_uuid': str(document.uuid),
        'metadata_filled': bool(document.publisher),
    })
