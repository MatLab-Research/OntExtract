"""
Fallback Extraction Module

Provides pattern-based fallback extraction when LangExtract fails.
Uses regex patterns to extract basic information.
"""

import re
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class FallbackExtractor:
    """Simple pattern-based extraction as fallback when LangExtract fails"""

    @staticmethod
    def extract_basic_information(text: str) -> Dict[str, Any]:
        """
        Simple fallback extraction using pattern matching

        Args:
            text: Document text to analyze

        Returns:
            Basic extraction results with reduced confidence scores
        """
        # Extract potential dates
        date_pattern = r'\b(?:1[0-9]{3}|20[0-2][0-9])\b'
        dates = re.findall(date_pattern, text)

        # Extract capitalized terms (potential concepts)
        concept_pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b'
        concepts = list(set(re.findall(concept_pattern, text)))[:10]  # Limit to 10

        return {
            'key_concepts': [
                {'term': c, 'position': [0, 0], 'confidence': 0.3}
                for c in concepts
            ],
            'temporal_markers': [
                {'marker': d, 'position': [0, 0], 'period': 'unknown'}
                for d in dates
            ],
            'domain_indicators': [
                {'domain': 'general', 'confidence': 0.3, 'evidence': ['fallback_analysis']}
            ],
            'document_structure': [],
            'analytical_complexity': 'medium',
            'recommended_tools': ['spacy_nlp', 'basic_tokenization'],
            'processing_priority': 'standard',
            'character_positions': False,
            'extraction_confidence': 0.3,
            'extraction_method': 'fallback_pattern_matching'
        }

    @staticmethod
    def extract_entities(text: str) -> Dict[str, Any]:
        """
        Fallback entity extraction using pattern matching

        Args:
            text: Document text

        Returns:
            Entity extraction results with position information
        """
        extracted_entities = []
        extracted_concepts = []

        # Pattern-based entity extraction
        patterns = {
            'PERSON': r'\b(?:Dr|Prof|Mr|Ms|Mrs)\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b',
            'ORG': r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Inc|Corp|LLC|Ltd|Company|University|Institute|Foundation)\b',
            'DATE': r'\b(?:1[0-9]{3}|20[0-2][0-9])\b',
            'ACRONYM': r'\b[A-Z]{2,}\b'
        }

        for entity_type, pattern in patterns.items():
            matches = re.finditer(pattern, text)
            for match in matches:
                entity_text = match.group().strip()
                start_pos = match.start()
                end_pos = match.end()

                # Create context
                context_start = max(0, start_pos - 30)
                context_end = min(len(text), end_pos + 30)
                context = text[context_start:context_end].strip()

                extracted_entities.append({
                    'entity': entity_text,
                    'type': entity_type,
                    'position': [start_pos, end_pos],
                    'confidence': 0.60,
                    'context': context
                })

        # Simple concept extraction (capitalized terms)
        concept_pattern = r'\b[A-Z][a-z]+(?:\s+[a-z]+)*\b'
        concept_matches = re.finditer(concept_pattern, text)
        for match in concept_matches:
            concept_text = match.group().strip()
            if len(concept_text) > 3:  # Filter short terms
                start_pos = match.start()
                end_pos = match.end()

                context_start = max(0, start_pos - 30)
                context_end = min(len(text), end_pos + 30)
                context = text[context_start:context_end].strip()

                extracted_concepts.append({
                    'term': concept_text,
                    'position': [start_pos, end_pos],
                    'confidence': 0.50,
                    'context': context
                })

        # Create mock extraction structure to match expected format
        mock_extraction = type('Extraction', (), {
            'attributes': {
                'named_entities': extracted_entities,
                'key_concepts': extracted_concepts[:10]  # Limit concepts
            }
        })()

        return {
            'success': True,
            'structured_extractions': [mock_extraction],
            'extraction_method': 'fallback_pattern_matching',
            'character_positions': True
        }
