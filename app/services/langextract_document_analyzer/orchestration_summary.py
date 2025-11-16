"""
Orchestration Summary Module

Generates summary information for orchestrating LLM decision making.
Provides document characteristics and tool routing guidance.
"""

import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class OrchestrationSummarizer:
    """Generate orchestration guidance from analysis results"""

    @staticmethod
    def generate_summary(analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate summary for orchestrating LLM decision making

        Args:
            analysis_result: Complete analysis results from extraction

        Returns:
            Orchestration guidance with document characteristics and routing info
        """
        return {
            'document_characteristics': {
                'complexity': analysis_result.get('analytical_complexity', 'medium'),
                'domain_primary': OrchestrationSummarizer._get_primary_domain(analysis_result),
                'temporal_focus': OrchestrationSummarizer._get_temporal_focus(analysis_result),
                'concept_density': len(analysis_result.get('key_concepts', [])),
                'processing_requirements': analysis_result.get('processing_priority', 'standard')
            },
            'tool_routing_guidance': {
                'recommended_tools': analysis_result.get('recommended_tools', []),
                'confidence': analysis_result.get('extraction_confidence', 0.5),
                'processing_order': OrchestrationSummarizer._determine_processing_order(analysis_result),
                'fallback_options': ['spacy_nlp', 'basic_embeddings']
            },
            'orchestration_context': {
                'extraction_timestamp': analysis_result.get('extraction_timestamp'),
                'character_level_tracking': analysis_result.get('character_positions', False),
                'ready_for_synthesis': True
            }
        }

    @staticmethod
    def _get_primary_domain(analysis_result: Dict[str, Any]) -> str:
        """
        Determine primary domain from analysis

        Args:
            analysis_result: Analysis results

        Returns:
            Primary domain identifier
        """
        domains = analysis_result.get('domain_indicators', [])
        if not domains:
            return 'general'

        # Get highest confidence domain
        if isinstance(domains[0], dict) and 'domain' in domains[0]:
            return domains[0]['domain']

        return 'general'

    @staticmethod
    def _get_temporal_focus(analysis_result: Dict[str, Any]) -> str:
        """
        Determine temporal focus from analysis

        Args:
            analysis_result: Analysis results

        Returns:
            Temporal focus ('historical', 'early_modern', 'modern', 'contemporary')
        """
        markers = analysis_result.get('temporal_markers', [])
        if not markers:
            return 'contemporary'

        # Analyze temporal patterns
        years = []
        for marker in markers:
            if isinstance(marker, dict) and 'marker' in marker:
                marker_text = str(marker['marker'])
                if marker_text.isdigit() and len(marker_text) == 4:
                    year = int(marker_text)
                    if 1000 <= year <= 2025:
                        years.append(year)

        if years:
            avg_year = sum(years) / len(years)
            if avg_year < 1900:
                return 'historical'
            elif avg_year < 1950:
                return 'early_modern'
            elif avg_year < 2000:
                return 'modern'
            else:
                return 'contemporary'

        return 'contemporary'

    @staticmethod
    def _determine_processing_order(analysis_result: Dict[str, Any]) -> List[str]:
        """
        Determine optimal processing order for tools

        Args:
            analysis_result: Analysis results

        Returns:
            Ordered list of tools to execute
        """
        tools = analysis_result.get('recommended_tools', [])

        # Processing order logic
        ordered = []

        # 1. Basic NLP first
        if 'spacy_nlp' in tools:
            ordered.append('spacy_nlp')
        if 'basic_tokenization' in tools:
            ordered.append('basic_tokenization')

        # 2. Domain-specific tools
        domain_tools = [t for t in tools if any(d in t for d in ['historical', 'technical', 'legal', 'philosophical'])]
        ordered.extend(domain_tools)

        # 3. Embedding and analysis tools
        analysis_tools = [t for t in tools if any(a in t for a in ['embedding', 'temporal', 'analysis'])]
        ordered.extend(analysis_tools)

        # 4. Remaining tools
        remaining = [t for t in tools if t not in ordered]
        ordered.extend(remaining)

        return ordered
