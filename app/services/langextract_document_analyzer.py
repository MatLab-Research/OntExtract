"""
LangExtract Document Analyzer - Stage 1 of Two-Stage Architecture

Performs structured extraction of definitions, temporal markers, and domain indicators
from documents with character-level position tracking for PROV-O traceability.
"""

import os
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import langextract as lx
from langextract import data

logger = logging.getLogger(__name__)


class LangExtractDocumentAnalyzer:
    """
    Stage 1: LangExtract structured extraction service
    
    Extracts structured information that feeds into the orchestrating LLM:
    - Definitions and key concepts
    - Temporal markers and period indicators  
    - Domain indicators and technical terminology
    - Character-level position information for traceability
    """
    
    def __init__(self):
        """Initialize with API key detection"""
        self.api_key = os.environ.get('GOOGLE_GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("GOOGLE_GEMINI_API_KEY required for LangExtract")
        
        self.model_id = "gemini-1.5-flash"  # Stable model with good paid quotas
        self.language_model_type = lx.inference.GeminiLanguageModel
    
    def analyze_document(self, text: str, document_metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Perform structured extraction from document text
        
        Args:
            text: Document text to analyze
            document_metadata: Optional metadata for context
            
        Returns:
            Structured analysis with character positions
        """
        if not text or len(text.strip()) < 10:
            raise ValueError("Document text too short for meaningful analysis")
        
        # Clean text for processing
        clean_text = self._clean_text(text)
        
        # Perform structured extraction
        extraction_result = self._extract_structured_information(clean_text)
        
        # Add metadata and processing info
        result = {
            'extraction_timestamp': datetime.utcnow().isoformat(),
            'text_length': len(clean_text),
            'extraction_method': 'langextract_gemini',
            'structured_extractions': extraction_result,
            'orchestration_ready': True
        }
        
        return result
    
    def _clean_text(self, text: str) -> str:
        """Clean text for LangExtract processing"""
        # Remove null characters that break processing
        text = text.replace('\x00', '')
        
        # Limit to reasonable length for API processing
        if len(text) > 50000:
            text = text[:50000]
            logger.warning("Text truncated to 50,000 characters for processing")
        
        return text
    
    def _extract_structured_information(self, text: str) -> Dict[str, Any]:
        """
        Use LangExtract to extract structured information for orchestration
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
            # Perform LangExtract extraction
            # Add timeout and reduce complexity to prevent hanging
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
                extraction_passes=1,  # Reduce from 2 to 1 to prevent timeout
                max_char_buffer=2000,  # Reduce buffer size
                batch_length=2,  # Reduce batch size
                max_workers=1  # Single worker to avoid rate limiting
            )
            
            # Process results into structured format
            return self._process_extraction_results(annotated_doc, text)
            
        except Exception as e:
            logger.error(f"LangExtract processing failed: {e}")
            return self._fallback_extraction(text)
    
    def _process_extraction_results(self, annotated_doc: Any, original_text: str) -> Dict[str, Any]:
        """Process LangExtract results into orchestration-ready format"""
        
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
        result = self._validate_and_enrich_results(result, original_text)
        
        return result
    
    def _validate_and_enrich_results(self, result: Dict[str, Any], original_text: str) -> Dict[str, Any]:
        """Validate extraction results and add analytical enrichments"""
        
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
            'expected_processing_time': self._estimate_processing_time(result)
        }
        
        return result
    
    def _estimate_processing_time(self, analysis_result: Dict[str, Any]) -> str:
        """Estimate processing time based on analysis complexity"""
        
        tool_count = len(analysis_result.get('recommended_tools', []))
        complexity = analysis_result.get('analytical_complexity', 'medium')
        
        if complexity == 'high' or tool_count > 6:
            return 'extended'  # 2-5 minutes
        elif complexity == 'medium' or tool_count > 3:
            return 'standard'  # 30-120 seconds
        else:
            return 'fast'  # 10-30 seconds
    
    def _fallback_extraction(self, text: str) -> Dict[str, Any]:
        """Simple fallback when LangExtract fails"""
        
        # Basic pattern matching for fallback
        import re
        
        # Extract potential dates
        date_pattern = r'\b(?:1[0-9]{3}|20[0-2][0-9])\b'
        dates = re.findall(date_pattern, text)
        
        # Extract capitalized terms (potential concepts)
        concept_pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b'
        concepts = list(set(re.findall(concept_pattern, text)))[:10]
        
        return {
            'key_concepts': [{'term': c, 'position': [0, 0], 'confidence': 0.3} for c in concepts],
            'temporal_markers': [{'marker': d, 'position': [0, 0], 'period': 'unknown'} for d in dates],
            'domain_indicators': [{'domain': 'general', 'confidence': 0.3, 'evidence': ['fallback_analysis']}],
            'document_structure': [],
            'analytical_complexity': 'medium',
            'recommended_tools': ['spacy_nlp', 'basic_tokenization'],
            'processing_priority': 'standard',
            'character_positions': False,
            'extraction_confidence': 0.3,
            'extraction_method': 'fallback_pattern_matching'
        }
    
    def get_orchestration_summary(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate summary for orchestrating LLM decision making
        """
        
        return {
            'document_characteristics': {
                'complexity': analysis_result.get('analytical_complexity', 'medium'),
                'domain_primary': self._get_primary_domain(analysis_result),
                'temporal_focus': self._get_temporal_focus(analysis_result),
                'concept_density': len(analysis_result.get('key_concepts', [])),
                'processing_requirements': analysis_result.get('processing_priority', 'standard')
            },
            'tool_routing_guidance': {
                'recommended_tools': analysis_result.get('recommended_tools', []),
                'confidence': analysis_result.get('extraction_confidence', 0.5),
                'processing_order': self._determine_processing_order(analysis_result),
                'fallback_options': ['spacy_nlp', 'basic_embeddings']
            },
            'orchestration_context': {
                'extraction_timestamp': analysis_result.get('extraction_timestamp'),
                'character_level_tracking': analysis_result.get('character_positions', False),
                'ready_for_synthesis': True
            }
        }
    
    def _get_primary_domain(self, analysis_result: Dict[str, Any]) -> str:
        """Determine primary domain from analysis"""
        domains = analysis_result.get('domain_indicators', [])
        if not domains:
            return 'general'
        
        # Get highest confidence domain
        if isinstance(domains[0], dict) and 'domain' in domains[0]:
            return domains[0]['domain']
        
        return 'general'
    
    def _get_temporal_focus(self, analysis_result: Dict[str, Any]) -> str:
        """Determine temporal focus from analysis"""
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
    
    def _determine_processing_order(self, analysis_result: Dict[str, Any]) -> List[str]:
        """Determine optimal processing order for tools"""
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

    def _extract_entities_with_positions(self, text: str) -> Dict[str, Any]:
        """
        Specialized entity extraction using LangExtract with character-level positioning

        Args:
            text: Document text to analyze for entities

        Returns:
            Structured entity extraction results
        """
        clean_text = self._clean_text(text)

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
                text=clean_text,
                model=language_model
            )

            return {
                'success': True,
                'structured_extractions': extractions,
                'extraction_method': 'langextract_entity_focused',
                'character_positions': True
            }

        except Exception as e:
            logger.error(f"LangExtract entity extraction failed: {e}")
            # Return fallback entity extraction
            return self._fallback_entity_extraction(clean_text)

    def _fallback_entity_extraction(self, text: str) -> Dict[str, Any]:
        """Fallback entity extraction using pattern matching when LangExtract fails"""
        import re

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