"""Legacy direct document upload compatibility route."""

from flask import current_app, flash, redirect, request, url_for
from flask_login import current_user

from app.services.base_service import ValidationError
from app.services.legacy_upload_workflow import LegacyUploadWorkflow
from app.utils.auth_decorators import api_require_login_for_write

from . import upload_bp


@upload_bp.route('/document', methods=['POST'])
@api_require_login_for_write
def upload_document():
    """Handle the legacy multipart upload form."""
    file = request.files.get('file')
    if not file:
        flash('No file provided', 'error')
        return redirect(url_for('upload.unified'))
    if not file.filename:
        flash('No file selected', 'error')
        return redirect(url_for('upload.unified'))

    workflow = LegacyUploadWorkflow(workflow_logger=current_app.logger)
    try:
        outcome = workflow.upload(
            file,
            request.form,
            current_user,
            current_app.config.get('UPLOAD_FOLDER'),
        )
    except ValidationError as exc:
        flash(str(exc), 'error')
        return redirect(url_for('upload.unified'))
    except Exception as exc:
        current_app.logger.error(
            f'Error uploading document: {exc}',
            exc_info=True,
        )
        flash(f'An error occurred while uploading: {exc}', 'error')
        return redirect(url_for('upload.unified'))

    document = outcome['document']
    if outcome['processing_warning']:
        flash(
            f'Document uploaded but processing failed: '
            f"{outcome['processing_warning']}",
            'warning',
        )
    else:
        flash(
            f'Document "{document.title}" uploaded and processed successfully',
            'success',
        )

    experiment = outcome['linked_experiment']
    if experiment:
        flash(f'Document linked to experiment "{experiment.name}"', 'success')
        return redirect(url_for('experiments.view', experiment_id=experiment.id))
    return redirect(url_for(
        'text_input.document_detail',
        document_uuid=document.uuid,
    ))
