"""
Result Processing Module

Processes LangExtract extraction results into orchestration-ready format,
validates data, and enriches with analytical recommendations.
"""

import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class ResultProcessor:
    """Process and validate LangExtract extraction results"""

    @staticmethod
    def process_extraction_results(annotated_doc: Any, original_text: str) -> Dict[str, Any]:
        """
        Process LangExtract results into orchestration-ready format

        Args:
            annotated_doc: LangExtract annotated document
            original_text: Original input text

        Returns:
            Structured results with character positions and confidence scores
        """
        result = {
            'key_concepts': [],
            'temporal_markers': [],
            'domain_indicators': [],
            'document_structure': [],
            'analytical_complexity': 'medium',
            'recommended_tools': [],
            'processing_priority': 'standard',
            'character_positions': True,
            'extraction_confidence': 0.0
        }

        total_extractions = 0
        confidence_sum = 0.0

        if annotated_doc and hasattr(annotated_doc, 'extractions'):
            for extraction in annotated_doc.extractions:
                # Handle different LangExtract data structure formats
                extraction_data = None
                if hasattr(extraction, 'data') and extraction.data:
                    extraction_data = extraction.data
                elif hasattr(extraction, 'attributes') and extraction.attributes:
                    extraction_data = extraction.attributes
                elif hasattr(extraction, 'extraction_text'):
                    # Try to parse JSON from extraction text
                    try:
                        import json
                        extraction_data = json.loads(extraction.extraction_text)
                    except:
                        extraction_data = {'raw_text': extraction.extraction_text}

                if extraction_data:
                    # Merge structured data
                    for key, value in extraction_data.items():
                        if key in result and value:
                            if isinstance(result[key], list) and isinstance(value, list):
                                result[key].extend(value)
                            elif result[key] is None or (isinstance(result[key], str) and not result[key]):
                                result[key] = value

                    # Track extraction quality
                    total_extractions += 1
                    if hasattr(extraction, 'confidence'):
                        confidence_sum += extraction.confidence

        # Calculate overall confidence
        if total_extractions > 0:
            result['extraction_confidence'] = confidence_sum / total_extractions

        # Validate and enrich results
        result = ResultProcessor.validate_and_enrich_results(result, original_text)

        return result

    @staticmethod
    def validate_and_enrich_results(result: Dict[str, Any], original_text: str) -> Dict[str, Any]:
        """
        Validate extraction results and add analytical enrichments

        Args:
            result: Initial extraction results
            original_text: Original document text

        Returns:
            Validated and enriched results
        """
        # Ensure we have recommended tools based on analysis
        if not result.get('recommended_tools'):
            tools = ['spacy_nlp', 'basic_tokenization']

            # Add tools based on domain indicators
            domains = result.get('domain_indicators', [])
            for domain_info in domains:
                if isinstance(domain_info, dict):
                    domain = domain_info.get('domain', '')
                    if 'historical' in domain or 'philosophy' in domain:
                        tools.extend(['historical_nlp', 'period_aware_embeddings'])
                    elif 'technical' in domain or 'scientific' in domain:
                        tools.extend(['technical_tokenizer', 'domain_embeddings'])
                    elif 'legal' in domain:
                        tools.extend(['legal_nlp', 'case_analysis'])

            # Add tools based on temporal markers
            if result.get('temporal_markers'):
                tools.append('temporal_analysis')
                if any('century' in str(marker) for marker in result['temporal_markers']):
                    tools.append('historical_contextualization')

            result['recommended_tools'] = list(set(tools))

        # Set processing priority
        complexity = result.get('analytical_complexity', 'medium')
        temporal_count = len(result.get('temporal_markers', []))
        concept_count = len(result.get('key_concepts', []))

        if complexity == 'high' or temporal_count > 5 or concept_count > 10:
            result['processing_priority'] = 'academic_high'
        elif temporal_count > 0 or concept_count > 5:
            result['processing_priority'] = 'academic_standard'
        else:
            result['processing_priority'] = 'standard'

        # Add orchestration metadata
        result['orchestration_metadata'] = {
            'stage': 'langextract_completed',
            'ready_for_orchestration': True,
            'tool_routing_confidence': result.get('extraction_confidence', 0.5),
            'expected_processing_time': ResultProcessor.estimate_processing_time(result)
        }

        return result

    @staticmethod
    def estimate_processing_time(analysis_result: Dict[str, Any]) -> str:
        """
        Estimate processing time based on analysis complexity

        Args:
            analysis_result: Analyzed document results

        Returns:
            Processing time estimate ('fast', 'standard', 'extended')
        """
        tool_count = len(analysis_result.get('recommended_tools', []))
        complexity = analysis_result.get('analytical_complexity', 'medium')

        if complexity == 'high' or tool_count > 6:
            return 'extended'  # 2-5 minutes
        elif complexity == 'medium' or tool_count > 3:
            return 'standard'  # 30-120 seconds
        else:
            return 'fast'  # 10-30 seconds
