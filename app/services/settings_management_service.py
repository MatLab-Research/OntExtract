"""System settings, prompt template, and LLM connection management."""

import json
import os

from jinja2 import Template, TemplateSyntaxError

from app import db
from app.models.app_settings import AppSetting
from app.models.prompt_template import PromptTemplate
from app.services.base_service import NotFoundError, ValidationError
from app.services.prompt_service import PromptService


class SettingsManagementService:
    """Manage administrator-visible application configuration."""

    CATEGORIES = ('prompts', 'nlp', 'processing', 'llm', 'ui', 'provenance')

    def __init__(self, prompt_service=None):
        self.prompt_service = prompt_service or PromptService

    @classmethod
    def dashboard_context(cls, user_id, active_tab='llm'):
        return {
            'settings': {
                category: AppSetting.get_category_settings(category, user_id)
                for category in cls.CATEGORIES
            },
            'templates': PromptTemplate.query.filter_by(is_active=True).all(),
            'active_tab': active_tab,
            'api_key_available': bool(os.getenv('ANTHROPIC_API_KEY')),
        }

    @classmethod
    def update_setting(cls, data, actor_id):
        if not isinstance(data, dict):
            raise ValidationError('Setting key and value required')
        key = data.get('setting_key')
        value = data.get('setting_value')
        if not key or value is None:
            raise ValidationError('Setting key and value required')
        category = data.get('category')
        if not category:
            raise ValidationError('Setting category required')
        data_type = data.get('data_type', 'string')
        converted = cls._convert_value(value, data_type)
        user_id = actor_id if data.get('user_specific', False) else None
        AppSetting.set_setting(
            key=key,
            value=converted,
            category=category,
            data_type=data_type,
            user_id=user_id,
        )
        return {
            'success': True,
            'message': f'Setting {key} updated',
            'setting_key': key,
            'setting_value': converted,
        }

    @classmethod
    def get_template(cls, template_id):
        template = cls._template(template_id)
        return {
            'id': template.id,
            'template_key': template.template_key,
            'template_text': template.template_text,
            'category': template.category,
            'variables': template.variables,
            'supports_llm_enhancement': template.supports_llm_enhancement,
            'llm_enhancement_prompt': template.llm_enhancement_prompt,
            'is_active': template.is_active,
        }

    @classmethod
    def update_template(cls, template_id, data):
        if not isinstance(data, dict):
            raise ValidationError('Template update payload required')
        template = cls._template(template_id)
        if 'template_text' in data:
            try:
                Template(data['template_text'])
            except TemplateSyntaxError as exc:
                raise ValidationError(f'Invalid template syntax: {exc}')
            template.template_text = data['template_text']
        if 'llm_enhancement_prompt' in data:
            template.llm_enhancement_prompt = data['llm_enhancement_prompt']
        if 'supports_llm_enhancement' in data:
            template.supports_llm_enhancement = cls._convert_boolean(
                data['supports_llm_enhancement']
            )
        if 'is_active' in data:
            template.is_active = cls._convert_boolean(data['is_active'])
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
        return {
            'success': True,
            'message': f'Template {template.template_key} updated',
        }

    @classmethod
    def test_template(cls, template_id, data):
        template = cls._template(template_id)
        context = data.get('context', {}) if isinstance(data, dict) else {}
        try:
            result = template.render(context)
        except ValueError as exc:
            raise ValidationError(f'Missing variables: {exc}')
        except TemplateSyntaxError as exc:
            raise ValidationError(f'Template syntax error: {exc}')
        return {'success': True, 'result': result}

    @staticmethod
    def reset_category(category, user_id):
        try:
            AppSetting.query.filter_by(
                category=category,
                user_id=user_id,
            ).delete()
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

    def test_llm_connection(self, provider, user):
        provider = provider or 'anthropic'
        if provider not in ('anthropic', 'openai'):
            raise ValidationError(f'Unknown provider: {provider}')
        api_key = self.prompt_service._get_api_key(provider, user)
        if not api_key:
            raise ValidationError(
                f'No API key found for {provider}. Add it to settings or set '
                'environment variable.'
            )
        prompt = "Respond with: 'Connection successful!'"
        if provider == 'anthropic':
            result = self.prompt_service._call_anthropic(
                prompt,
                'claude-sonnet-4-5-20250929',
                api_key,
            )
        else:
            result = self.prompt_service._call_openai(
                prompt,
                'gpt-4',
                api_key,
            )
        response = result[:100] + '...' if len(result) > 100 else result
        return {
            'success': True,
            'message': 'Connection successful!',
            'response': response,
        }

    @staticmethod
    def _template(template_id):
        template = db.session.get(PromptTemplate, template_id)
        if not template:
            raise NotFoundError(f'Prompt template {template_id} not found')
        return template

    @classmethod
    def _convert_value(cls, value, data_type):
        try:
            if data_type == 'integer':
                numeric = float(value)
                return int(numeric) if numeric.is_integer() else numeric
            if data_type == 'float':
                return float(value)
            if data_type == 'boolean':
                return cls._convert_boolean(value)
            if data_type == 'json' and isinstance(value, str):
                return json.loads(value)
            return value
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ValidationError(
                f'Invalid {data_type} value for setting'
            ) from exc

    @staticmethod
    def _convert_boolean(value):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in ('true', '1', 'yes', 'on'):
                return True
            if normalized in ('false', '0', 'no', 'off', ''):
                return False
        if isinstance(value, (int, float)) and value in (0, 1):
            return bool(value)
        raise ValidationError('Invalid boolean value for setting')
