"""OED reference form pages."""

from flask import render_template, request

from app.utils.auth_decorators import api_require_login_for_write

from .. import references_bp


@references_bp.route('/oed/new')
@api_require_login_for_write
def new_oed_reference():
    """Render a page to add an OED entry as a reference.

    For now we accept an entry_id (e.g., orchestra_nn01). We'll offer a preview via the API.
    """
    experiment_id = request.args.get('experiment_id')
    return render_template('references/add_oed.html', experiment_id=experiment_id)
