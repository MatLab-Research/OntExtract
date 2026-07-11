"""Document embedding generation route."""

from flask import current_app, jsonify, request
from flask_login import current_user

from app.services.base_service import NotFoundError, PermissionError, ValidationError
from app.services.document_embedding_workflow import DocumentEmbeddingWorkflow
from app.utils.auth_decorators import api_require_login_for_write

from . import processing_bp


@processing_bp.route('/document/<string:document_uuid>/embeddings', methods=['POST'])
@api_require_login_for_write
def generate_embeddings(document_uuid):
    """Generate embeddings for a new or experiment-owned document version."""
    workflow = DocumentEmbeddingWorkflow(workflow_logger=current_app.logger)
    try:
        document = workflow.get_document(document_uuid)
        result = workflow.generate(
            document,
            request.get_json(silent=True) or {},
            current_user,
        )
        return jsonify(result)
    except NotFoundError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 404
    except PermissionError:
        return jsonify({'success': False, 'error': 'Permission denied'}), 403
    except ValidationError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    except Exception as exc:
        current_app.logger.error(
            f'Embedding generation failed: {exc}',
            exc_info=True,
        )
        return jsonify({
            'success': False,
            'error': 'Embedding generation failed',
        }), 500
