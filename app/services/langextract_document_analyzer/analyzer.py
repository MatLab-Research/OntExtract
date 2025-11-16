"""
Main Document Analyzer Coordinator

Coordinates the LangExtract document analysis pipeline, delegating to
specialized modules for each step of the process.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from .text_preprocessing import TextPreprocessor
from .extraction import LangExtractExtractor
from .result_processing import ResultProcessor
from .orchestration_summary import OrchestrationSummarizer
from .fallback import FallbackExtractor

logger = logging.getLogger(__name__)


class LangExtractDocumentAnalyzer:
    """
    Stage 1: LangExtract structured extraction service

    Coordinates document analysis pipeline:
    1. Text preprocessing
    2. LangExtract structured extraction
    3. Result processing and validation
    4. Orchestration summary generation

    Delegates to specialized modules for better maintainability and testability.
    """

    def __init__(self, provider: Optional[str] = None, model_id: Optional[str] = None):
        """
        Initialize analyzer with configurable model selection

        Args:
            provider: LLM provider ('gemini', 'anthropic', 'openai'). Defaults to config.
            model_id: Specific model ID. Defaults to config.
        """
        self.preprocessor = TextPreprocessor()
        self.extractor = LangExtractExtractor(provider=provider, model_id=model_id)
        self.result_processor = ResultProcessor()
        self.summarizer = OrchestrationSummarizer()
        self.fallback = FallbackExtractor()

    def analyze_document(self, text: str, document_metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Perform structured extraction from document text

        Args:
            text: Document text to analyze
            document_metadata: Optional metadata for context

        Returns:
            Structured analysis with character positions
        """
        # Validate text
        if not self.preprocessor.validate_text(text):
            raise ValueError("Document text too short for meaningful analysis")

        # Clean text for processing
        clean_text, was_truncated = self.preprocessor.clean_text(text)

        # Perform structured extraction
        extraction_result = self.extractor.extract_structured_information(clean_text)

        # Process results or use fallback
        if extraction_result.get('success'):
            structured_extractions = self.result_processor.process_extraction_results(
                extraction_result['annotated_doc'],
                clean_text
            )
            extraction_method = extraction_result['extraction_method']
        else:
            logger.warning("LangExtract extraction failed, using fallback")
            structured_extractions = self.fallback.extract_basic_information(clean_text)
            extraction_method = 'fallback_pattern_matching'

        # Add metadata and processing info
        result = {
            'extraction_timestamp': datetime.utcnow().isoformat(),
            'text_length': len(clean_text),
            'text_truncated': was_truncated,
            'extraction_method': extraction_method,
            'model_used': extraction_result.get('model_used'),
            'structured_extractions': structured_extractions,
            'orchestration_ready': True
        }

        return result

    def get_orchestration_summary(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate summary for orchestrating LLM decision making

        Args:
            analysis_result: Complete analysis result from analyze_document()

        Returns:
            Orchestration guidance
        """
        structured_extractions = analysis_result.get('structured_extractions', {})
        return self.summarizer.generate_summary(structured_extractions)

    def extract_entities(self, text: str) -> Dict[str, Any]:
        """
        Specialized entity extraction with position tracking

        Args:
            text: Document text

        Returns:
            Entity extraction results
        """
        # Clean text
        clean_text, _ = self.preprocessor.clean_text(text)

        # Attempt LangExtract entity extraction
        extraction_result = self.extractor.extract_entities_with_positions(clean_text)

        # Use fallback if needed
        if not extraction_result.get('success'):
            logger.warning("LangExtract entity extraction failed, using fallback")
            extraction_result = self.fallback.extract_entities(clean_text)

        return extraction_result
