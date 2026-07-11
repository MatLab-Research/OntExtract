"""Read-only OED API adapter routes."""

from flask import jsonify, request

from app.services.oed_service import OEDService
from app.utils.auth_decorators import api_require_login_for_write

from .. import references_bp


@references_bp.route('/api/oed/entry')
@api_require_login_for_write
def api_oed_entry():
    """Lookup an OED entry by headword via OED API (if enabled)."""
    headword = request.args.get('q', '').strip()
    if not headword:
        return jsonify({"success": False, "error": "Missing 'q' query param"}), 400

    svc = OEDService()
    data = svc.get_entry(headword)
    status = 200 if data.get('success', True) else 502
    return jsonify(data), status


@references_bp.route('/api/oed/word/<entry_id>')
@api_require_login_for_write
def api_oed_word(entry_id: str):
    svc = OEDService()
    data = svc.get_word(entry_id)
    status = 200 if data.get('success', True) else 502
    return jsonify(data), status


@references_bp.route('/api/oed/word/<entry_id>/quotations')
@api_require_login_for_write
def api_oed_word_quotations(entry_id: str):
    svc = OEDService()
    # Optional pagination
    try:
        limit_str = request.args.get('limit')
        offset_str = request.args.get('offset')
        limit = int(limit_str) if isinstance(limit_str, str) and limit_str.strip() else None
        offset = int(offset_str) if isinstance(offset_str, str) and offset_str.strip() else None
    except ValueError:
        return jsonify({"success": False, "error": "limit/offset must be integers"}), 400
    data = svc.get_quotations(entry_id, limit=limit, offset=offset)
    status = 200 if data.get('success', True) else 502
    return jsonify(data), status


@references_bp.route('/api/oed/suggest')
@api_require_login_for_write
def api_oed_suggest():
    q = (request.args.get('q') or '').strip()
    if not q:
        return jsonify({"success": False, "error": "Missing 'q' headword"}), 400
    svc = OEDService()
    data = svc.suggest_ids(q)
    status = 200 if data.get('success', True) else 502
    return jsonify(data), status


@references_bp.route('/api/oed/variants')
@api_require_login_for_write
def api_oed_variants():
    q = (request.args.get('q') or '').strip()
    if not q:
        return jsonify({"success": False, "error": "Missing 'q' headword"}), 400
    svc = OEDService()
    data = svc.get_variants(q)
    status = 200 if data.get('success', True) else 502
    return jsonify(data), status
