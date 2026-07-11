"""Public document family listing and detail pages."""

from flask import abort, render_template, request

from app.services.base_service import NotFoundError
from app.services.document_page_service import DocumentPageService
from app.utils.auth_decorators import public_with_auth_context

from .. import text_input_bp


@text_input_bp.route('/documents')
@public_with_auth_context
def document_list():
    context = DocumentPageService.get_list_context(
        page=request.args.get('page', 1, type=int),
        source_type=request.args.get('type', 'all'),
    )
    return render_template('text_input/document_list.html', **context)


@text_input_bp.route('/document/<uuid:document_uuid>')
@public_with_auth_context
def document_detail(document_uuid):
    try:
        context = DocumentPageService.get_detail_context(document_uuid)
    except NotFoundError:
        abort(404)
    return render_template(
        'text_input/document_detail_simplified.html',
        **context,
    )
