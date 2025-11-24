"""
Settings Management Routes

Provides UI for managing:
- Prompt templates
- LLM integration settings
- NLP tool defaults
- Processing defaults
- UI preferences
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import current_user
from app.utils.auth_decorators import api_require_login_for_write
from app import db
from app.models.app_settings import AppSetting
from app.models.prompt_template import PromptTemplate
from jinja2 import Template, TemplateSyntaxError
import logging

logger = logging.getLogger(__name__)

settings_bp = Blueprint('settings', __name__, url_prefix='/settings')


@settings_bp.route('/')
@api_require_login_for_write
def index():
    """Settings dashboard with tabbed interface (admin only)."""

    # Only administrators can access system settings
    if not current_user.is_admin:
        flash('Only administrators can access system settings.', 'danger')
        return redirect(url_for('main.index'))

    # Get all categories
    categories = ['prompts', 'nlp', 'processing', 'llm', 'ui']

    # Get settings by category
    user_id = current_user.id if current_user.is_authenticated else None
    settings_by_category = {}
    for category in categories:
        settings_by_category[category] = AppSetting.get_category_settings(category, user_id)

    # Get all prompt templates
    templates = PromptTemplate.query.filter_by(is_active=True).all()

    # Check for API key availability
    import os
    api_key_available = bool(os.getenv('ANTHROPIC_API_KEY'))

    return render_template('settings/index.html',
                         settings=settings_by_category,
                         templates=templates,
                         active_tab=request.args.get('tab', 'llm'),
                         api_key_available=api_key_available)


@settings_bp.route('/update', methods=['POST'])
@api_require_login_for_write
def update_setting():
    """Update a single setting."""
    try:
        data = request.get_json()

        setting_key = data.get('setting_key')
        setting_value = data.get('setting_value')
        category = data.get('category')
        data_type = data.get('data_type', 'string')
        user_specific = data.get('user_specific', False)

        if not setting_key or setting_value is None:
            return jsonify({'error': 'Setting key and value required'}), 400

        # Convert value to appropriate type
        if data_type == 'integer':
            setting_value = int(setting_value)
        elif data_type == 'boolean':
            setting_value = bool(setting_value)

        # Update or create setting
        user_id = current_user.id if user_specific else None
        AppSetting.set_setting(
            key=setting_key,
            value=setting_value,
            category=category,
            data_type=data_type,
            user_id=user_id
        )

        return jsonify({
            'success': True,
            'message': f'Setting {setting_key} updated',
            'setting_key': setting_key,
            'setting_value': setting_value
        })

    except Exception as e:
        logger.error(f"Error updating setting: {e}")
        return jsonify({'error': str(e)}), 500


@settings_bp.route('/template/<int:template_id>', methods=['GET'])
@api_require_login_for_write
def get_template(template_id):
    """Get template details for editing."""
    template = PromptTemplate.query.get_or_404(template_id)

    return jsonify({
        'id': template.id,
        'template_key': template.template_key,
        'template_text': template.template_text,
        'category': template.category,
        'variables': template.variables,
        'supports_llm_enhancement': template.supports_llm_enhancement,
        'llm_enhancement_prompt': template.llm_enhancement_prompt,
        'is_active': template.is_active
    })


@settings_bp.route('/template/<int:template_id>', methods=['PUT'])
@api_require_login_for_write
def update_template(template_id):
    """Update a prompt template."""
    try:
        template = PromptTemplate.query.get_or_404(template_id)
        data = request.get_json()

        # Update fields
        if 'template_text' in data:
            template.template_text = data['template_text']
            # Validate syntax
            try:
                template.validate_template()
            except TemplateSyntaxError as e:
                return jsonify({'error': f'Invalid template syntax: {str(e)}'}), 400

        if 'llm_enhancement_prompt' in data:
            template.llm_enhancement_prompt = data['llm_enhancement_prompt']

        if 'supports_llm_enhancement' in data:
            template.supports_llm_enhancement = data['supports_llm_enhancement']

        if 'is_active' in data:
            template.is_active = data['is_active']

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Template {template.template_key} updated'
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating template: {e}")
        return jsonify({'error': str(e)}), 500


@settings_bp.route('/template/<int:template_id>/test', methods=['POST'])
@api_require_login_for_write
def test_template(template_id):
    """Test a template with sample data."""
    try:
        template = PromptTemplate.query.get_or_404(template_id)
        data = request.get_json()

        context = data.get('context', {})

        # Render template
        try:
            result = template.render(context)
            return jsonify({
                'success': True,
                'result': result
            })
        except ValueError as e:
            return jsonify({'error': f'Missing variables: {str(e)}'}), 400
        except TemplateSyntaxError as e:
            return jsonify({'error': f'Template syntax error: {str(e)}'}), 400

    except Exception as e:
        logger.error(f"Error testing template: {e}")
        return jsonify({'error': str(e)}), 500


@settings_bp.route('/reset/<category>', methods=['POST'])
@api_require_login_for_write
def reset_category(category):
    """Reset all user settings in a category to system defaults."""
    try:
        # Delete user-specific settings in this category
        AppSetting.query.filter_by(
            category=category,
            user_id=current_user.id
        ).delete()

        db.session.commit()

        flash(f'Settings in {category} category reset to defaults', 'success')
        return redirect(url_for('settings.index', tab=category))

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error resetting category: {e}")
        flash(f'Error resetting settings: {str(e)}', 'danger')
        return redirect(url_for('settings.index', tab=category))


@settings_bp.route('/test-llm-connection', methods=['POST'])
@api_require_login_for_write
def test_llm_connection():
    """Test LLM API connection."""
    try:
        data = request.get_json()
        provider = data.get('provider', 'anthropic')

        from app.services.prompt_service import PromptService

        # Get API key
        api_key = PromptService._get_api_key(provider, current_user)
        if not api_key:
            return jsonify({
                'success': False,
                'error': f'No API key found for {provider}. Add it to settings or set environment variable.'
            }), 400

        # Try a simple test call
        test_prompt = "Respond with: 'Connection successful!'"

        if provider == 'anthropic':
            result = PromptService._call_anthropic(test_prompt, 'claude-sonnet-4-5-20250929', api_key)
        elif provider == 'openai':
            result = PromptService._call_openai(test_prompt, 'gpt-4', api_key)
        else:
            return jsonify({'success': False, 'error': f'Unknown provider: {provider}'}), 400

        return jsonify({
            'success': True,
            'message': 'Connection successful!',
            'response': result[:100] + '...' if len(result) > 100 else result
        })

    except Exception as e:
        logger.error(f"LLM connection test failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
