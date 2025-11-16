"""
Segmentation Analyzer

Provides LangExtract-powered segmentation recommendations and segment extraction.
"""

import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class SegmentationAnalyzer:
    """Analyzes documents for segmentation recommendations"""

    def get_segmentation_recommendations(self, document_analyzer, document_text: str) -> Dict[str, Any]:
        """
        Get LangExtract-powered segmentation recommendations

        Args:
            document_analyzer: LangExtractDocumentAnalyzer instance
            document_text: Text to analyze for segmentation

        Returns:
            Segmentation recommendations with character positions
        """
        try:
            # Use LangExtract to analyze document structure
            analysis = document_analyzer.analyze_document(
                text=document_text,
                document_metadata={'purpose': 'segmentation_analysis'}
            )

            # Extract segmentation guidance from structured analysis
            extractions = analysis.get('structured_extractions', {})

            recommendations = {
                'method': 'langextract_semantic_segmentation',
                'confidence': extractions.get('extraction_confidence', 0.5),
                'character_level_positions': True,

                # Structural segments based on document analysis
                'structural_segments': self.extract_structural_segments(extractions),

                # Semantic segments based on concept clustering
                'semantic_segments': self.extract_semantic_segments(extractions),

                # Temporal segments based on temporal markers
                'temporal_segments': self.extract_temporal_segments(extractions),

                # Recommended segmentation strategy
                'recommended_strategy': self.recommend_segmentation_strategy(extractions),

                # Integration with existing methods
                'integration_suggestions': {
                    'combine_with': ['paragraph', 'semantic'],
                    'avoid_combining_with': ['sentence'],  # Too granular for LangExtract
                    'optimal_hybrid_approach': 'langextract_structural + semantic_refinement'
                }
            }

            return recommendations

        except Exception as e:
            logger.error(f"Failed to get LangExtract segmentation recommendations: {e}")
            raise

    def extract_structural_segments(self, extractions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract structural segments from LangExtract analysis"""
        segments = []
        structure_info = extractions.get('document_structure', [])

        for item in structure_info:
            if isinstance(item, dict) and 'position' in item:
                segments.append({
                    'type': 'structural',
                    'element': item.get('element', 'section'),
                    'start_pos': item.get('position', [0, 0])[0],
                    'end_pos': item.get('position', [0, 0])[1],
                    'confidence': item.get('confidence', 0.7),
                    'content_preview': item.get('content', '')[:100]
                })

        return segments

    def extract_semantic_segments(self, extractions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract semantic segments based on concept clustering"""
        segments = []
        concepts = extractions.get('key_concepts', [])

        # Group concepts by position to create semantic boundaries
        concept_positions = []
        for concept in concepts:
            if isinstance(concept, dict) and 'position' in concept:
                concept_positions.append({
                    'concept': concept.get('term', ''),
                    'start': concept.get('position', [0, 0])[0],
                    'end': concept.get('position', [0, 0])[1],
                    'confidence': concept.get('confidence', 0.7)
                })

        # Sort by position and create semantic segments
        concept_positions.sort(key=lambda x: x['start'])

        current_segment_start = 0
        for i, concept in enumerate(concept_positions):
            if i > 0:
                # Create segment between concepts
                segments.append({
                    'type': 'semantic',
                    'start_pos': current_segment_start,
                    'end_pos': concept['start'],
                    'primary_concepts': [concept_positions[i-1]['concept']],
                    'confidence': (concept_positions[i-1]['confidence'] + concept['confidence']) / 2
                })
            current_segment_start = concept['end']

        return segments

    def extract_temporal_segments(self, extractions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract temporal segments based on temporal markers"""
        segments = []
        temporal_markers = extractions.get('temporal_markers', [])

        for marker in temporal_markers:
            if isinstance(marker, dict) and 'position' in marker:
                segments.append({
                    'type': 'temporal',
                    'marker': marker.get('marker', ''),
                    'period': marker.get('period', 'unknown'),
                    'start_pos': marker.get('position', [0, 0])[0],
                    'end_pos': marker.get('position', [0, 0])[1],
                    'temporal_context': marker.get('context', ''),
                    'confidence': 0.8  # Temporal markers are usually reliable
                })

        return segments

    def recommend_segmentation_strategy(self, extractions: Dict[str, Any]) -> Dict[str, str]:
        """Recommend optimal segmentation strategy based on analysis"""
        concept_count = len(extractions.get('key_concepts', []))
        temporal_count = len(extractions.get('temporal_markers', []))
        structure_count = len(extractions.get('document_structure', []))
        complexity = extractions.get('analytical_complexity', 'medium')

        if temporal_count > 3:
            return {
                'primary': 'temporal_segmentation',
                'rationale': 'High temporal marker density suggests chronological organization',
                'secondary': 'semantic_refinement'
            }
        elif concept_count > 10:
            return {
                'primary': 'semantic_segmentation',
                'rationale': 'High concept density suggests thematic organization',
                'secondary': 'structural_boundaries'
            }
        elif structure_count > 0:
            return {
                'primary': 'structural_segmentation',
                'rationale': 'Clear document structure identified',
                'secondary': 'semantic_enhancement'
            }
        else:
            return {
                'primary': 'hybrid_segmentation',
                'rationale': 'Mixed content requires combined approach',
                'secondary': 'paragraph_fallback'
            }
