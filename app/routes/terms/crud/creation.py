"""Term creation page adapter."""

from flask import current_app, flash, redirect, render_template, url_for
from flask_login import current_user

from app.forms import AddTermForm
from app.services.base_service import PermissionError, ServiceError, ValidationError
from app.services.provenance_service import provenance_service
from app.services.term_creation_service import (
    DuplicateTermError,
    TermCreationService,
)
from app.utils.auth_decorators import write_login_required

from .. import terms_bp


def _service():
    return TermCreationService(
        provenance_service=provenance_service,
        workflow_logger=current_app.logger,
    )


@terms_bp.route('/add', methods=['GET', 'POST'])
@write_login_required
def add_term():
    form = AddTermForm()
    if form.validate_on_submit():
        try:
            term = _service().create(
                TermCreationService.form_data(form),
                current_user.id,
            )
            flash(
                f'Term "{term.term_text}" created successfully with first '
                'temporal version.',
                'success',
            )
            return redirect(url_for('terms.view_term', term_id=term.id))
        except DuplicateTermError as exc:
            flash(f'{exc}. Please choose a different term.', 'error')
        except ValidationError as exc:
            flash(str(exc), 'error')
        except PermissionError:
            flash('Permission denied', 'error')
        except ServiceError as exc:
            current_app.logger.error(
                'Term creation failed: %s',
                exc,
                exc_info=True,
            )
            flash(
                'An error occurred while creating the term. Please try again.',
                'error',
            )
    try:
        context = TermCreationService.page_context(current_user.id)
    except PermissionError:
        context = {'existing_domains': [], 'documents': []}
    return render_template('terms/add.html', form=form, **context)
