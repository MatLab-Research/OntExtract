"""Reference document listing, detail, edit, delete, and download routes."""

from flask import abort, current_app, flash, redirect, render_template, send_file, request, url_for
from flask_login import current_user

from app.services.base_service import NotFoundError, PermissionError, ValidationError
from app.services.provenance_service import provenance_service
from app.services.reference_crud_service import (
    ReferenceCrudService,
    ReferenceInUseError,
)
from app.utils.auth_decorators import write_login_required

from . import references_bp


def _service():
    return ReferenceCrudService(provenance_service, current_app.logger)


def _not_found():
    abort(404)


@references_bp.route('/')
def index():
    return render_template(
        'references/index.html',
        references=ReferenceCrudService.list_references(),
    )


@references_bp.route('/<int:id>')
def view(id):
    try:
        context = ReferenceCrudService.detail_context(id)
    except NotFoundError:
        return _not_found()
    return render_template('references/view.html', **context)


@references_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@write_login_required
def edit(id):
    try:
        if request.method == 'POST':
            reference = ReferenceCrudService.update(
                id,
                current_user.id,
                request.form,
            )
            flash('Reference updated successfully', 'success')
            return redirect(url_for('references.view', id=reference.id))
        context = ReferenceCrudService.edit_context(id, current_user.id)
        return render_template('references/edit.html', **context)
    except NotFoundError:
        return _not_found()
    except PermissionError:
        flash('You do not have permission to edit this reference.', 'error')
        return redirect(url_for('references.view', id=id))
    except ValidationError as exc:
        flash(str(exc), 'error')
        try:
            context = ReferenceCrudService.edit_context(id, current_user.id)
        except (NotFoundError, PermissionError):
            return redirect(url_for('references.index'))
        return render_template('references/edit.html', **context), 400
    except Exception as exc:
        current_app.logger.error(
            f'Error updating reference {id}: {exc}',
            exc_info=True,
        )
        flash('Error updating reference', 'error')
        return redirect(url_for('references.view', id=id))


@references_bp.route('/<int:id>/delete', methods=['POST'])
@write_login_required
def delete(id):
    try:
        _service().delete(id, current_user.id)
        flash('Reference deleted successfully', 'success')
        return redirect(url_for('references.index'))
    except NotFoundError:
        return _not_found()
    except PermissionError:
        flash('You do not have permission to delete this reference.', 'error')
    except ReferenceInUseError as exc:
        names = ', '.join(
            f'"{experiment.name}"' for experiment in exc.experiments[:3]
        )
        if len(exc.experiments) > 3:
            names += f' and {len(exc.experiments) - 3} more'
        flash(
            'Cannot delete this reference because it is used in '
            f'{len(exc.experiments)} experiment(s): {names}.',
            'error',
        )
    except Exception as exc:
        current_app.logger.error(
            f'Error deleting reference {id}: {exc}',
            exc_info=True,
        )
        flash('Error deleting reference', 'error')
    return redirect(url_for('references.view', id=id))


@references_bp.route('/<int:id>/download')
def download(id):
    try:
        result = ReferenceCrudService.download(id)
        return send_file(
            result['path'],
            as_attachment=True,
            download_name=result['filename'],
        )
    except NotFoundError:
        return _not_found()
    except ValidationError as exc:
        flash(str(exc), 'warning')
        return redirect(url_for('references.view', id=id))
