"""Administrator-only settings management routes."""

import logging

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user

from app.services.base_service import NotFoundError, ValidationError
from app.services.settings_management_service import SettingsManagementService
from app.utils.auth_decorators import admin_required


logger = logging.getLogger(__name__)
settings_bp = Blueprint('settings', __name__, url_prefix='/settings')


def _json_error(operation, exc, status=500):
    logger.error(f'{operation}: {exc}', exc_info=status == 500)
    return jsonify({'error': str(exc)}), status


@settings_bp.route('/')
@admin_required
def index():
    context = SettingsManagementService.dashboard_context(
        current_user.id,
        request.args.get('tab', 'llm'),
    )
    return render_template('settings/index.html', **context)


@settings_bp.route('/update', methods=['POST'])
@admin_required
def update_setting():
    try:
        return jsonify(SettingsManagementService.update_setting(
            request.get_json(silent=True),
            current_user.id,
        ))
    except ValidationError as exc:
        return _json_error('Invalid setting update', exc, 400)
    except Exception as exc:
        return _json_error('Error updating setting', exc)


@settings_bp.route('/template/<int:template_id>', methods=['GET'])
@admin_required
def get_template(template_id):
    try:
        return jsonify(SettingsManagementService.get_template(template_id))
    except NotFoundError as exc:
        return _json_error('Template not found', exc, 404)


@settings_bp.route('/template/<int:template_id>', methods=['PUT'])
@admin_required
def update_template(template_id):
    try:
        return jsonify(SettingsManagementService.update_template(
            template_id,
            request.get_json(silent=True),
        ))
    except NotFoundError as exc:
        return _json_error('Template not found', exc, 404)
    except ValidationError as exc:
        return _json_error('Invalid template update', exc, 400)
    except Exception as exc:
        return _json_error('Error updating template', exc)


@settings_bp.route('/template/<int:template_id>/test', methods=['POST'])
@admin_required
def test_template(template_id):
    try:
        return jsonify(SettingsManagementService.test_template(
            template_id,
            request.get_json(silent=True),
        ))
    except NotFoundError as exc:
        return _json_error('Template not found', exc, 404)
    except ValidationError as exc:
        return _json_error('Template test failed', exc, 400)
    except Exception as exc:
        return _json_error('Error testing template', exc)


@settings_bp.route('/reset/<category>', methods=['POST'])
@admin_required
def reset_category(category):
    try:
        SettingsManagementService.reset_category(category, current_user.id)
        flash(f'Settings in {category} category reset to defaults', 'success')
    except Exception as exc:
        logger.error(f'Error resetting category: {exc}', exc_info=True)
        flash(f'Error resetting settings: {exc}', 'danger')
    return redirect(url_for('settings.index', tab=category))


@settings_bp.route('/test-llm-connection', methods=['POST'])
@admin_required
def test_llm_connection():
    try:
        data = request.get_json(silent=True) or {}
        return jsonify(SettingsManagementService().test_llm_connection(
            data.get('provider', 'anthropic'),
            current_user,
        ))
    except ValidationError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    except Exception as exc:
        logger.error(f'LLM connection test failed: {exc}', exc_info=True)
        return jsonify({'success': False, 'error': str(exc)}), 500
