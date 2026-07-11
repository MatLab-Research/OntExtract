"""General reference file upload route."""

from flask import current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user

from app import db
from app.models.experiment import Experiment
from app.services.base_service import NotFoundError, PermissionError, ValidationError
from app.services.legacy_upload_workflow import LegacyUploadWorkflow
from app.services.text_processing import TextProcessingService
from app.utils.auth_decorators import api_require_login_for_write

from .. import references_bp


def _experiment_context(experiment_id):
    if not experiment_id:
        return None
    try:
        experiment = db.session.get(Experiment, int(experiment_id))
    except (TypeError, ValueError):
        return None
    if not experiment or not current_user.is_authenticated:
        return None
    return experiment if current_user.can_edit_resource(experiment) else None


@references_bp.route('/upload', methods=['GET', 'POST'])
@api_require_login_for_write
def upload():
    if request.method == 'GET':
        experiment = _experiment_context(request.args.get('experiment_id'))
        template = (
            'references/upload_tabbed.html'
            if request.args.get('tabbed', 'true').lower() == 'true'
            else 'references/upload.html'
        )
        return render_template(template, experiment=experiment)

    file = request.files.get('file')
    if not file:
        flash('No file provided', 'error')
        return redirect(request.url)
    if not file.filename:
        flash('No file selected', 'error')
        return redirect(request.url)

    workflow = LegacyUploadWorkflow(
        processing_service=TextProcessingService(),
        workflow_logger=current_app.logger,
    )
    try:
        outcome = workflow.upload(
            file,
            request.form,
            current_user,
            current_app.config.get('UPLOAD_FOLDER'),
            force_document_type='reference',
            prefill_metadata=current_app.config.get('PREFILL_METADATA', True),
            use_zotero=current_app.config.get('PREFILL_USE_ZOTERO', False),
            validate_file_type=True,
        )
    except (ValidationError, NotFoundError, PermissionError) as exc:
        flash(str(exc), 'error')
        return redirect(request.url)
    except Exception as exc:
        current_app.logger.error(
            f'Error uploading reference: {exc}',
            exc_info=True,
        )
        flash('An error occurred while uploading the reference', 'error')
        return redirect(request.url)

    document = outcome['document']
    if outcome['processing_warning']:
        flash(
            f'Reference uploaded but processing failed: '
            f"{outcome['processing_warning']}",
            'warning',
        )
    else:
        flash(
            f'Reference "{document.title}" uploaded and processed successfully',
            'success',
        )
    experiment = outcome['linked_experiment']
    if experiment:
        flash(f'Reference linked to experiment "{experiment.name}"', 'success')
        return redirect(url_for('experiments.view', experiment_id=experiment.id))
    return redirect(url_for('references.view', id=document.id))
