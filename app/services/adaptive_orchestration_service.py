"""
Adaptive Orchestration Service

Enhanced LLM orchestration that incorporates researcher feedback and learning patterns
for continuous improvement of tool selection decisions.
"""

import os
import json
import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from decimal import Decimal

from app.models.orchestration_logs import OrchestrationDecision, ToolExecutionLog
from app.models.orchestration_feedback import LearningPattern, OrchestrationFeedback
from app.services.llm_bridge_service import OntExtractLLMService

logger = logging.getLogger(__name__)


class AdaptiveOrchestrationService(OntExtractLLMService):
    """
    Enhanced orchestration service that learns from researcher feedback.
    
    Features:
    - Applies learning patterns from historical feedback
    - Weighs LLM decisions against researcher expertise
    - Provides confidence adjustments based on pattern matching
    - Supports real-time decision refinement
    """
    
    def __init__(self, enable_learning: bool = True, learning_weight: float = 0.3):
        """
        Initialize adaptive orchestration service.
        
        Args:
            enable_learning: Whether to apply learning patterns
            learning_weight: How much weight to give learned patterns (0.0-1.0)
        """
        super().__init__()
        self.enable_learning = enable_learning
        self.learning_weight = learning_weight
        self.decision_log = []  # Track decisions for this session
        
        logger.info(f"Adaptive orchestration initialized (learning: {enable_learning}, weight: {learning_weight})")
    
    async def analyze_document_with_learning(self, 
                                           document_text: str,
                                           metadata: Dict[str, Any] = None,
                                           researcher_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Analyze document with learning pattern integration.
        
        Args:
            document_text: Document content
            metadata: Document metadata (year, domain, etc.)
            researcher_context: Context about researcher preferences
            
        Returns:
            Enhanced orchestration decision with learning integration
        """
        
        metadata = metadata or {}
        researcher_context = researcher_context or {}
        
        # Step 1: Get base LLM decision
        base_decision = await self.analyze_document_for_tools(document_text, metadata)
        
        if not self.enable_learning:
            return base_decision
        
        # Step 2: Find applicable learning patterns
        applicable_patterns = LearningPattern.find_applicable_patterns(metadata)
        
        if not applicable_patterns:
            logger.debug("No applicable learning patterns found")
            return base_decision
        
        # Step 3: Apply learning patterns to enhance decision
        enhanced_decision = self._apply_learning_patterns(base_decision, applicable_patterns, metadata)
        
        # Step 4: Adjust confidence based on pattern reliability
        enhanced_decision = self._adjust_confidence_with_patterns(enhanced_decision, applicable_patterns)
        
        # Step 5: Consider researcher context if available
        if researcher_context:
            enhanced_decision = self._incorporate_researcher_preferences(
                enhanced_decision, researcher_context
            )
        
        # Step 6: Log the decision enhancement
        self._log_decision_enhancement(base_decision, enhanced_decision, applicable_patterns)
        
        return enhanced_decision
    
    def _apply_learning_patterns(self, 
                                base_decision: Dict[str, Any], 
                                patterns: List[LearningPattern],
                                context: Dict[str, Any]) -> Dict[str, Any]:
        """Apply learning patterns to enhance base decision"""
        
        enhanced_decision = base_decision.copy()
        applied_patterns = []
        
        # Sort patterns by effectiveness (confidence * success_rate)
        sorted_patterns = sorted(
            patterns,
            key=lambda p: float(p.confidence or 0) * float(p.success_rate or 0.5),
            reverse=True
        )
        
        for pattern in sorted_patterns:
            try:
                # Apply pattern transformation
                pattern_enhanced = pattern.apply_to_decision(enhanced_decision)
                
                # Blend with current decision based on learning weight
                enhanced_decision = self._blend_decisions(
                    enhanced_decision, 
                    pattern_enhanced, 
                    pattern_weight=float(pattern.confidence or 0.5) * self.learning_weight
                )
                
                applied_patterns.append({
                    'pattern_id': str(pattern.id),
                    'pattern_name': pattern.pattern_name,
                    'pattern_type': pattern.pattern_type,
                    'confidence': float(pattern.confidence),
                    'weight_applied': float(pattern.confidence or 0.5) * self.learning_weight
                })
                
                # Record pattern application
                pattern.record_application(success=True)  # Assume success for now
                
            except Exception as e:
                logger.warning(f"Failed to apply pattern {pattern.pattern_name}: {e}")
                continue
        
        # Add metadata about applied patterns
        enhanced_decision['applied_learning_patterns'] = applied_patterns
        enhanced_decision['learning_enhancement'] = True
        
        logger.info(f"Applied {len(applied_patterns)} learning patterns to decision")
        
        return enhanced_decision
    
    def _blend_decisions(self, 
                        base_decision: Dict[str, Any], 
                        pattern_decision: Dict[str, Any], 
                        pattern_weight: float) -> Dict[str, Any]:
        """Blend base LLM decision with pattern-enhanced decision"""
        
        blended = base_decision.copy()
        
        # Tool selection blending
        base_tools = set(base_decision.get('primary_tools', []))
        pattern_tools = set(pattern_decision.get('primary_tools', []))
        
        if pattern_weight > 0.5:
            # High pattern confidence - prefer pattern tools
            blended['primary_tools'] = list(pattern_tools.union(base_tools))
        else:
            # Lower pattern confidence - blend more conservatively
            # Keep base tools, add pattern tools if they don't conflict
            blended_tools = base_tools.copy()
            for tool in pattern_tools:
                if tool not in base_tools and len(blended_tools) < 5:  # Limit tool count
                    blended_tools.add(tool)
            blended['primary_tools'] = list(blended_tools)
        
        # Embedding model selection
        if pattern_weight > 0.6 and pattern_decision.get('embedding_model'):
            blended['embedding_model'] = pattern_decision['embedding_model']
        # else keep base decision
        
        # Processing strategy
        if pattern_weight > 0.7 and pattern_decision.get('processing_strategy'):
            blended['processing_strategy'] = pattern_decision['processing_strategy']
        
        # Reasoning enhancement
        pattern_reasoning = pattern_decision.get('reasoning', '')
        if pattern_reasoning and 'Pattern' not in blended.get('reasoning', ''):
            blended['reasoning'] = blended.get('reasoning', '') + f" Enhanced by learning patterns: {pattern_reasoning}"
        
        return blended
    
    def _adjust_confidence_with_patterns(self, 
                                       decision: Dict[str, Any], 
                                       patterns: List[LearningPattern]) -> Dict[str, Any]:
        """Adjust decision confidence based on pattern reliability"""
        
        if not patterns:
            return decision
        
        base_confidence = decision.get('confidence', 0.5)
        
        # Calculate pattern-based confidence boost
        pattern_confidence_sum = sum(float(p.confidence or 0.5) for p in patterns)
        pattern_success_sum = sum(float(p.success_rate or 0.5) for p in patterns)
        
        avg_pattern_confidence = pattern_confidence_sum / len(patterns)
        avg_pattern_success = pattern_success_sum / len(patterns)
        
        # Boost confidence if patterns are reliable
        pattern_reliability = (avg_pattern_confidence + avg_pattern_success) / 2
        
        if pattern_reliability > 0.7:
            confidence_boost = min(0.2, (pattern_reliability - 0.7) * 0.4)
            adjusted_confidence = min(1.0, base_confidence + confidence_boost)
        else:
            # Slight penalty if patterns are unreliable
            confidence_penalty = max(0.0, (0.7 - pattern_reliability) * 0.1)
            adjusted_confidence = max(0.0, base_confidence - confidence_penalty)
        
        decision['confidence'] = adjusted_confidence
        decision['pattern_reliability'] = pattern_reliability
        decision['confidence_adjustment'] = adjusted_confidence - base_confidence
        
        logger.debug(f"Confidence adjusted: {base_confidence:.3f} → {adjusted_confidence:.3f} (patterns: {pattern_reliability:.3f})")
        
        return decision
    
    def _incorporate_researcher_preferences(self, 
                                          decision: Dict[str, Any], 
                                          researcher_context: Dict[str, Any]) -> Dict[str, Any]:
        """Incorporate known researcher preferences into decision"""
        
        enhanced = decision.copy()
        
        # Researcher expertise weighting
        researcher_domains = researcher_context.get('expertise_domains', [])
        decision_domain = decision.get('domain', 'general')
        
        if decision_domain in researcher_domains:
            # Researcher has expertise in this domain - boost confidence in their preferences
            expertise_weight = researcher_context.get('expertise_level_weight', 0.8)
            
            # Apply researcher tool preferences
            preferred_tools = researcher_context.get('preferred_tools', {})
            if decision_domain in preferred_tools:
                domain_tools = preferred_tools[decision_domain]
                current_tools = set(enhanced.get('primary_tools', []))
                
                # Add researcher-preferred tools
                for tool in domain_tools:
                    if tool not in current_tools:
                        current_tools.add(tool)
                
                enhanced['primary_tools'] = list(current_tools)
                enhanced['researcher_preference_applied'] = True
        
        # Researcher confidence in domain
        if researcher_context.get('domain_confidence'):
            domain_conf = researcher_context['domain_confidence']
            if decision_domain in domain_conf and domain_conf[decision_domain] > 0.8:
                # High researcher confidence - give more weight to their implicit preferences
                enhanced['researcher_authority_weight'] = domain_conf[decision_domain]
        
        return enhanced
    
    def _log_decision_enhancement(self, 
                                 base_decision: Dict[str, Any],
                                 enhanced_decision: Dict[str, Any], 
                                 patterns: List[LearningPattern]):
        """Log decision enhancement for analysis"""
        
        enhancement_log = {
            'timestamp': datetime.utcnow().isoformat(),
            'base_tools': base_decision.get('primary_tools', []),
            'enhanced_tools': enhanced_decision.get('primary_tools', []),
            'base_confidence': base_decision.get('confidence', 0.5),
            'enhanced_confidence': enhanced_decision.get('confidence', 0.5),
            'patterns_applied': len(patterns),
            'pattern_names': [p.pattern_name for p in patterns],
            'learning_weight_used': self.learning_weight
        }
        
        self.decision_log.append(enhancement_log)
        
        # Log significant changes
        if len(set(enhancement_log['enhanced_tools']) - set(enhancement_log['base_tools'])) > 0:
            logger.info(f"Learning patterns added tools: {set(enhancement_log['enhanced_tools']) - set(enhancement_log['base_tools'])}")
        
        if abs(enhancement_log['enhanced_confidence'] - enhancement_log['base_confidence']) > 0.1:
            logger.info(f"Learning patterns changed confidence: {enhancement_log['base_confidence']:.3f} → {enhancement_log['enhanced_confidence']:.3f}")
    
    async def provide_decision_explanation(self, 
                                         decision: Dict[str, Any], 
                                         include_patterns: bool = True) -> str:
        """Generate detailed explanation of orchestration decision for researchers"""
        
        explanation_parts = []
        
        # Base decision explanation
        explanation_parts.append(f"**Primary Analysis**: Selected tools {decision.get('primary_tools', [])} ")
        explanation_parts.append(f"with {decision.get('embedding_model', 'default')} embedding model ")
        explanation_parts.append(f"(confidence: {decision.get('confidence', 'unknown'):.2f}).")
        
        # Original LLM reasoning
        if decision.get('reasoning'):
            explanation_parts.append(f"\n**LLM Reasoning**: {decision['reasoning']}")
        
        # Learning pattern influence
        if include_patterns and decision.get('applied_learning_patterns'):
            explanation_parts.append(f"\n**Learning Pattern Influence**:")
            for pattern in decision['applied_learning_patterns']:
                explanation_parts.append(f"- Applied '{pattern['pattern_name']}' ({pattern['pattern_type']}) ")
                explanation_parts.append(f"with {pattern['weight_applied']:.2f} weight")
        
        # Confidence adjustments
        if decision.get('confidence_adjustment'):
            adj = decision['confidence_adjustment']
            direction = "increased" if adj > 0 else "decreased"
            explanation_parts.append(f"\n**Confidence Adjustment**: {direction} by {abs(adj):.3f} ")
            explanation_parts.append(f"based on pattern reliability ({decision.get('pattern_reliability', 'unknown'):.2f})")
        
        # Researcher preference integration
        if decision.get('researcher_preference_applied'):
            explanation_parts.append(f"\n**Researcher Preferences**: Incorporated domain expertise preferences")
        
        return "".join(explanation_parts)
    
    def get_feedback_integration_opportunities(self, 
                                             decision: Dict[str, Any], 
                                             metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify opportunities for researcher feedback on this decision"""
        
        opportunities = []
        
        # Check for low-confidence decisions
        confidence = decision.get('confidence', 0.5)
        if confidence < 0.7:
            opportunities.append({
                'type': 'low_confidence_decision',
                'priority': 'high',
                'description': f"Decision confidence is low ({confidence:.2f}). Researcher input could improve accuracy.",
                'suggested_feedback': ['tool_selection', 'model_choice', 'confidence_assessment']
            })
        
        # Check for novel contexts
        applicable_patterns = LearningPattern.find_applicable_patterns(metadata)
        if len(applicable_patterns) == 0:
            opportunities.append({
                'type': 'novel_context',
                'priority': 'medium',
                'description': "No historical patterns found for this context. Feedback would create new learning patterns.",
                'suggested_feedback': ['full_decision_review', 'domain_expertise_input']
            })
        
        # Check for conflicting patterns
        if len(applicable_patterns) > 1:
            pattern_conflicts = self._detect_pattern_conflicts(applicable_patterns)
            if pattern_conflicts:
                opportunities.append({
                    'type': 'pattern_conflict',
                    'priority': 'medium',
                    'description': "Multiple patterns suggest different approaches. Researcher input could resolve conflicts.",
                    'conflicting_patterns': pattern_conflicts,
                    'suggested_feedback': ['preference_clarification', 'context_disambiguation']
                })
        
        # Check for domain-specific complexity
        domain = metadata.get('domain', 'general')
        if domain in ['philosophical', 'legal', 'scientific'] and confidence < 0.8:
            opportunities.append({
                'type': 'domain_expertise_needed',
                'priority': 'high',
                'description': f"Complex {domain} domain may benefit from expert review.",
                'suggested_feedback': ['domain_specific_factors', 'specialized_tool_requirements']
            })
        
        return opportunities
    
    def _detect_pattern_conflicts(self, patterns: List[LearningPattern]) -> List[Dict[str, Any]]:
        """Detect conflicts between learning patterns"""
        
        conflicts = []
        
        for i, pattern1 in enumerate(patterns):
            for pattern2 in patterns[i+1:]:
                conflict = self._compare_pattern_recommendations(pattern1, pattern2)
                if conflict:
                    conflicts.append(conflict)
        
        return conflicts
    
    def _compare_pattern_recommendations(self, 
                                       pattern1: LearningPattern, 
                                       pattern2: LearningPattern) -> Optional[Dict[str, Any]]:
        """Compare two patterns for recommendation conflicts"""
        
        rec1 = pattern1.recommendations
        rec2 = pattern2.recommendations
        
        # Tool conflicts
        tools1 = set(rec1.get('tools', []))
        tools2 = set(rec2.get('tools', []))
        
        if pattern1.pattern_type == 'avoidance' and pattern2.pattern_type == 'preference':
            avoid_tools = tools1
            prefer_tools = tools2
            conflicting_tools = avoid_tools.intersection(prefer_tools)
            
            if conflicting_tools:
                return {
                    'type': 'tool_preference_conflict',
                    'pattern1': {'name': pattern1.pattern_name, 'avoids': list(avoid_tools)},
                    'pattern2': {'name': pattern2.pattern_name, 'prefers': list(prefer_tools)},
                    'conflicting_tools': list(conflicting_tools)
                }
        
        # Model conflicts
        model1 = rec1.get('embedding_model')
        model2 = rec2.get('embedding_model')
        
        if model1 and model2 and model1 != model2:
            return {
                'type': 'model_preference_conflict',
                'pattern1': {'name': pattern1.pattern_name, 'model': model1},
                'pattern2': {'name': pattern2.pattern_name, 'model': model2}
            }
        
        return None
    
    def get_decision_enhancement_summary(self) -> Dict[str, Any]:
        """Get summary of decision enhancements made during this session"""
        
        if not self.decision_log:
            return {'enhancement_count': 0}
        
        total_decisions = len(self.decision_log)
        tools_added_count = sum(1 for log in self.decision_log 
                               if set(log['enhanced_tools']) - set(log['base_tools']))
        
        avg_confidence_change = sum(
            log['enhanced_confidence'] - log['base_confidence'] 
            for log in self.decision_log
        ) / total_decisions
        
        total_patterns_applied = sum(log['patterns_applied'] for log in self.decision_log)
        
        return {
            'enhancement_count': total_decisions,
            'tools_added_sessions': tools_added_count,
            'average_confidence_change': avg_confidence_change,
            'total_patterns_applied': total_patterns_applied,
            'learning_effectiveness': avg_confidence_change > 0.05  # Threshold for meaningful improvement
        }