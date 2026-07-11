"""Administrative operational error-log page."""

from flask import render_template, request

from app.services.admin_error_read_service import AdminErrorReadService
from app.utils.auth_decorators import admin_required

from . import admin_bp


@admin_bp.route('/admin/errors')
@admin_required
def error_log():
    context = AdminErrorReadService().get_context(
        source=request.args.get('source', 'all'),
        time_filter=request.args.get('time', '24h'),
        search_query=request.args.get('q', ''),
    )
    return render_template('admin/errors.html', **context)
