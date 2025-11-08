from app import db
from datetime import datetime
from typing import Dict, Any, List, Optional
from jinja2 import Template, TemplateSyntaxError


class PromptTemplate(db.Model):
    """
    Jinja2 prompt templates for generating descriptions and prompts.

    Supports dual-path workflow: template-only or LLM-enhanced.
    """
    __tablename__ = 'prompt_templates'

    id = db.Column(db.Integer, primary_key=True)
    template_key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    template_text = db.Column(db.Text, nullable=False)  # Jinja2 template
    category = db.Column(db.String(50), nullable=False, index=True)  # 'experiment_description', 'analysis_summary', etc.
    variables = db.Column(db.JSON, nullable=False, default=dict)  # {'document_title': 'string', 'word_count': 'int'}
    supports_llm_enhancement = db.Column(db.Boolean, default=True)
    llm_enhancement_prompt = db.Column(db.Text)  # Prompt for LLM to enhance template output
    is_active = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @classmethod
    def get_template(cls, template_key: str) -> Optional['PromptTemplate']:
        """
        Get an active template by key.

        Args:
            template_key: Template identifier

        Returns:
            PromptTemplate instance or None
        """
        return cls.query.filter_by(template_key=template_key, is_active=True).first()

    @classmethod
    def get_by_category(cls, category: str) -> List['PromptTemplate']:
        """
        Get all active templates in a category.

        Args:
            category: Template category

        Returns:
            List of PromptTemplate instances
        """
        return cls.query.filter_by(category=category, is_active=True).all()

    def render(self, context: Dict[str, Any]) -> str:
        """
        Render template with provided context.

        Args:
            context: Dictionary of template variables

        Returns:
            Rendered string

        Raises:
            TemplateSyntaxError: If template syntax is invalid
            ValueError: If required variables are missing
        """
        # Validate required variables
        missing_vars = set(self.variables.keys()) - set(context.keys())
        if missing_vars:
            raise ValueError(f"Missing required variables: {missing_vars}")

        try:
            template = Template(self.template_text)
            return template.render(**context)
        except TemplateSyntaxError as e:
            raise TemplateSyntaxError(f"Invalid template syntax in {self.template_key}: {e}")

    def get_llm_enhancement_context(self, rendered_template: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare context for LLM enhancement.

        Args:
            rendered_template: The rendered template output
            context: Original template context

        Returns:
            Dictionary with all context for LLM
        """
        return {
            'template_output': rendered_template,
            'template_key': self.template_key,
            'category': self.category,
            'context': context,
            'enhancement_prompt': self.llm_enhancement_prompt
        }

    @classmethod
    def seed_defaults(cls):
        """Seed default prompt templates."""
        defaults = [
            {
                'template_key': 'experiment_description_single_document',
                'template_text': "Analysis of '{{ document_title }}' ({{ word_count }} words)",
                'category': 'experiment_description',
                'variables': {'document_title': 'string', 'word_count': 'int'},
                'supports_llm_enhancement': True,
                'llm_enhancement_prompt': '''Enhance this experiment description with 2-3 sentences about the document's research domain and potential analytical value. Keep it concise and factual.

Document metadata:
- Title: {{ document_title }}
- Word count: {{ word_count }}
{% if year %}- Year: {{ year }}{% endif %}
{% if authors %}- Authors: {{ authors }}{% endif %}

Current description: {{ template_output }}

Enhanced description:'''
            },
            {
                'template_key': 'experiment_description_multi_document',
                'template_text': "Comparative analysis of {{ document_count }} documents ({{ total_words }} words total){% if domain %} in {{ domain }} domain{% endif %}",
                'category': 'experiment_description',
                'variables': {'document_count': 'int', 'total_words': 'int', 'domain': 'string'},
                'supports_llm_enhancement': True,
                'llm_enhancement_prompt': '''Enhance this experiment description by suggesting 2-3 potential research questions or analytical approaches for comparing these documents.

Experiment metadata:
- Document count: {{ document_count }}
- Total words: {{ total_words }}
{% if domain %}- Domain: {{ domain }}{% endif %}

Current description: {{ template_output }}

Enhanced description:'''
            },
            {
                'template_key': 'experiment_description_temporal',
                'template_text': "Tracking evolution of term '{{ term_text }}' across {{ document_count }} documents from {{ earliest_year }} to {{ latest_year }}",
                'category': 'experiment_description',
                'variables': {'term_text': 'string', 'document_count': 'int', 'earliest_year': 'int', 'latest_year': 'int'},
                'supports_llm_enhancement': True,
                'llm_enhancement_prompt': '''Enhance this temporal evolution description with insights about potential semantic shifts or contextual changes to expect during this time period.

Experiment metadata:
- Term: {{ term_text }}
- Document count: {{ document_count }}
- Time range: {{ earliest_year }} to {{ latest_year }}

Current description: {{ template_output }}

Enhanced description:'''
            },
            {
                'template_key': 'experiment_description_domain_comparison',
                'template_text': "Comparing usage of term '{{ term_text }}' across {{ domain_count }} domains: {{ domain_list }}",
                'category': 'experiment_description',
                'variables': {'term_text': 'string', 'domain_count': 'int', 'domain_list': 'string'},
                'supports_llm_enhancement': True,
                'llm_enhancement_prompt': '''Enhance this domain comparison description by highlighting potential differences in how the term might be understood across these domains.

Experiment metadata:
- Term: {{ term_text }}
- Domain count: {{ domain_count }}
- Domains: {{ domain_list }}

Current description: {{ template_output }}

Enhanced description:'''
            },
            {
                'template_key': 'analysis_summary',
                'template_text': "Processed {{ segment_count }} segments, generated {{ embedding_count }} embeddings using {{ model_name }}",
                'category': 'analysis_summary',
                'variables': {'segment_count': 'int', 'embedding_count': 'int', 'model_name': 'string'},
                'supports_llm_enhancement': False,
                'llm_enhancement_prompt': None
            }
        ]

        for template_data in defaults:
            existing = cls.query.filter_by(template_key=template_data['template_key']).first()
            if not existing:
                template = cls(**template_data)
                db.session.add(template)

        db.session.commit()

    def validate_template(self) -> bool:
        """
        Validate template syntax.

        Returns:
            True if template is valid

        Raises:
            TemplateSyntaxError: If syntax is invalid
        """
        try:
            Template(self.template_text)
            return True
        except TemplateSyntaxError as e:
            raise TemplateSyntaxError(f"Invalid template syntax: {e}")

    def __repr__(self):
        return f'<PromptTemplate {self.template_key} ({self.category})>'
