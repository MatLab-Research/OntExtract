"""Legacy standalone document embedding compatibility adapter."""

from flask import current_app, jsonify
from flask_login import current_user

from app.services.base_service import NotFoundError, PermissionError, ValidationError
from app.services.document_embedding_workflow import DocumentEmbeddingWorkflow
from app.utils.auth_decorators import write_login_required

from . import text_input_bp


@text_input_bp.route('/documents/<int:document_id>/apply_embeddings', methods=['POST'])
@write_login_required
def apply_embeddings(document_id):
    workflow = DocumentEmbeddingWorkflow(workflow_logger=current_app.logger)
    try:
        document = workflow.get_document(document_id)
        result = workflow.generate(document, {'method': 'local'}, current_user)
        return jsonify({
            'success': True,
            'message': 'Embeddings applied successfully',
            'embedding_info': result['embedding_info'],
        })
    except NotFoundError as exc:
        return jsonify({'error': str(exc)}), 404
    except PermissionError:
        return jsonify({'error': 'Permission denied'}), 403
    except ValidationError as exc:
        return jsonify({'error': str(exc)}), 400
    except Exception as exc:
        current_app.logger.error(
            'Legacy embedding generation failed: %s',
            exc,
            exc_info=True,
        )
        return jsonify({'error': 'Failed to generate embeddings'}), 500
