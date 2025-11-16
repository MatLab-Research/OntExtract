"""
Core Extraction Module

Handles LangExtract structured extraction with configurable model selection.
Uses task-specific models from application config for optimal performance/cost.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
import langextract as lx
from langextract import data
from config.llm_config import get_llm_config, LLMTaskType

logger = logging.getLogger(__name__)


class LangExtractExtractor:
    """
    Core LangExtract structured extraction service

    Extracts structured information using configurable LLM models.
    Supports multiple providers (Gemini, Claude, GPT) via centralized config.
    """

    def __init__(self, provider: Optional[str] = None, model_id: Optional[str] = None):
        """
        Initialize extractor with model configuration

        Args:
            provider: LLM provider ('gemini', 'anthropic', 'openai').
                     Defaults to extraction task config from LLMConfigManager.
            model_id: Specific model ID. Defaults to extraction task config from LLMConfigManager.
        """
        # Get configuration from centralized LLM config manager
        llm_config = get_llm_config()

        if provider is None or model_id is None:
            # Use task-specific configuration for extraction
            extraction_config = llm_config.get_extraction_config()
            self.provider = provider or extraction_config['provider']
            self.model_id = model_id or extraction_config['model']
            self.api_key = extraction_config['api_key']
        else:
            # Use provided values and get API key from config manager
            self.provider = provider
            self.model_id = model_id
            self.api_key = llm_config.get_api_key_for_provider(provider)

        # Configure provider-specific settings
        if self.provider == 'gemini' or self.provider == 'google':
            self.language_model_type = lx.inference.GeminiLanguageModel
        elif self.provider == 'anthropic' or self.provider == 'claude':
            # LangExtract may need provider adapter for Claude
            raise NotImplementedError("Claude provider not yet supported by LangExtract")
        elif self.provider == 'openai' or self.provider == 'gpt':
            # LangExtract may need provider adapter for OpenAI
            raise NotImplementedError("OpenAI provider not yet supported by LangExtract")
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

        if not self.api_key:
            raise ValueError(
                f"API key required for {self.provider} provider. "
                f"Please set the appropriate environment variable."
            )

        logger.info(f"✓ Initialized LangExtract with {self.provider} provider, model: {self.model_id}")

    def extract_structured_information(self, text: str) -> Dict[str, Any]:
        """
        Use LangExtract to extract structured information for orchestration

        Args:
            text: Cleaned document text

        Returns:
            Structured extraction results
        """
        # Define extraction schema matching section 3.1 claims
        prompt_description = """
        Extract structured information from this document to guide analytical tool selection.

        Focus on extracting:
        1. KEY_CONCEPTS: Important terms, definitions, and concepts
        2. TEMPORAL_MARKERS: Dates, periods, historical references, time indicators
        3. DOMAIN_INDICATORS: Subject area, technical terminology, field-specific language
        4. DOCUMENT_STRUCTURE: Sections, headings, organizational elements
        5. ANALYTICAL_COMPLEXITY: Indicators of complexity level and processing requirements

        For each extraction, maintain character-level position information.
        Provide confidence scores for analytical tool routing decisions.
        """

        # Provide examples for consistent extraction
        examples = [
            data.ExampleData(
                text="""In 1957, Anscombe's work on intentionality established philosophical foundations
                for agency theory. The concept of moral responsibility evolved significantly during
                the post-war period, requiring sophisticated analysis of ethical frameworks.""",
                extractions=[
                    data.Extraction(
                        extraction_class="analytical_guidance",
                        extraction_text="structured_analysis",
                        attributes={
                            "key_concepts": [
                                {"term": "intentionality", "position": [15, 29], "confidence": 0.9},
                                {"term": "agency theory", "position": [64, 76], "confidence": 0.85}
                            ],
                            "temporal_markers": [
                                {"marker": "1957", "position": [3, 7], "period": "mid_20th_century"},
                                {"marker": "post-war period", "position": [155, 170], "period": "1945_1960"}
                            ],
                            "domain_indicators": [
                                {"domain": "philosophy", "confidence": 0.9, "evidence": ["intentionality", "moral responsibility"]},
                                {"domain": "ethics", "confidence": 0.85, "evidence": ["ethical frameworks"]}
                            ],
                            "analytical_complexity": "high",
                            "recommended_tools": ["historical_nlp", "philosophical_terminology", "temporal_analysis"],
                            "processing_priority": "academic_historical"
                        }
                    )
                ]
            )
        ]

        try:
            # Perform LangExtract extraction with timeout and optimized settings
            annotated_doc = lx.extract(
                text_or_documents=text,
                prompt_description=prompt_description,
                examples=examples,
                model_id=self.model_id,
                api_key=self.api_key,
                language_model_type=self.language_model_type,
                format_type=data.FormatType.JSON,
                temperature=0.2,  # Low temperature for consistent analysis
                fence_output=False,
                use_schema_constraints=True,
                extraction_passes=1,  # Single pass to prevent timeout
                max_char_buffer=2000,  # Optimized buffer size
                batch_length=2,  # Reduced batch size
                max_workers=1  # Single worker to avoid rate limiting
            )

            return {
                'success': True,
                'annotated_doc': annotated_doc,
                'extraction_method': f'langextract_{self.provider}',
                'model_used': self.model_id
            }

        except Exception as e:
            logger.error(f"LangExtract processing failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'extraction_method': f'langextract_{self.provider}_failed'
            }

    def extract_entities_with_positions(self, text: str) -> Dict[str, Any]:
        """
        Specialized entity extraction using LangExtract with character-level positioning

        Args:
            text: Document text to analyze for entities

        Returns:
            Structured entity extraction results
        """
        # Define entity-focused extraction schema
        prompt_description = """
        Extract named entities and key concepts from this document with precise character positions.

        Focus on extracting:
        1. NAMED_ENTITIES: People, organizations, locations, dates, technical terms
        2. KEY_CONCEPTS: Important domain-specific terms and concepts
        3. TECHNICAL_TERMS: Specialized vocabulary and jargon

        For each entity/concept:
        - Provide exact character positions [start, end]
        - Assign entity type (PERSON, ORG, LOCATION, DATE, CONCEPT, TECHNICAL)
        - Include confidence score (0.0-1.0)
        - Provide surrounding context (±30 characters)
        """

        # Entity extraction examples
        examples = [
            data.ExampleData(
                text="""In 1957, Anscombe developed her theory of intentionality at Oxford University.
                The concept revolutionized moral philosophy and influenced agency theory.""",
                extractions=[
                    data.Extraction(
                        extraction_class="entity_extraction",
                        extraction_text="entities_and_concepts",
                        attributes={
                            "named_entities": [
                                {"entity": "Anscombe", "type": "PERSON", "position": [8, 16], "confidence": 0.95, "context": "In 1957, Anscombe developed"},
                                {"entity": "1957", "type": "DATE", "position": [3, 7], "confidence": 0.99, "context": "In 1957, Anscombe developed"},
                                {"entity": "Oxford University", "type": "ORG", "position": [53, 70], "confidence": 0.90, "context": "intentionality at Oxford University. The"}
                            ],
                            "key_concepts": [
                                {"term": "intentionality", "position": [39, 52], "confidence": 0.85, "context": "theory of intentionality at Oxford"},
                                {"term": "moral philosophy", "position": [109, 125], "confidence": 0.88, "context": "revolutionized moral philosophy and influenced"},
                                {"term": "agency theory", "position": [141, 154], "confidence": 0.82, "context": "influenced agency theory."}
                            ]
                        }
                    )
                ]
            )
        ]

        try:
            # Perform LangExtract analysis
            language_model = self.language_model_type(api_key=self.api_key, model_id=self.model_id)

            extraction_schema = data.ExtractionSchema(
                [data.ExtractionType("entity_extraction", prompt_description)],
                examples=examples
            )

            extractions = extraction_schema.extract(
                text=text,
                model=language_model
            )

            return {
                'success': True,
                'structured_extractions': extractions,
                'extraction_method': f'langextract_entity_{self.provider}',
                'model_used': self.model_id,
                'character_positions': True
            }

        except Exception as e:
            logger.error(f"LangExtract entity extraction failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'extraction_method': f'langextract_entity_{self.provider}_failed'
            }
