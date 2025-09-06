"""
LLM Bridge Service for OntExtract

Connects OntExtract to the shared LLM orchestration infrastructure for 
intelligent tool selection and document analysis coordination.
"""

import os
import sys
import json
import asyncio
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

# Add shared services to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..', 'shared'))

try:
    from llm_orchestration import get_llm_orchestrator
    from llm_orchestration.core.orchestrator import OrchestratorConfig
    ORCHESTRATOR_AVAILABLE = True
except ImportError as e:
    ORCHESTRATOR_AVAILABLE = False
    import warnings
    warnings.warn(f"Shared LLM orchestration not available: {e}")

logger = logging.getLogger(__name__)


class OntExtractLLMService:
    """
    Bridge service connecting OntExtract to shared LLM orchestration.
    
    Provides intelligent tool selection, document analysis coordination,
    and temporal processing optimization using the platform's unified
    LLM orchestration system.
    """
    
    def __init__(self, enable_mcp_context: bool = True):
        """
        Initialize the bridge service.
        
        Args:
            enable_mcp_context: Whether to use MCP ontological context
        """
        self.enable_mcp_context = enable_mcp_context
        self._orchestrator = None
        
        if not ORCHESTRATOR_AVAILABLE:
            logger.warning("Shared LLM orchestration not available - using fallback mode")
    
    @property
    def orchestrator(self):
        """Lazy-load the LLM orchestrator."""
        if self._orchestrator is None and ORCHESTRATOR_AVAILABLE:
            config = OrchestratorConfig(
                enable_fallback=True,
                enable_caching=True,
                mcp_server_url=os.environ.get("ONTSERVE_MCP_URL", "http://localhost:8082")
            )
            self._orchestrator = get_llm_orchestrator(config)
            logger.info("LLM orchestrator initialized for OntExtract")
        
        return self._orchestrator
    
    async def analyze_document_for_tools(self, 
                                       document_text: str, 
                                       metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Analyze document and recommend optimal NLP processing approach.
        
        Args:
            document_text: Document content to analyze
            metadata: Document metadata (year, domain, format, etc.)
            
        Returns:
            Dictionary with recommended tools and reasoning
        """
        if not self.orchestrator:
            return self._fallback_tool_selection(document_text, metadata)
        
        metadata = metadata or {}
        year = metadata.get('year', 'unknown')
        domain = metadata.get('domain', 'general')
        format_type = metadata.get('format', 'unknown')
        
        tool_selection_prompt = f"""
        Analyze this document and recommend optimal NLP processing approach:
        
        Document Info:
        - Text sample: {document_text[:500]}...
        - Year: {year}
        - Domain: {domain}
        - Format: {format_type}
        - Length: {len(document_text)} characters
        
        Available NLP Tools:
        1. spaCy (en_core_web_trf): Modern text, NER, POS tagging, dependencies
        2. NLTK: Collocations, frequency analysis, tokenization
        3. Word2Vec: Semantic neighborhood tracking, context analysis
        4. Sentence Transformers: Local embedding generation
        5. Historical BERT: Pre-1950 texts with archaic spelling
        6. SciBERT: Scientific/technical terminology
        7. LegalBERT: Legal language patterns
        
        Consider:
        - Time period affects embedding model selection
        - Domain influences tool effectiveness
        - Text characteristics (formal, archaic, technical)
        - Processing efficiency for temporal analysis
        
        Return JSON with this exact structure:
        {{
            "primary_tools": ["tool1", "tool2"],
            "embedding_model": "model_name",
            "confidence": 0.85,
            "reasoning": "explanation of choices",
            "processing_strategy": "sequential|parallel",
            "expected_runtime": "estimate in seconds"
        }}
        """
        
        try:
            # Use world_name for MCP context if domain is specified
            world_name = domain if domain != 'general' else None
            
            response = await self.orchestrator.send_message(
                message=tool_selection_prompt,
                world_name=world_name,
                system_prompt="You are an expert in NLP tool selection for temporal semantic analysis. Always return valid JSON.",
                temperature=0.3,  # Lower temperature for consistent tool selection
                max_tokens=500
            )
            
            # Parse JSON response
            tool_selection = self._parse_tool_selection(response.content)
            tool_selection['llm_provider'] = response.provider
            tool_selection['response_time'] = getattr(response, 'processing_time', 0)
            
            logger.info(f"LLM tool selection completed: {tool_selection['primary_tools']}")
            return tool_selection
            
        except Exception as e:
            logger.error(f"LLM tool selection failed: {e}")
            return self._fallback_tool_selection(document_text, metadata)
    
    async def interpret_nlp_results(self, 
                                  nlp_results: Dict[str, Any], 
                                  original_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Use LLM to interpret raw NLP processing results.
        
        Args:
            nlp_results: Raw outputs from NLP tools
            original_context: Original document context
            
        Returns:
            Interpreted results with insights and confidence scores
        """
        if not self.orchestrator:
            return self._fallback_interpretation(nlp_results)
        
        original_context = original_context or {}
        
        interpretation_prompt = f"""
        Interpret these NLP analysis results for temporal semantic analysis:
        
        Original Context:
        {json.dumps(original_context, indent=2)}
        
        NLP Results:
        {json.dumps(nlp_results, indent=2)}
        
        Analysis Tasks:
        1. Identify key semantic features and their confidence
        2. Detect potential semantic drift indicators
        3. Assess data quality and reliability
        4. Suggest areas needing additional analysis
        5. Calculate overall confidence in results
        
        Return JSON with this structure:
        {{
            "semantic_features": ["feature1", "feature2"],
            "drift_indicators": [
                {{"type": "frequency_change", "confidence": 0.8, "evidence": "..."}}
            ],
            "data_quality": {{"score": 0.9, "issues": ["potential_issue"]}},
            "recommendations": ["next_step1", "next_step2"],
            "overall_confidence": 0.85,
            "interpretation_summary": "concise summary"
        }}
        """
        
        try:
            response = await self.orchestrator.send_message(
                message=interpretation_prompt,
                system_prompt="You are an expert in temporal semantic analysis interpretation. Always return valid JSON.",
                temperature=0.2,
                max_tokens=800
            )
            
            interpretation = self._parse_interpretation(response.content)
            interpretation['llm_provider'] = response.provider
            
            logger.info(f"NLP result interpretation completed with confidence: {interpretation.get('overall_confidence', 'unknown')}")
            return interpretation
            
        except Exception as e:
            logger.error(f"NLP result interpretation failed: {e}")
            return self._fallback_interpretation(nlp_results)
    
    async def generate_semantic_narrative(self, 
                                        analysis_results: Dict[str, Any], 
                                        term: str, 
                                        periods: List[int]) -> str:
        """
        Generate scholarly narrative from semantic analysis results.
        
        Args:
            analysis_results: Complete analysis results
            term: Term being analyzed
            periods: Time periods covered
            
        Returns:
            Scholarly narrative text
        """
        if not self.orchestrator:
            return self._fallback_narrative(analysis_results, term, periods)
        
        narrative_prompt = f"""
        Generate a scholarly narrative for semantic evolution analysis:
        
        Term: "{term}"
        Time Periods: {periods}
        
        Analysis Results:
        {json.dumps(analysis_results, indent=2)}
        
        Requirements:
        1. Academic tone suitable for research publication
        2. Highlight significant semantic changes
        3. Reference specific evidence from analysis
        4. Discuss confidence levels and limitations
        5. Maximum 300 words
        
        Focus on:
        - Evolution patterns and trends
        - Key semantic shifts and their timing
        - Contextual factors influencing change
        - Implications for understanding term usage
        """
        
        try:
            response = await self.orchestrator.send_message(
                message=narrative_prompt,
                system_prompt="You are an expert academic writer specializing in linguistic analysis. Write in formal academic style.",
                temperature=0.4,  # Slightly higher for creative narrative
                max_tokens=400
            )
            
            narrative = response.content.strip()
            logger.info(f"Semantic narrative generated ({len(narrative)} characters)")
            return narrative
            
        except Exception as e:
            logger.error(f"Narrative generation failed: {e}")
            return self._fallback_narrative(analysis_results, term, periods)
    
    def _parse_tool_selection(self, response_text: str) -> Dict[str, Any]:
        """Parse LLM tool selection response."""
        try:
            # Extract JSON from response
            response_text = response_text.strip()
            if response_text.startswith('```'):
                # Remove code block markers
                lines = response_text.split('\n')
                json_lines = []
                in_json = False
                for line in lines:
                    if line.strip().startswith('```'):
                        in_json = not in_json
                    elif in_json:
                        json_lines.append(line)
                response_text = '\n'.join(json_lines)
            
            parsed = json.loads(response_text)
            
            # Validate required fields
            required_fields = ['primary_tools', 'confidence', 'reasoning']
            for field in required_fields:
                if field not in parsed:
                    raise ValueError(f"Missing required field: {field}")
            
            return parsed
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse tool selection: {e}")
            return {
                'primary_tools': ['spacy', 'embeddings'],
                'embedding_model': 'sentence-transformers/all-MiniLM-L6-v2',
                'confidence': 0.5,
                'reasoning': 'Fallback selection due to parsing error',
                'processing_strategy': 'sequential',
                'parse_error': str(e)
            }
    
    def _parse_interpretation(self, response_text: str) -> Dict[str, Any]:
        """Parse LLM interpretation response."""
        try:
            # Similar JSON extraction as tool selection
            response_text = response_text.strip()
            if response_text.startswith('```'):
                lines = response_text.split('\n')
                json_lines = []
                in_json = False
                for line in lines:
                    if line.strip().startswith('```'):
                        in_json = not in_json
                    elif in_json:
                        json_lines.append(line)
                response_text = '\n'.join(json_lines)
            
            parsed = json.loads(response_text)
            
            # Set defaults for missing fields
            defaults = {
                'semantic_features': [],
                'drift_indicators': [],
                'data_quality': {'score': 0.7, 'issues': []},
                'recommendations': [],
                'overall_confidence': 0.7,
                'interpretation_summary': 'Analysis completed'
            }
            
            for key, default_value in defaults.items():
                if key not in parsed:
                    parsed[key] = default_value
            
            return parsed
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse interpretation: {e}")
            return {
                'semantic_features': ['analysis_attempted'],
                'drift_indicators': [],
                'data_quality': {'score': 0.5, 'issues': ['parsing_error']},
                'recommendations': ['manual_review_needed'],
                'overall_confidence': 0.5,
                'interpretation_summary': 'Interpretation failed, manual review required',
                'parse_error': str(e)
            }
    
    def _fallback_tool_selection(self, document_text: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Fallback tool selection when orchestrator unavailable."""
        metadata = metadata or {}
        year = metadata.get('year')
        domain = metadata.get('domain', 'general')
        
        # Simple heuristic-based selection
        tools = ['spacy', 'embeddings']
        embedding_model = 'sentence-transformers/all-MiniLM-L6-v2'
        
        if domain == 'scientific':
            embedding_model = 'allenai/scibert_scivocab_uncased'
        elif domain == 'legal':
            embedding_model = 'nlpaueb/legal-bert-base-uncased'
        elif year and year < 1950:
            tools.append('historical_processing')
        
        return {
            'primary_tools': tools,
            'embedding_model': embedding_model,
            'confidence': 0.6,
            'reasoning': 'Heuristic-based fallback selection',
            'processing_strategy': 'sequential',
            'fallback_mode': True
        }
    
    def _fallback_interpretation(self, nlp_results: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback interpretation when orchestrator unavailable."""
        return {
            'semantic_features': list(nlp_results.keys()) if nlp_results else [],
            'drift_indicators': [],
            'data_quality': {'score': 0.7, 'issues': ['no_llm_interpretation']},
            'recommendations': ['manual_analysis_recommended'],
            'overall_confidence': 0.6,
            'interpretation_summary': 'Basic processing completed, LLM interpretation unavailable',
            'fallback_mode': True
        }
    
    def _fallback_narrative(self, analysis_results: Dict[str, Any], term: str, periods: List[int]) -> str:
        """Fallback narrative generation when orchestrator unavailable."""
        return f"""
        Analysis of semantic evolution for term "{term}" across periods {periods}.
        
        Processing completed using available NLP tools. Detailed interpretation 
        requires LLM orchestration system. Results include basic semantic features 
        and statistical measures. Manual review recommended for comprehensive 
        scholarly analysis.
        
        Data quality appears adequate for preliminary findings. Consider enabling 
        LLM orchestration for enhanced narrative generation and interpretation.
        """.strip()
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of LLM bridge service and orchestrator."""
        health = {
            'bridge_service': 'ok',
            'orchestrator_available': ORCHESTRATOR_AVAILABLE,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if self.orchestrator:
            try:
                orchestrator_health = await self.orchestrator.health_check()
                health['orchestrator'] = orchestrator_health
            except Exception as e:
                health['orchestrator_error'] = str(e)
        
        return health


# Global instance for easy import
_llm_service = None

def get_llm_service() -> OntExtractLLMService:
    """Get the global LLM service instance."""
    global _llm_service
    if _llm_service is None:
        _llm_service = OntExtractLLMService()
    return _llm_service