"""Dictionary and pasted-reference creation adapter."""

from flask import current_app, flash, redirect, request, url_for
from flask_login import current_user

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
from app.utils.auth_decorators import api_require_login_for_write

from .. import references_bp


def _service():
    return DictionaryReferenceCreationService(
        provenance_service=provenance_service,
        workflow_logger=current_app.logger,
    )


@references_bp.route('/upload_dictionary', methods=['POST'])
@api_require_login_for_write
def upload_dictionary():
    try:
        outcome = _service().create(request.form, current_user.id)
    except (ValidationError, NotFoundError, PermissionError) as exc:
        flash(
            'Permission denied' if isinstance(exc, PermissionError) else str(exc),
            'error',
        )
        return redirect(url_for('references.upload'))
    except ServiceError as exc:
        current_app.logger.error(
            'Dictionary reference creation failed: %s',
            exc,
            exc_info=True,
        )
        flash('Failed to save dictionary reference', 'error')
        return redirect(url_for('references.upload'))

    document = outcome.document
    flash(f'Dictionary entry "{document.title}" saved successfully', 'success')
    if outcome.experiment:
        flash(
            f'Dictionary entry linked to experiment '
            f'"{outcome.experiment.name}"',
            'success',
        )
        return redirect(url_for(
            'experiments.view',
            experiment_id=outcome.experiment.id,
        ))
    return redirect(url_for('references.view', id=document.id))
