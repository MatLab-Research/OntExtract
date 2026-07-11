"""Single and batch OED reference creation routes."""

from flask import current_app, flash, redirect, request, url_for
from flask_login import current_user

from app.services.base_service import NotFoundError, PermissionError, ValidationError
from app.services.oed_reference_creation_service import (
    OEDLookupError,
    OEDReferenceCreationService,
)
from app.services.oed_service import OEDService
from app.services.provenance_service import ProvenanceService
from app.utils.auth_decorators import api_require_login_for_write

from .. import references_bp


def _service():
    return OEDReferenceCreationService(
        OEDService(),
        ProvenanceService,
        current_app.logger,
    )


def _new_page():
    return redirect(url_for(
        'references.new_oed_reference',
        experiment_id=request.form.get('experiment_id'),
    ))


@references_bp.route('/oed/add', methods=['POST'])
@api_require_login_for_write
def add_oed_reference():
    try:
        result = _service().create_one(
            request.form.get('entry_id'),
            current_user,
            selected_sense_ids=request.form.getlist('sense_id'),
            title_override=request.form.get('title'),
            experiment_id=request.form.get('experiment_id'),
            include_in_analysis=(
                request.form.get('include_in_analysis') == 'true'
            ),
        )
    except OEDLookupError as exc:
        flash(f'OED lookup failed: {exc}', 'error')
        return _new_page()
    except (ValidationError, NotFoundError, PermissionError) as exc:
        flash(str(exc), 'error')
        return _new_page()

    if result.experiment:
        flash(
            f'Reference linked to experiment "{result.experiment.name}"',
            'success',
        )
        return redirect(url_for(
            'experiments.view',
            experiment_id=result.experiment.id,
        ))
    headword = result.document.source_metadata.get('headword')
    flash(f'Added OED reference for "{headword}"', 'success')
    return redirect(url_for('references.view', id=result.document.id))


@references_bp.route('/oed/add_batch', methods=['POST'])
@api_require_login_for_write
def add_oed_references_batch():
    try:
        result = _service().create_batch(
            request.form.getlist('entry_id'),
            current_user,
            experiment_id=request.form.get('experiment_id'),
            include_in_analysis=(
                request.form.get('include_in_analysis') == 'true'
            ),
        )
    except (ValidationError, NotFoundError, PermissionError) as exc:
        flash(str(exc), 'error')
        return _new_page()

    if result.documents:
        flash(f'Added {len(result.documents)} OED reference(s).', 'success')
    if result.errors:
        summary = '; '.join(result.errors[:4])
        if len(result.errors) > 4:
            summary += ' …'
        flash(f'Some entries failed: {summary}', 'warning')
    if result.experiment and result.documents:
        flash(f'Linked to experiment "{result.experiment.name}"', 'success')
        return redirect(url_for(
            'experiments.view',
            experiment_id=result.experiment.id,
        ))
    return redirect(url_for('references.index'))
