"""Individual document deletion routes."""

from flask import current_app, flash, jsonify, redirect, request, url_for
from flask_login import current_user

from app.models.document import Document
from app.services.document_deletion_service import DocumentDeletionService
from app.utils.auth_decorators import write_login_required

from ... import text_input_bp


def _permission_denied(document):
    if request.is_json:
        return jsonify({'error': 'Permission denied'}), 403
    flash('You do not have permission to delete this document', 'error')
    return redirect(
        url_for('text_input.document_detail', document_uuid=document.uuid)
    )


def _delete_response(document):
    try:
        DocumentDeletionService.delete_document(document, current_app.logger)
        if request.is_json:
            return jsonify({
                'success': True,
                'message': 'Document deleted successfully'
            })
        flash('Document deleted successfully', 'success')
        return redirect(url_for('text_input.document_list'))
    except Exception as exc:
        current_app.logger.error(
            f"Error deleting document {document.id}: {exc}"
        )
        if request.is_json:
            return jsonify({
                'error': 'An error occurred while deleting the document'
            }), 500
        flash('An error occurred while deleting the document', 'error')
        return redirect(
            url_for('text_input.document_detail', document_uuid=document.uuid)
        )


@text_input_bp.route('/document/<int:document_id>/delete', methods=['POST'])
@write_login_required
def delete_document(document_id):
    """Delete a document by database ID."""
    document = Document.query.filter_by(id=document_id).first_or_404()
    if not current_user.can_delete_resource(document):
        return _permission_denied(document)
    return _delete_response(document)


@text_input_bp.route('/document/<uuid:document_uuid>/delete', methods=['POST'])
@write_login_required
def delete_document_by_uuid(document_uuid):
    """Delete an unreferenced document by UUID."""
    document = Document.query.filter_by(uuid=document_uuid).first_or_404()
    if not current_user.can_delete_resource(document):
        return _permission_denied(document)

    experiments = DocumentDeletionService.get_referencing_experiments(document.id)
    if experiments:
        experiment_list = [
            {'id': experiment.id, 'name': experiment.name}
            for experiment in experiments
        ]
        if request.is_json:
            return jsonify({
                'error': 'Cannot delete document: still referenced in experiments',
                'experiments': experiment_list
            }), 409

        names = ', '.join(
            f'"{experiment.name}"' for experiment in experiments[:3]
        )
        if len(experiments) > 3:
            names += f' and {len(experiments) - 3} more'
        flash(
            'Cannot delete this document because it is part of '
            f'{len(experiments)} experiment(s): {names}. Please remove the '
            'document from experiments first, or delete the experiment(s).',
            'error',
        )
        return redirect(
            url_for('text_input.document_detail', document_uuid=document_uuid)
        )

    return _delete_response(document)
