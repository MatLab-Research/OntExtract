"""
LLM Configuration Manager

Provides a structured interface for accessing task-specific LLM model configurations.
Supports multiple providers (Gemini, Anthropic, OpenAI) with fallback strategies.
"""

from typing import Tuple, Optional
from flask import current_app
import logging

logger = logging.getLogger(__name__)


class LLMTaskType:
    """Enumeration of LLM task types with specific model requirements"""
    EXTRACTION = "extraction"  # Structured extraction (LangExtract)
    SYNTHESIS = "synthesis"  # Semantic analysis & reasoning
    ORCHESTRATION = "orchestration"  # Tool routing & decisions
    OED_PARSING = "oed_parsing"  # OED entry parsing
    LONG_CONTEXT = "long_context"  # Long document processing
    CLASSIFICATION = "classification"  # Fast classification tasks
    FALLBACK = "fallback"  # Default fallback


class LLMConfigManager:
    """
    Centralized LLM configuration manager

    Provides easy access to task-specific model configurations with provider flexibility.

    Example:
        >>> config = LLMConfigManager()
        >>> provider, model = config.get_model_for_task(LLMTaskType.EXTRACTION)
        >>> # Returns: ('gemini', 'gemini-2.5-flash')
    """

    def __init__(self, app=None):
        """
        Initialize LLM configuration manager

        Args:
            app: Flask application instance (optional, uses current_app if not provided)
        """
        self.app = app

    def _get_config(self, key: str, default: any = None) -> any:
        """Get configuration value from Flask config or default"""
        if self.app:
            return self.app.config.get(key, default)
        elif current_app:
            return current_app.config.get(key, default)
        else:
            return default

    def get_model_for_task(self, task_type: str) -> Tuple[str, str]:
        """
        Get the provider and model ID for a specific task type

        Args:
            task_type: Task type from LLMTaskType enum

        Returns:
            Tuple of (provider, model_id)

        Example:
            >>> provider, model = config.get_model_for_task(LLMTaskType.EXTRACTION)
            >>> # Returns: ('gemini', 'gemini-2.5-flash')
        """
        task_mapping = {
            LLMTaskType.EXTRACTION: (
                self._get_config('LLM_EXTRACTION_PROVIDER', 'gemini'),
                self._get_config('LLM_EXTRACTION_MODEL', 'gemini-2.5-flash')
            ),
            LLMTaskType.SYNTHESIS: (
                self._get_config('LLM_SYNTHESIS_PROVIDER', 'anthropic'),
                self._get_config('LLM_SYNTHESIS_MODEL', 'claude-sonnet-4-5')
            ),
            LLMTaskType.ORCHESTRATION: (
                self._get_config('LLM_ORCHESTRATION_PROVIDER', 'openai'),
                self._get_config('LLM_ORCHESTRATION_MODEL', 'gpt-5-mini')
            ),
            LLMTaskType.OED_PARSING: (
                self._get_config('LLM_OED_PARSING_PROVIDER', 'gemini'),
                self._get_config('LLM_OED_PARSING_MODEL', 'gemini-2.5-pro')
            ),
            LLMTaskType.LONG_CONTEXT: (
                self._get_config('LLM_LONG_CONTEXT_PROVIDER', 'anthropic'),
                self._get_config('LLM_LONG_CONTEXT_MODEL', 'claude-sonnet-4-5')
            ),
            LLMTaskType.CLASSIFICATION: (
                self._get_config('LLM_CLASSIFICATION_PROVIDER', 'gemini'),
                self._get_config('LLM_CLASSIFICATION_MODEL', 'gemini-2.5-flash-lite')
            ),
            LLMTaskType.FALLBACK: (
                self._get_config('LLM_FALLBACK_PROVIDER', 'openai'),
                self._get_config('LLM_FALLBACK_MODEL', 'gpt-5.1')
            )
        }

        provider, model = task_mapping.get(task_type, task_mapping[LLMTaskType.FALLBACK])

        logger.debug(f"LLM config for task '{task_type}': provider={provider}, model={model}")

        return provider, model

    def get_api_key_for_provider(self, provider: str) -> Optional[str]:
        """
        Get the API key for a specific provider

        Args:
            provider: Provider name ('gemini', 'anthropic', 'openai')

        Returns:
            API key string or None if not configured
        """
        key_mapping = {
            'gemini': 'GOOGLE_GEMINI_API_KEY',
            'google': 'GOOGLE_GEMINI_API_KEY',
            'anthropic': 'ANTHROPIC_API_KEY',
            'claude': 'ANTHROPIC_API_KEY',
            'openai': 'OPENAI_API_KEY',
            'gpt': 'OPENAI_API_KEY'
        }

        config_key = key_mapping.get(provider.lower())
        if not config_key:
            logger.warning(f"Unknown provider '{provider}', cannot determine API key")
            return None

        api_key = self._get_config(config_key)

        if not api_key:
            logger.warning(f"API key not configured for provider '{provider}' (config key: {config_key})")

        return api_key

    def get_extraction_config(self) -> dict:
        """Get configuration for structured extraction tasks"""
        provider, model = self.get_model_for_task(LLMTaskType.EXTRACTION)
        return {
            'provider': provider,
            'model': model,
            'api_key': self.get_api_key_for_provider(provider),
            'task_type': LLMTaskType.EXTRACTION,
            'description': 'Structured extraction (definitions, temporal markers, domain indicators)'
        }

    def get_synthesis_config(self) -> dict:
        """Get configuration for semantic analysis and synthesis tasks"""
        provider, model = self.get_model_for_task(LLMTaskType.SYNTHESIS)
        return {
            'provider': provider,
            'model': model,
            'api_key': self.get_api_key_for_provider(provider),
            'task_type': LLMTaskType.SYNTHESIS,
            'description': 'Semantic analysis, cross-document synthesis, complex reasoning'
        }

    def get_orchestration_config(self) -> dict:
        """Get configuration for orchestration and routing tasks"""
        provider, model = self.get_model_for_task(LLMTaskType.ORCHESTRATION)
        return {
            'provider': provider,
            'model': model,
            'api_key': self.get_api_key_for_provider(provider),
            'task_type': LLMTaskType.ORCHESTRATION,
            'description': 'Tool routing, task orchestration, confidence scoring'
        }

    def get_oed_parsing_config(self) -> dict:
        """Get configuration for OED dictionary parsing tasks"""
        provider, model = self.get_model_for_task(LLMTaskType.OED_PARSING)
        return {
            'provider': provider,
            'model': model,
            'api_key': self.get_api_key_for_provider(provider),
            'task_type': LLMTaskType.OED_PARSING,
            'description': 'OED entry parsing, etymology extraction, complex nested structures'
        }

    def get_long_context_config(self) -> dict:
        """Get configuration for long context processing tasks"""
        provider, model = self.get_model_for_task(LLMTaskType.LONG_CONTEXT)
        return {
            'provider': provider,
            'model': model,
            'api_key': self.get_api_key_for_provider(provider),
            'task_type': LLMTaskType.LONG_CONTEXT,
            'description': 'Long document processing, multi-document comparison (200k+ tokens)'
        }

    def get_classification_config(self) -> dict:
        """Get configuration for fast classification tasks"""
        provider, model = self.get_model_for_task(LLMTaskType.CLASSIFICATION)
        return {
            'provider': provider,
            'model': model,
            'api_key': self.get_api_key_for_provider(provider),
            'task_type': LLMTaskType.CLASSIFICATION,
            'description': 'Fast classification, domain detection, categorization'
        }

    def get_all_configurations(self) -> dict:
        """Get all task configurations for debugging/logging"""
        return {
            'extraction': self.get_extraction_config(),
            'synthesis': self.get_synthesis_config(),
            'orchestration': self.get_orchestration_config(),
            'oed_parsing': self.get_oed_parsing_config(),
            'long_context': self.get_long_context_config(),
            'classification': self.get_classification_config()
        }

    def validate_configuration(self) -> dict:
        """
        Validate all LLM configurations

        Returns:
            Dictionary with validation results for each provider
        """
        results = {
            'valid': True,
            'providers': {},
            'missing_api_keys': []
        }

        # Check each unique provider
        all_configs = self.get_all_configurations()
        providers_checked = set()

        for task_name, config in all_configs.items():
            provider = config['provider']
            if provider in providers_checked:
                continue

            providers_checked.add(provider)
            api_key = config['api_key']

            results['providers'][provider] = {
                'has_api_key': bool(api_key),
                'tasks_using': [t for t, c in all_configs.items() if c['provider'] == provider]
            }

            if not api_key:
                results['valid'] = False
                results['missing_api_keys'].append(provider)

        return results


# Singleton instance for easy access
_llm_config_manager = None


def get_llm_config() -> LLMConfigManager:
    """
    Get the singleton LLM configuration manager instance

    Returns:
        LLMConfigManager instance

    Example:
        >>> from config.llm_config import get_llm_config, LLMTaskType
        >>> config = get_llm_config()
        >>> provider, model = config.get_model_for_task(LLMTaskType.EXTRACTION)
    """
    global _llm_config_manager
    if _llm_config_manager is None:
        _llm_config_manager = LLMConfigManager()
    return _llm_config_manager
