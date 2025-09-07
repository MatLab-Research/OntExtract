"""
LLM Orchestration Coordinator - Stage 2 of Two-Stage Architecture

Receives LangExtract structured extractions and coordinates subsequent NLP analysis
through intelligent tool selection and synthesis coordination.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

# Import shared services for multi-provider LLM access
from app.services.langextract_document_analyzer import LangExtractDocumentAnalyzer

logger = logging.getLogger(__name__)


class LLMOrchestrationCoordinator:
    """
    Stage 2: Orchestrating LLM that coordinates NLP analysis
    
    Based on LangExtract structured extractions, this service:
    1. Analyzes extracted content to determine tool selection
    2. Routes to appropriate NLP tools based on content characteristics
    3. Coordinates synthesis of multiple pipeline outputs
    4. Handles graceful degradation and fallback mechanisms
    """
    
    def __init__(self):
        """Initialize orchestration coordinator"""
        
        # Available NLP tools and their capabilities
        self.available_tools = {
            # Basic NLP Tools
            'spacy_nlp': {
                'capabilities': ['tokenization', 'pos_tagging', 'ner', 'dependency_parsing'],
                'best_for': ['general_text', 'modern_english'],
                'processing_time': 'fast',
                'reliability': 0.9
            },
            'basic_tokenization': {
                'capabilities': ['word_splitting', 'sentence_splitting'],
                'best_for': ['simple_preprocessing', 'fallback'],
                'processing_time': 'very_fast',
                'reliability': 0.95
            },
            
            # Historical/Period-Aware Tools
            'historical_nlp': {
                'capabilities': ['archaic_terminology', 'historical_context', 'period_aware_parsing'],
                'best_for': ['pre_1950_texts', 'historical_documents'],
                'processing_time': 'slow',
                'reliability': 0.8
            },
            'period_aware_embeddings': {
                'capabilities': ['temporal_embeddings', 'semantic_drift_analysis'],
                'best_for': ['temporal_analysis', 'semantic_evolution'],
                'processing_time': 'medium',
                'reliability': 0.85
            },
            'historical_contextualization': {
                'capabilities': ['period_context', 'historical_significance'],
                'best_for': ['academic_analysis', 'temporal_grounding'],
                'processing_time': 'medium',
                'reliability': 0.8
            },
            
            # Domain-Specific Tools
            'technical_tokenizer': {
                'capabilities': ['technical_terminology', 'domain_parsing'],
                'best_for': ['scientific_texts', 'technical_documents'],
                'processing_time': 'fast',
                'reliability': 0.85
            },
            'domain_embeddings': {
                'capabilities': ['domain_specific_vectors', 'specialized_similarity'],
                'best_for': ['domain_analysis', 'technical_concepts'],
                'processing_time': 'medium',
                'reliability': 0.85
            },
            'philosophical_nlp': {
                'capabilities': ['philosophical_concepts', 'argument_structure'],
                'best_for': ['philosophy_texts', 'ethical_analysis'],
                'processing_time': 'slow',
                'reliability': 0.8
            },
            'legal_nlp': {
                'capabilities': ['legal_terminology', 'case_references'],
                'best_for': ['legal_documents', 'case_analysis'],
                'processing_time': 'medium',
                'reliability': 0.8
            },
            
            # Analysis Tools
            'temporal_analysis': {
                'capabilities': ['temporal_extraction', 'period_classification'],
                'best_for': ['chronological_analysis', 'temporal_patterns'],
                'processing_time': 'medium',
                'reliability': 0.85
            },
            'semantic_drift_analysis': {
                'capabilities': ['meaning_evolution', 'semantic_change'],
                'best_for': ['diachronic_analysis', 'concept_evolution'],
                'processing_time': 'slow',
                'reliability': 0.8
            },
            'embedding_generation': {
                'capabilities': ['vector_representations', 'similarity_calculation'],
                'best_for': ['semantic_similarity', 'clustering'],
                'processing_time': 'medium',
                'reliability': 0.9
            }
        }
        
        # Initialize LLM client for orchestration decisions
        self.orchestrator_llm = self._initialize_orchestrator_llm()
    
    def _initialize_orchestrator_llm(self):
        """Initialize LLM client for orchestration decisions"""
        
        # Try Anthropic first, then OpenAI
        if os.environ.get('ANTHROPIC_API_KEY'):
            try:
                import anthropic
                return anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))
            except ImportError:
                logger.warning("Anthropic client not available")
        
        if os.environ.get('OPENAI_API_KEY'):
            try:
                from openai import OpenAI
                return OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
            except ImportError:
                logger.warning("OpenAI client not available")
        
        logger.warning("No LLM client available - using fallback orchestration")
        return None
    
    def orchestrate_analysis(self, langextract_results: Dict[str, Any], 
                           document_text: str, 
                           user_preferences: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Main orchestration method that coordinates NLP analysis
        
        Args:
            langextract_results: Structured extractions from Stage 1
            document_text: Original document text
            user_preferences: Optional user preferences for analysis
            
        Returns:
            Orchestration plan with tool selection and coordination
        """
        
        # Analyze LangExtract results for orchestration decisions
        orchestration_context = self._analyze_orchestration_context(langextract_results)
        
        # Generate orchestration plan using LLM
        orchestration_plan = self._generate_orchestration_plan(
            orchestration_context, langextract_results, user_preferences
        )
        
        # Validate and optimize the plan
        optimized_plan = self._optimize_orchestration_plan(orchestration_plan)
        
        # Add execution metadata
        execution_plan = self._prepare_execution_plan(optimized_plan, langextract_results)
        
        return execution_plan
    
    def _analyze_orchestration_context(self, langextract_results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze LangExtract results to understand orchestration requirements"""
        
        context = {
            'content_characteristics': {},
            'processing_requirements': {},
            'tool_selection_factors': {},
            'synthesis_complexity': 'medium'
        }
        
        # Analyze content characteristics
        temporal_markers = langextract_results.get('temporal_markers', [])
        key_concepts = langextract_results.get('key_concepts', [])
        domain_indicators = langextract_results.get('domain_indicators', [])
        
        context['content_characteristics'] = {
            'temporal_complexity': len(temporal_markers),
            'concept_density': len(key_concepts),
            'domain_specificity': len(domain_indicators),
            'extraction_confidence': langextract_results.get('extraction_confidence', 0.5)
        }
        
        # Determine processing requirements
        complexity = langextract_results.get('analytical_complexity', 'medium')
        context['processing_requirements'] = {
            'complexity_level': complexity,
            'expected_duration': langextract_results.get('orchestration_metadata', {}).get('expected_processing_time', 'standard'),
            'resource_intensity': 'high' if complexity == 'high' else 'medium'
        }
        
        # Analyze tool selection factors
        context['tool_selection_factors'] = {
            'period_specialization_needed': any('historical' in str(marker) for marker in temporal_markers),
            'domain_specialization_needed': len(domain_indicators) > 0,
            'technical_processing_needed': complexity in ['high', 'technical'],
            'temporal_analysis_needed': len(temporal_markers) > 2
        }
        
        # Determine synthesis complexity
        tool_count = len(langextract_results.get('recommended_tools', []))
        if tool_count > 5 or complexity == 'high':
            context['synthesis_complexity'] = 'high'
        elif tool_count > 3:
            context['synthesis_complexity'] = 'medium'
        else:
            context['synthesis_complexity'] = 'low'
        
        return context
    
    def _generate_orchestration_plan(self, context: Dict[str, Any], 
                                   langextract_results: Dict[str, Any], 
                                   user_preferences: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate orchestration plan using LLM reasoning"""
        
        if self.orchestrator_llm:
            return self._llm_orchestration_decision(context, langextract_results, user_preferences)
        else:
            return self._fallback_orchestration_decision(context, langextract_results, user_preferences)
    
    def _llm_orchestration_decision(self, context: Dict[str, Any], 
                                  langextract_results: Dict[str, Any], 
                                  user_preferences: Dict[str, Any] = None) -> Dict[str, Any]:
        """Use LLM to make sophisticated orchestration decisions"""
        
        # Prepare orchestration prompt
        orchestration_prompt = f"""
        You are an expert NLP pipeline orchestrator. Based on the structured document analysis below, 
        determine the optimal sequence and coordination of NLP tools.

        DOCUMENT ANALYSIS FROM LANGEXTRACT:
        - Key concepts extracted: {len(langextract_results.get('key_concepts', []))}
        - Temporal markers: {len(langextract_results.get('temporal_markers', []))}
        - Domain indicators: {langextract_results.get('domain_indicators', [])}
        - Complexity level: {langextract_results.get('analytical_complexity', 'medium')}
        - Recommended tools: {langextract_results.get('recommended_tools', [])}

        ORCHESTRATION CONTEXT:
        - Content characteristics: {context.get('content_characteristics', {})}
        - Processing requirements: {context.get('processing_requirements', {})}
        - Tool selection factors: {context.get('tool_selection_factors', {})}

        AVAILABLE TOOLS AND CAPABILITIES:
        {json.dumps(self.available_tools, indent=2)}

        USER PREFERENCES: {user_preferences or "None specified"}

        Based on this analysis, provide an orchestration plan as JSON:
        {{
            "selected_tools": ["tool1", "tool2", ...],
            "processing_sequence": [
                {{"tool": "tool_name", "stage": 1, "rationale": "why this tool at this stage"}},
                ...
            ],
            "parallel_processing": {{"stage_1": ["tool1", "tool2"], "stage_2": ["tool3"]}},
            "synthesis_strategy": "how to combine outputs",
            "confidence": 0.85,
            "estimated_processing_time": "2-4 minutes",
            "fallback_plan": ["fallback_tool1", "fallback_tool2"],
            "orchestration_rationale": "detailed explanation of tool selection and sequencing"
        }}

        Focus on:
        1. Tool selection based on content characteristics (historical vs modern, technical vs general)
        2. Optimal sequencing to build analysis progressively
        3. Parallel processing opportunities to reduce total time
        4. Synthesis strategy to combine different analytical perspectives
        5. Robust fallback mechanisms for reliability
        """
        
        try:
            if hasattr(self.orchestrator_llm, 'messages'):  # Anthropic
                message = self.orchestrator_llm.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=4000,
                    temperature=0.3,  # Balanced creativity and consistency
                    messages=[{"role": "user", "content": orchestration_prompt}]
                )
                response_text = message.content[0].text.strip()
            else:  # OpenAI fallback
                response = self.orchestrator_llm.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": orchestration_prompt}],
                    max_tokens=4000,
                    temperature=0.3
                )
                response_text = response.choices[0].message.content.strip()
            
            # Parse JSON response
            if response_text.startswith('```'):
                response_text = response_text.split('```')[1]
                if response_text.startswith('json'):
                    response_text = response_text[4:]
            
            orchestration_plan = json.loads(response_text)
            
            # Validate the plan
            if not isinstance(orchestration_plan.get('selected_tools'), list):
                raise ValueError("Invalid selected_tools format")
            
            return orchestration_plan
            
        except Exception as e:
            logger.error(f"LLM orchestration failed: {e}")
            return self._fallback_orchestration_decision(context, langextract_results, user_preferences)
    
    def _fallback_orchestration_decision(self, context: Dict[str, Any], 
                                       langextract_results: Dict[str, Any], 
                                       user_preferences: Dict[str, Any] = None) -> Dict[str, Any]:
        """Fallback rule-based orchestration when LLM is unavailable"""
        
        selected_tools = []
        processing_sequence = []
        stage = 1
        
        # Rule-based tool selection
        recommended = langextract_results.get('recommended_tools', [])
        
        # Stage 1: Basic preprocessing
        if 'spacy_nlp' in recommended:
            selected_tools.append('spacy_nlp')
            processing_sequence.append({
                'tool': 'spacy_nlp',
                'stage': stage,
                'rationale': 'Basic NLP preprocessing and entity recognition'
            })
        
        # Stage 2: Domain-specific processing
        stage += 1
        domain_tools = [t for t in recommended if any(d in t for d in ['historical', 'technical', 'legal', 'philosophical'])]
        for tool in domain_tools:
            if tool in self.available_tools:
                selected_tools.append(tool)
                processing_sequence.append({
                    'tool': tool,
                    'stage': stage,
                    'rationale': f'Domain-specific processing for {tool}'
                })
        
        # Stage 3: Analysis tools
        stage += 1
        analysis_tools = [t for t in recommended if 'analysis' in t or 'embedding' in t]
        for tool in analysis_tools:
            if tool in self.available_tools:
                selected_tools.append(tool)
                processing_sequence.append({
                    'tool': tool,
                    'stage': stage,
                    'rationale': f'Analytical processing with {tool}'
                })
        
        # Fallback if no tools selected
        if not selected_tools:
            selected_tools = ['spacy_nlp', 'basic_tokenization']
            processing_sequence = [
                {'tool': 'spacy_nlp', 'stage': 1, 'rationale': 'Fallback basic NLP'},
                {'tool': 'basic_tokenization', 'stage': 2, 'rationale': 'Fallback tokenization'}
            ]
        
        return {
            'selected_tools': selected_tools,
            'processing_sequence': processing_sequence,
            'parallel_processing': {'stage_1': selected_tools[:2]} if len(selected_tools) > 1 else {},
            'synthesis_strategy': 'sequential_integration',
            'confidence': 0.6,
            'estimated_processing_time': '1-2 minutes',
            'fallback_plan': ['spacy_nlp', 'basic_tokenization'],
            'orchestration_rationale': 'Rule-based fallback orchestration due to LLM unavailability',
            'orchestration_method': 'fallback_rules'
        }
    
    def _optimize_orchestration_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize orchestration plan for efficiency and reliability"""
        
        # Remove unavailable tools
        available_tools = [t for t in plan.get('selected_tools', []) if t in self.available_tools]
        plan['selected_tools'] = available_tools
        
        # Optimize processing sequence
        optimized_sequence = []
        for seq_item in plan.get('processing_sequence', []):
            if seq_item.get('tool') in self.available_tools:
                # Add reliability score
                tool_info = self.available_tools[seq_item['tool']]
                seq_item['reliability'] = tool_info.get('reliability', 0.8)
                seq_item['expected_duration'] = tool_info.get('processing_time', 'medium')
                optimized_sequence.append(seq_item)
        
        plan['processing_sequence'] = optimized_sequence
        
        # Ensure fallback plan is valid
        fallback = [t for t in plan.get('fallback_plan', []) if t in self.available_tools]
        if not fallback:
            fallback = ['spacy_nlp', 'basic_tokenization']
        plan['fallback_plan'] = fallback
        
        return plan
    
    def _prepare_execution_plan(self, orchestration_plan: Dict[str, Any], 
                              langextract_results: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare final execution plan with metadata"""
        
        return {
            'orchestration_id': f"orch_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            'timestamp': datetime.utcnow().isoformat(),
            'langextract_stage_completed': True,
            'orchestration_stage_completed': True,
            'ready_for_execution': True,
            
            # Core orchestration plan
            'orchestration_plan': orchestration_plan,
            
            # LangExtract context
            'langextract_analysis': {
                'extraction_confidence': langextract_results.get('extraction_confidence', 0.5),
                'key_concepts_count': len(langextract_results.get('key_concepts', [])),
                'temporal_markers_count': len(langextract_results.get('temporal_markers', [])),
                'domain_indicators': langextract_results.get('domain_indicators', []),
                'character_level_positions': langextract_results.get('character_positions', False)
            },
            
            # Execution metadata
            'execution_metadata': {
                'total_tools_selected': len(orchestration_plan.get('selected_tools', [])),
                'processing_stages': len(set(s.get('stage', 1) for s in orchestration_plan.get('processing_sequence', []))),
                'estimated_total_time': orchestration_plan.get('estimated_processing_time', 'unknown'),
                'orchestration_confidence': orchestration_plan.get('confidence', 0.5),
                'synthesis_required': True,
                'fallback_available': bool(orchestration_plan.get('fallback_plan'))
            },
            
            # Synthesis preparation
            'synthesis_preparation': {
                'strategy': orchestration_plan.get('synthesis_strategy', 'sequential_integration'),
                'output_format': 'unified_semantic_narrative',
                'integration_points': self._identify_integration_points(orchestration_plan),
                'validation_requirements': ['consistency_check', 'completeness_validation', 'confidence_assessment']
            }
        }
    
    def _identify_integration_points(self, orchestration_plan: Dict[str, Any]) -> List[str]:
        """Identify where different tool outputs need integration"""
        
        tools = orchestration_plan.get('selected_tools', [])
        integration_points = []
        
        # Integration between basic NLP and domain tools
        if any('spacy' in t for t in tools) and any(d in t for t in tools for d in ['historical', 'technical', 'legal']):
            integration_points.append('basic_domain_integration')
        
        # Integration between embeddings and temporal analysis
        if any('embedding' in t for t in tools) and any('temporal' in t for t in tools):
            integration_points.append('semantic_temporal_integration')
        
        # Integration between multiple analysis tools
        analysis_tools = [t for t in tools if 'analysis' in t]
        if len(analysis_tools) > 1:
            integration_points.append('multi_analysis_synthesis')
        
        return integration_points
    
    def get_orchestration_summary(self, execution_plan: Dict[str, Any]) -> Dict[str, str]:
        """Generate human-readable summary of orchestration decisions"""
        
        plan = execution_plan.get('orchestration_plan', {})
        tools = plan.get('selected_tools', [])
        
        summary = {
            'tools_selected': f"{len(tools)} tools selected: {', '.join(tools)}",
            'processing_approach': plan.get('synthesis_strategy', 'sequential_integration'),
            'confidence_level': f"{plan.get('confidence', 0.5):.1%} confidence in orchestration decisions",
            'expected_duration': plan.get('estimated_processing_time', 'unknown'),
            'orchestration_rationale': plan.get('orchestration_rationale', 'No rationale provided')
        }
        
        return summary