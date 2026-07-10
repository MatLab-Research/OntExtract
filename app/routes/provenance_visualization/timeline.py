"""Authorized PROV-O timeline pages."""

from flask import abort, render_template, request
from flask_login import current_user, login_required

from app.services.base_service import NotFoundError, PermissionError, ValidationError
from app.services.provenance_visualization_service import (
    ProvenanceVisualizationService,
)

from . import bp


def _page_error(exc):
    if isinstance(exc, ValidationError):
        abort(400)
    if isinstance(exc, PermissionError):
        abort(403)
    abort(404)


@bp.route('/timeline')
@login_required
def timeline():
    try:
        context = ProvenanceVisualizationService.timeline_context(
            request.args,
            current_user.id,
        )
    except (ValidationError, PermissionError, NotFoundError) as exc:
        _page_error(exc)
    return render_template('provenance/timeline.html', **context)


@bp.route('/experiment/<int:experiment_id>')
@login_required
def experiment_timeline(experiment_id):
    try:
        context = ProvenanceVisualizationService.experiment_context(
            experiment_id,
            current_user.id,
        )
    except (PermissionError, NotFoundError) as exc:
        _page_error(exc)
    return render_template('provenance/experiment_timeline.html', **context)
