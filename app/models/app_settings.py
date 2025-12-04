from app import db
from datetime import datetime
from typing import Any, Dict, Optional


class AppSetting(db.Model):
    """
    Application settings with category-based organization.

    Supports both system-wide and user-specific settings.
    Settings are stored as JSONB for flexibility.
    """
    __tablename__ = 'app_settings'

    id = db.Column(db.Integer, primary_key=True)
    setting_key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    setting_value = db.Column(db.JSON, nullable=False)
    category = db.Column(db.String(50), nullable=False, index=True)  # 'prompts', 'nlp', 'processing', 'llm', 'ui'
    data_type = db.Column(db.String(20), nullable=False)  # 'string', 'integer', 'boolean', 'json'
    description = db.Column(db.Text)
    default_value = db.Column(db.JSON)
    requires_llm = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # NULL = system-wide
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = db.relationship('User', backref='settings', lazy='select')

    @classmethod
    def get_setting(cls, key: str, user_id: Optional[int] = None, default: Any = None) -> Any:
        """
        Get a setting value, checking user-specific first, then system-wide.

        Args:
            key: Setting key
            user_id: Optional user ID for user-specific settings
            default: Default value if setting not found

        Returns:
            Setting value or default
        """
        if user_id:
            user_setting = cls.query.filter_by(setting_key=key, user_id=user_id).first()
            if user_setting:
                return user_setting.setting_value

        system_setting = cls.query.filter_by(setting_key=key, user_id=None).first()
        if system_setting:
            return system_setting.setting_value

        return default

    @classmethod
    def set_setting(cls, key: str, value: Any, category: str, data_type: str = 'string',
                   description: str = None, user_id: Optional[int] = None) -> 'AppSetting':
        """
        Set a setting value, creating or updating as needed.

        Args:
            key: Setting key
            value: Setting value (will be JSON serialized)
            category: Setting category
            data_type: Data type hint
            description: Optional description
            user_id: Optional user ID for user-specific settings

        Returns:
            AppSetting instance
        """
        setting = cls.query.filter_by(setting_key=key, user_id=user_id).first()

        if setting:
            setting.setting_value = value
            setting.updated_at = datetime.utcnow()
        else:
            setting = cls(
                setting_key=key,
                setting_value=value,
                category=category,
                data_type=data_type,
                description=description,
                user_id=user_id
            )
            db.session.add(setting)

        db.session.commit()
        return setting

    @classmethod
    def get_category_settings(cls, category: str, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get all settings in a category as a dictionary.

        Args:
            category: Setting category
            user_id: Optional user ID for user-specific settings

        Returns:
            Dictionary of setting_key: setting_value
        """
        query = cls.query.filter_by(category=category)

        if user_id:
            # Get user-specific settings, falling back to system settings
            user_settings = query.filter_by(user_id=user_id).all()
            system_settings = query.filter_by(user_id=None).all()

            # Merge with user settings taking precedence
            result = {s.setting_key: s.setting_value for s in system_settings}
            result.update({s.setting_key: s.setting_value for s in user_settings})
            return result
        else:
            # Only system settings
            settings = query.filter_by(user_id=None).all()
            return {s.setting_key: s.setting_value for s in settings}

    @classmethod
    def seed_defaults(cls):
        """Seed default settings if they don't exist.

        Only includes settings that are actually used in the codebase:
        - enable_llm_enhancement: controls PromptService.render_and_enhance()
        - llm_max_tokens: controls max response length for LLM calls
        - default_llm_provider: used when calling LLM APIs
        - llm_model: default model for LLM calls
        - definition_extraction_confidence_threshold: controls definition extraction sensitivity
        """
        defaults = [
            # LLM Integration Settings (used in prompt_service.py)
            ('default_llm_provider', 'anthropic', 'llm', 'string', 'Default LLM provider'),
            ('enable_llm_enhancement', True, 'llm', 'boolean', 'Enable LLM template enhancement (requires API key)'),
            ('llm_model', 'claude-sonnet-4-5-20250929', 'llm', 'string', 'Default LLM model'),
            ('llm_max_tokens', 200, 'llm', 'integer', 'Maximum tokens for LLM responses'),

            # NLP Tool Settings (used in processing_tools.py)
            ('definition_extraction_confidence_threshold', 0.70, 'nlp', 'float', 'Confidence threshold for definition extraction'),

            # Provenance Settings
            ('purge_provenance_on_delete', True, 'provenance', 'boolean',
             'When enabled, provenance records are permanently deleted with documents/terms/experiments. When disabled, records are marked as invalidated but preserved for audit trail.'),
            ('show_deleted_in_timeline', False, 'provenance', 'boolean',
             'Default visibility of invalidated items in timeline views (only relevant when purge_provenance_on_delete is disabled)'),
        ]

        for key, value, category, data_type, description in defaults:
            existing = cls.query.filter_by(setting_key=key, user_id=None).first()
            if not existing:
                setting = cls(
                    setting_key=key,
                    setting_value=value,
                    category=category,
                    data_type=data_type,
                    description=description,
                    default_value=value,
                    user_id=None
                )
                db.session.add(setting)

        db.session.commit()

    def __repr__(self):
        return f'<AppSetting {self.setting_key}={self.setting_value} ({self.category})>'
