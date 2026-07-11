"""Definition-result cleanup JSON adapter."""

from flask import current_app, jsonify
from flask_login import current_user

from app.services.base_service import NotFoundError, PermissionError, ServiceError
from app.services.definition_cleanup_service import DefinitionCleanupService
from app.utils.auth_decorators import api_require_login_for_write

from . import processing_bp


@processing_bp.route('/document/<string:document_uuid>/clear/definitions', methods=['DELETE'])
@api_require_login_for_write
def clear_definitions(document_uuid):
    try:
        return jsonify(DefinitionCleanupService.clear(
            document_uuid,
            current_user.id,
        ))
    except NotFoundError as exc:
        return jsonify({'error': str(exc)}), 404
    except PermissionError:
        return jsonify({'error': 'Permission denied'}), 403
    except ServiceError as exc:
        current_app.logger.error(
            'Definition cleanup failed: %s',
            exc,
            exc_info=True,
        )
        return jsonify({'error': 'Failed to clear definition results'}), 500
