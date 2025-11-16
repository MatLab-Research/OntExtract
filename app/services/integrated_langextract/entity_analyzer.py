"""
Entity Analyzer

Specialized entity extraction using LangExtract + Gemini integration.
"""

import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class EntityAnalyzer:
    """Analyzes documents for entity extraction"""

    def analyze_document_for_entities(self, document_analyzer, text: str,
                                     document_metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Specialized entity extraction using LangExtract + Gemini integration

        Args:
            document_analyzer: LangExtractDocumentAnalyzer instance
            text: Document text to analyze for entities
            document_metadata: Optional metadata for context

        Returns:
            Structured entity extraction results with character positions and confidence scores
        """
        if not text or len(text.strip()) < 10:
            raise ValueError("Document text too short for meaningful entity analysis")

        try:
            # Use document analyzer for structured entity extraction
            analysis_result = document_analyzer._extract_entities_with_positions(text)

            # Extract entities and concepts from the analysis
            extracted_entities = []
            extracted_concepts = []

            if 'structured_extractions' in analysis_result:
                extractions = analysis_result['structured_extractions']

                # Process named entities
                for extraction in extractions:
                    if hasattr(extraction, 'attributes') and extraction.attributes:
                        attrs = extraction.attributes

                        # Extract named entities
                        if 'named_entities' in attrs:
                            for entity in attrs['named_entities']:
                                extracted_entities.append({
                                    'text': entity.get('entity', ''),
                                    'type': entity.get('type', 'ENTITY'),
                                    'confidence': entity.get('confidence', 0.85),
                                    'context': entity.get('context', ''),
                                    'start_pos': entity.get('position', [0, 0])[0],
                                    'end_pos': entity.get('position', [0, 0])[1]
                                })

                        # Extract key concepts
                        if 'key_concepts' in attrs:
                            for concept in attrs['key_concepts']:
                                extracted_concepts.append({
                                    'term': concept.get('term', ''),
                                    'confidence': concept.get('confidence', 0.80),
                                    'context': concept.get('context', ''),
                                    'position': concept.get('position', [0, 0])
                                })

            return {
                'success': True,
                'entities': extracted_entities,
                'key_concepts': extracted_concepts,
                'extraction_method': 'langextract_gemini',
                'total_entities': len(extracted_entities),
                'total_concepts': len(extracted_concepts),
                'character_level_positioning': True,
                'metadata': document_metadata or {}
            }

        except Exception as e:
            logger.error(f"LangExtract entity extraction failed: {e}")
            raise Exception(f"Entity extraction failed: {e}")
