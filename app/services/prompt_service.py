"""
Prompt Template Service

Dual-path workflow for generating descriptions:
1. Template-only: Fast Jinja2 rendering (no API key required)
2. LLM-enhanced: Template + LLM enhancement (requires API key)

All LLM calls tracked via PROV-O provenance.
"""

from typing import Dict, Any, Optional
from datetime import datetime
from jinja2 import Template, TemplateSyntaxError
import logging
import os

from app import db
from app.models.prompt_template import PromptTemplate
from app.models.app_settings import AppSetting
from app.services.provenance_service import ProvenanceService
from app.models.prov_o_models import ProvActivity, ProvEntity, ProvAgent

logger = logging.getLogger(__name__)


class PromptService:
    """
    Service for rendering prompt templates with optional LLM enhancement.

    Supports dual-path workflow:
    - Template-only: render_template() - Fast, no API key needed
    - LLM-enhanced: render_and_enhance() - Template + LLM improvement
    """

    @staticmethod
    def render_template(template_key: str, context: Dict[str, Any]) -> str:
        """
        Render a template with provided context (template-only path).

        Args:
            template_key: Template identifier
            context: Dictionary of template variables

        Returns:
            Rendered string

        Raises:
            ValueError: If template not found or variables missing
            TemplateSyntaxError: If template syntax invalid
        """
        template = PromptTemplate.get_template(template_key)
        if not template:
            raise ValueError(f"Template '{template_key}' not found")

        try:
            return template.render(context)
        except ValueError as e:
            logger.error(f"Template rendering failed: {e}")
            raise
        except TemplateSyntaxError as e:
            logger.error(f"Template syntax error: {e}")
            raise

    @staticmethod
    def render_and_enhance(
        template_key: str,
        context: Dict[str, Any],
        user,
        provider: str = None,
        model: str = None
    ) -> Dict[str, Any]:
        """
        Render template and enhance with LLM (dual-path with enhancement).

        Args:
            template_key: Template identifier
            context: Dictionary of template variables
            user: User model instance (for provenance)
            provider: Optional LLM provider override ('anthropic', 'openai')
            model: Optional model override

        Returns:
            Dictionary with:
                - template_output: Rendered template
                - enhanced_output: LLM-enhanced text
                - used_llm: Whether LLM was actually used
                - activity_id: Provenance activity ID (if LLM used)

        Raises:
            ValueError: If template not found or LLM not configured
        """
        # Get template
        template = PromptTemplate.get_template(template_key)
        if not template:
            raise ValueError(f"Template '{template_key}' not found")

        # Render template
        template_output = template.render(context)

        # Check if LLM enhancement is supported and enabled
        if not template.supports_llm_enhancement:
            return {
                'template_output': template_output,
                'enhanced_output': template_output,
                'used_llm': False,
                'activity_id': None
            }

        # Get LLM settings
        llm_enabled = AppSetting.get_setting('enable_llm_enhancement', user.id if user else None, default=False)
        if not llm_enabled:
            return {
                'template_output': template_output,
                'enhanced_output': template_output,
                'used_llm': False,
                'activity_id': None
            }

        # Get API key
        api_key = PromptService._get_api_key(provider or 'anthropic', user)
        if not api_key:
            logger.warning(f"LLM enhancement requested but no API key found for user {user.id if user else 'system'}")
            return {
                'template_output': template_output,
                'enhanced_output': template_output,
                'used_llm': False,
                'activity_id': None
            }

        # Enhance with LLM
        try:
            provider = provider or AppSetting.get_setting('default_llm_provider', user.id if user else None, default='anthropic')
            model = model or AppSetting.get_setting('llm_model', user.id if user else None, default='claude-3-5-sonnet-20241022')

            enhanced_output, activity_id = PromptService._enhance_with_llm(
                template=template,
                template_output=template_output,
                context=context,
                user=user,
                provider=provider,
                model=model,
                api_key=api_key
            )

            return {
                'template_output': template_output,
                'enhanced_output': enhanced_output,
                'used_llm': True,
                'activity_id': str(activity_id)
            }

        except Exception as e:
            logger.error(f"LLM enhancement failed: {e}")
            # Graceful fallback to template-only
            return {
                'template_output': template_output,
                'enhanced_output': template_output,
                'used_llm': False,
                'activity_id': None,
                'error': str(e)
            }

    @staticmethod
    def _get_api_key(provider: str, user) -> Optional[str]:
        """
        Get API key for provider, checking user settings then environment.

        Args:
            provider: 'anthropic' or 'openai'
            user: User instance

        Returns:
            API key or None
        """
        # Check user-specific setting first
        if user:
            key = AppSetting.get_setting(f'{provider}_api_key', user.id)
            if key:
                return key

        # Fall back to environment variable
        env_var = f'{provider.upper()}_API_KEY'
        return os.environ.get(env_var)

    @staticmethod
    def _enhance_with_llm(
        template: PromptTemplate,
        template_output: str,
        context: Dict[str, Any],
        user,
        provider: str,
        model: str,
        api_key: str
    ) -> tuple[str, Any]:
        """
        Call LLM to enhance template output and track via provenance.

        Args:
            template: PromptTemplate instance
            template_output: Rendered template text
            context: Original template context
            user: User instance
            provider: LLM provider
            model: Model name
            api_key: API key

        Returns:
            (enhanced_text, activity_id)
        """
        start_time = datetime.utcnow()

        # Prepare enhancement prompt
        enhancement_context = context.copy()
        enhancement_context['template_output'] = template_output
        enhancement_prompt_template = Template(template.llm_enhancement_prompt)
        enhancement_prompt = enhancement_prompt_template.render(**enhancement_context)

        # Call LLM based on provider
        if provider == 'anthropic':
            enhanced_text = PromptService._call_anthropic(enhancement_prompt, model, api_key)
        elif provider == 'openai':
            enhanced_text = PromptService._call_openai(enhancement_prompt, model, api_key)
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

        end_time = datetime.utcnow()

        # Track via provenance
        activity_id = PromptService._track_llm_enhancement(
            template=template,
            context=context,
            template_output=template_output,
            enhanced_output=enhanced_text,
            user=user,
            provider=provider,
            model=model,
            start_time=start_time,
            end_time=end_time
        )

        return enhanced_text, activity_id

    @staticmethod
    def _call_anthropic(prompt: str, model: str, api_key: str) -> str:
        """
        Call Anthropic API for text enhancement.

        Args:
            prompt: Enhancement prompt
            model: Model name
            api_key: API key

        Returns:
            Enhanced text
        """
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)

            max_tokens = AppSetting.get_setting('llm_max_tokens', default=500)

            message = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            return message.content[0].text

        except Exception as e:
            logger.error(f"Anthropic API call failed: {e}")
            raise

    @staticmethod
    def _call_openai(prompt: str, model: str, api_key: str) -> str:
        """
        Call OpenAI API for text enhancement.

        Args:
            prompt: Enhancement prompt
            model: Model name
            api_key: API key

        Returns:
            Enhanced text
        """
        try:
            import openai
            client = openai.OpenAI(api_key=api_key)

            max_tokens = AppSetting.get_setting('llm_max_tokens', default=500)

            response = client.chat.completions.create(
                model=model,
                max_tokens=max_tokens,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            raise

    @staticmethod
    def _track_llm_enhancement(
        template: PromptTemplate,
        context: Dict[str, Any],
        template_output: str,
        enhanced_output: str,
        user,
        provider: str,
        model: str,
        start_time: datetime,
        end_time: datetime
    ) -> Any:
        """
        Track LLM enhancement via PROV-O provenance.

        Args:
            template: PromptTemplate instance
            context: Template context
            template_output: Rendered template
            enhanced_output: LLM-enhanced output
            user: User instance
            provider: LLM provider
            model: Model name
            start_time: Enhancement start time
            end_time: Enhancement end time

        Returns:
            Activity ID
        """
        # Get agents
        llm_agent = ProvenanceService.get_or_create_llm_agent(provider=provider, model_id=model)
        user_agent = ProvenanceService.get_or_create_user_agent(user.id, user.username)

        # Create activity
        activity = ProvActivity(
            activity_type='prompt_enhancement',
            startedattime=start_time,
            endedattime=end_time,
            wasassociatedwith=llm_agent.agent_id,
            activity_parameters={
                'template_key': template.template_key,
                'category': template.category,
                'provider': provider,
                'model': model,
                'user_id': user.id,
                'input_context': context,
                'template_output_length': len(template_output),
                'enhanced_output_length': len(enhanced_output)
            },
            activity_status='completed'
        )
        db.session.add(activity)
        db.session.flush()

        # Create entity for enhanced output
        entity = ProvEntity(
            entity_type='enhanced_description',
            generatedattime=end_time,
            wasgeneratedby=activity.activity_id,
            wasattributedto=llm_agent.agent_id,
            entity_value={
                'template_key': template.template_key,
                'category': template.category,
                'template_output': template_output,
                'enhanced_output': enhanced_output,
                'provider': provider,
                'model': model
            }
        )
        db.session.add(entity)
        db.session.commit()

        return activity.activity_id

    @staticmethod
    def _get_template_key(experiment_type: str) -> str:
        """
        Get template key for experiment type.

        Args:
            experiment_type: Experiment type string

        Returns:
            Template key string
        """
        mapping = {
            'single_document_analysis': 'experiment_description_single_document',
            'document_analysis': 'experiment_description_multi_document',
            'temporal_evolution': 'experiment_description_temporal',
            'domain_comparison': 'experiment_description_domain_comparison'
        }
        return mapping.get(experiment_type, 'experiment_description_single_document')

    @staticmethod
    def _build_experiment_context(
        experiment_type: str,
        documents: list,
        references: list,
        configuration: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Build template context from experiment data.

        Args:
            experiment_type: Type of experiment
            documents: List of Document instances
            references: List of reference Document instances
            configuration: Experiment configuration dict

        Returns:
            Template context dictionary
        """
        # Filter out None values
        documents = [d for d in documents if d]
        references = [r for r in references if r]

        if experiment_type == 'single_document_analysis':
            doc = documents[0] if documents else None
            return {
                'document_title': doc.title if doc else 'Unknown',
                'word_count': doc.word_count or 0 if doc else 0
            }

        elif experiment_type == 'document_analysis':
            total_words = sum(d.word_count or 0 for d in documents)
            # Try to infer domain from document metadata
            domain = None
            if documents and documents[0].source_metadata:
                domain = documents[0].source_metadata.get('domain') or documents[0].source_metadata.get('subject')

            return {
                'document_count': len(documents),
                'total_words': total_words,
                'domain': domain or ''
            }

        elif experiment_type == 'temporal_evolution':
            years = []
            for doc in documents:
                if doc.source_metadata and 'year' in doc.source_metadata:
                    try:
                        years.append(int(doc.source_metadata['year']))
                    except (ValueError, TypeError):
                        pass

            return {
                'term_text': configuration.get('focus_term', 'term'),
                'document_count': len(documents),
                'earliest_year': min(years) if years else 1900,
                'latest_year': max(years) if years else 2025
            }

        elif experiment_type == 'domain_comparison':
            domains = configuration.get('domain_focus', '')
            domain_list = [d.strip() for d in domains.split(',') if d.strip()] if domains else []

            return {
                'term_text': configuration.get('focus_term', 'term'),
                'domain_count': len(domain_list) if domain_list else 2,
                'domain_list': ', '.join(domain_list) if domain_list else 'multiple domains'
            }

        else:
            # Fallback to single document template
            doc = documents[0] if documents else None
            return {
                'document_title': doc.title if doc else 'Unknown',
                'word_count': doc.word_count or 0 if doc else 0
            }


# Singleton instance for easy import
prompt_service = PromptService()
