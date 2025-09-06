"""
Human-in-the-Loop Orchestration Feedback Models

PROV-O compliant models for capturing researcher feedback on orchestration decisions
and implementing adaptive learning to improve future tool selection accuracy.
"""

from sqlalchemy.dialects.postgresql import UUID, JSON, ARRAY
from datetime import datetime
from app import db
import uuid
import logging
from typing import List, Dict, Any, Optional
from decimal import Decimal

logger = logging.getLogger(__name__)


class OrchestrationFeedback(db.Model):
    """PROV-O Entity: Researcher feedback on orchestration decisions for continuous improvement"""
    
    __tablename__ = 'orchestration_feedback'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Reference to original decision
    orchestration_decision_id = db.Column(UUID(as_uuid=True), 
                                        db.ForeignKey('orchestration_decisions.id'), 
                                        nullable=False, index=True)
    
    # Researcher providing feedback
    researcher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    researcher_expertise = db.Column(JSON)  # Domain expertise areas
    
    # Feedback metadata
    feedback_type = db.Column(db.String(50), nullable=False, index=True)  # 'correction', 'enhancement', 'validation'
    feedback_scope = db.Column(db.String(50))  # 'tool_selection', 'model_choice', 'strategy', 'confidence'
    
    # Original vs. Preferred decisions
    original_decision = db.Column(JSON)  # Snapshot of original decision
    researcher_preference = db.Column(JSON)  # What researcher would have chosen
    
    # Detailed feedback
    agreement_level = db.Column(db.String(20))  # 'strongly_agree', 'agree', 'neutral', 'disagree', 'strongly_disagree'
    confidence_assessment = db.Column(db.Numeric(4,3))  # Researcher's confidence in their feedback
    
    reasoning = db.Column(db.Text, nullable=False)  # Why researcher disagrees/agrees
    domain_specific_factors = db.Column(JSON)  # Domain knowledge that LLM missed
    
    # Suggested improvements
    suggested_tools = db.Column(ARRAY(db.String))
    suggested_embedding_model = db.Column(db.String(100))
    suggested_processing_strategy = db.Column(db.String(50))
    alternative_reasoning = db.Column(db.Text)
    
    # Learning integration
    feedback_status = db.Column(db.String(20), default='pending', index=True)  # pending, reviewed, integrated, rejected
    integration_notes = db.Column(db.Text)  # How feedback was used to improve system
    
    # Impact tracking
    subsequent_decisions_influenced = db.Column(db.Integer, default=0)
    improvement_verified = db.Column(db.Boolean)
    verification_notes = db.Column(db.Text)
    
    # Temporal metadata
    provided_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, index=True)
    reviewed_at = db.Column(db.DateTime(timezone=True))
    integrated_at = db.Column(db.DateTime(timezone=True))
    
    # Relationships
    orchestration_decision = db.relationship('OrchestrationDecision', backref='feedback_entries')
    researcher = db.relationship('User', backref='orchestration_feedback')
    
    # Constraints
    __table_args__ = (
        db.CheckConstraint("feedback_type IN ('correction', 'enhancement', 'validation', 'clarification')"),
        db.CheckConstraint("agreement_level IN ('strongly_agree', 'agree', 'neutral', 'disagree', 'strongly_disagree')"),
        db.CheckConstraint("feedback_status IN ('pending', 'reviewed', 'integrated', 'rejected', 'obsolete')"),
        db.CheckConstraint("confidence_assessment >= 0 AND confidence_assessment <= 1"),
        db.Index('idx_feedback_decision_researcher', 'orchestration_decision_id', 'researcher_id'),
        db.Index('idx_feedback_type_status', 'feedback_type', 'feedback_status'),
    )
    
    def __init__(self, **kwargs):
        """Initialize feedback with researcher context"""
        super().__init__()
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def create_from_decision(self, orchestration_decision, researcher, feedback_data: Dict[str, Any]):
        """Create feedback entry from orchestration decision and researcher input"""
        
        # Snapshot original decision for comparison
        self.original_decision = {
            'selected_tools': orchestration_decision.selected_tools,
            'embedding_model': orchestration_decision.embedding_model,
            'processing_strategy': orchestration_decision.processing_strategy,
            'confidence': float(orchestration_decision.decision_confidence) if orchestration_decision.decision_confidence else None,
            'reasoning': orchestration_decision.reasoning_summary
        }
        
        # Set researcher preference
        self.researcher_preference = feedback_data.get('preferred_decision', {})
        
        # Extract feedback details
        self.feedback_type = feedback_data.get('type', 'correction')
        self.feedback_scope = feedback_data.get('scope', 'tool_selection')
        self.agreement_level = feedback_data.get('agreement', 'disagree')
        self.confidence_assessment = Decimal(str(feedback_data.get('confidence', 0.8)))
        self.reasoning = feedback_data.get('reasoning', '')
        
        # Domain-specific factors
        self.domain_specific_factors = feedback_data.get('domain_factors', {})
        
        # Suggestions
        self.suggested_tools = feedback_data.get('suggested_tools', [])
        self.suggested_embedding_model = feedback_data.get('suggested_model')
        self.suggested_processing_strategy = feedback_data.get('suggested_strategy')
        self.alternative_reasoning = feedback_data.get('alternative_reasoning')
        
        # Researcher expertise context
        self.researcher_expertise = feedback_data.get('expertise', {})
        
        logger.info(f"Feedback created for decision {orchestration_decision.id} by researcher {researcher.id}")
    
    def analyze_disagreement(self) -> Dict[str, Any]:
        """Analyze the nature and scope of disagreement with original decision"""
        
        analysis = {
            'disagreement_areas': [],
            'severity': 'minor',
            'actionable_insights': [],
            'domain_knowledge_gaps': []
        }
        
        original = self.original_decision
        preferred = self.researcher_preference
        
        # Tool selection disagreement
        if set(original.get('selected_tools', [])) != set(preferred.get('selected_tools', [])):
            analysis['disagreement_areas'].append('tool_selection')
            
            removed_tools = set(original.get('selected_tools', [])) - set(preferred.get('selected_tools', []))
            added_tools = set(preferred.get('selected_tools', [])) - set(original.get('selected_tools', []))
            
            if removed_tools:
                analysis['actionable_insights'].append(f"Consider avoiding {list(removed_tools)} for similar contexts")
            if added_tools:
                analysis['actionable_insights'].append(f"Consider including {list(added_tools)} for similar contexts")
        
        # Embedding model disagreement
        if original.get('embedding_model') != preferred.get('embedding_model'):
            analysis['disagreement_areas'].append('embedding_model')
            analysis['actionable_insights'].append(f"Prefer {preferred.get('embedding_model')} over {original.get('embedding_model')} for this domain")
        
        # Processing strategy disagreement
        if original.get('processing_strategy') != preferred.get('processing_strategy'):
            analysis['disagreement_areas'].append('processing_strategy')
        
        # Determine severity
        if len(analysis['disagreement_areas']) >= 3:
            analysis['severity'] = 'major'
        elif len(analysis['disagreement_areas']) == 2:
            analysis['severity'] = 'moderate'
        
        # Extract domain knowledge gaps
        if self.domain_specific_factors:
            for factor, value in self.domain_specific_factors.items():
                analysis['domain_knowledge_gaps'].append(f"{factor}: {value}")
        
        return analysis
    
    def generate_learning_pattern(self) -> Dict[str, Any]:
        """Generate a learning pattern for improving future decisions"""
        
        disagreement = self.analyze_disagreement()
        
        # Extract contextual pattern from original decision
        context_pattern = {
            'input_metadata': self.orchestration_decision.input_metadata,
            'document_characteristics': self.orchestration_decision.document_characteristics,
            'decision_factors': self.orchestration_decision.decision_factors
        }
        
        # Create improvement pattern
        learning_pattern = {
            'pattern_id': str(uuid.uuid4()),
            'context_signature': self._generate_context_signature(context_pattern),
            'feedback_type': self.feedback_type,
            'confidence': float(self.confidence_assessment),
            'researcher_expertise': self.researcher_expertise,
            
            'avoid_decisions': {
                'tools': list(set(self.original_decision.get('selected_tools', [])) - set(self.researcher_preference.get('selected_tools', []))),
                'embedding_model': self.original_decision.get('embedding_model') if self.original_decision.get('embedding_model') != self.researcher_preference.get('embedding_model') else None,
                'reasoning_patterns': self._extract_problematic_reasoning()
            },
            
            'prefer_decisions': {
                'tools': self.suggested_tools or self.researcher_preference.get('selected_tools', []),
                'embedding_model': self.suggested_embedding_model or self.researcher_preference.get('embedding_model'),
                'processing_strategy': self.suggested_processing_strategy or self.researcher_preference.get('processing_strategy'),
                'reasoning': self.alternative_reasoning
            },
            
            'domain_insights': self.domain_specific_factors,
            'applicability_conditions': self._generate_applicability_conditions(),
            'created_at': self.provided_at.isoformat(),
            'researcher_authority': self._assess_researcher_authority()
        }
        
        return learning_pattern
    
    def _generate_context_signature(self, context: Dict[str, Any]) -> str:
        """Generate a signature for matching similar contexts"""
        
        signature_elements = []
        
        input_meta = context.get('input_metadata', {})
        if input_meta.get('year'):
            # Decade-based grouping
            decade = (int(input_meta['year']) // 10) * 10
            signature_elements.append(f"decade:{decade}s")
        
        if input_meta.get('domain'):
            signature_elements.append(f"domain:{input_meta['domain']}")
        
        if input_meta.get('complexity'):
            signature_elements.append(f"complexity:{input_meta['complexity']}")
        
        doc_chars = context.get('document_characteristics', {})
        if doc_chars.get('temporal_period'):
            signature_elements.append(f"period:{doc_chars['temporal_period']}")
        
        if doc_chars.get('requires_specialized_models'):
            signature_elements.append("specialized:true")
        
        return "|".join(sorted(signature_elements))
    
    def _extract_problematic_reasoning(self) -> List[str]:
        """Extract problematic reasoning patterns from original decision"""
        
        problematic_patterns = []
        original_reasoning = self.original_decision.get('reasoning', '').lower()
        
        # Common problematic patterns
        if 'modern tools sufficient' in original_reasoning and 'historical' in str(self.orchestration_decision.input_metadata):
            problematic_patterns.append('underestimating_historical_complexity')
        
        if 'standard' in original_reasoning and self.researcher_preference.get('embedding_model', '').startswith('specialized'):
            problematic_patterns.append('ignoring_domain_specialization')
        
        return problematic_patterns
    
    def _generate_applicability_conditions(self) -> Dict[str, Any]:
        """Generate conditions for when this feedback should be applied"""
        
        conditions = {}
        
        # Temporal conditions
        input_meta = self.orchestration_decision.input_metadata or {}
        if input_meta.get('year'):
            year = int(input_meta['year'])
            conditions['year_range'] = {
                'min': year - 20,  # Apply to similar time periods
                'max': year + 20
            }
        
        # Domain conditions
        if input_meta.get('domain'):
            conditions['domains'] = [input_meta['domain']]
            
            # Extend to related domains
            domain_relations = {
                'philosophical': ['ethical', 'metaphysical', 'epistemological'],
                'scientific': ['technical', 'medical', 'engineering'],
                'legal': ['regulatory', 'governmental', 'policy']
            }
            
            related = domain_relations.get(input_meta['domain'], [])
            conditions['domains'].extend(related)
        
        # Complexity conditions
        if input_meta.get('complexity'):
            conditions['complexity_levels'] = [input_meta['complexity']]
        
        # Text characteristics
        doc_chars = self.orchestration_decision.document_characteristics or {}
        if doc_chars.get('historical_distance'):
            distance = doc_chars['historical_distance']
            conditions['historical_distance_range'] = {
                'min': max(0, distance - 50),
                'max': distance + 50
            }
        
        return conditions
    
    def _assess_researcher_authority(self) -> Dict[str, Any]:
        """Assess the authority/credibility of the researcher providing feedback"""
        
        authority = {
            'confidence_score': float(self.confidence_assessment),
            'expertise_match': 0.5,  # Default
            'feedback_quality': 'medium'  # Will be assessed over time
        }
        
        # Check expertise match with decision context
        if self.researcher_expertise:
            context_domain = self.orchestration_decision.input_metadata.get('domain', '')
            researcher_domains = self.researcher_expertise.get('domains', [])
            
            if context_domain in researcher_domains:
                authority['expertise_match'] = 1.0
            elif any(domain in context_domain for domain in researcher_domains):
                authority['expertise_match'] = 0.8
        
        # Assess feedback quality based on detail and reasoning
        if self.reasoning and len(self.reasoning) > 100:
            authority['feedback_quality'] = 'high'
        elif not self.reasoning or len(self.reasoning) < 20:
            authority['feedback_quality'] = 'low'
        
        return authority
    
    def mark_integrated(self, integration_notes: str = ''):
        """Mark feedback as integrated into learning system"""
        self.feedback_status = 'integrated'
        self.integrated_at = datetime.utcnow()
        self.integration_notes = integration_notes
        
        logger.info(f"Feedback {self.id} marked as integrated")
    
    def track_impact(self, influenced_decisions: int):
        """Track the impact of this feedback on subsequent decisions"""
        self.subsequent_decisions_influenced = influenced_decisions
        
        if influenced_decisions > 0:
            self.improvement_verified = True
            self.verification_notes = f"Influenced {influenced_decisions} subsequent decisions"
    
    def __repr__(self):
        return f'<OrchestrationFeedback {self.feedback_type} by researcher {self.researcher_id}>'


class LearningPattern(db.Model):
    """Codified learning patterns derived from researcher feedback for improving orchestration"""
    
    __tablename__ = 'learning_patterns'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Pattern metadata
    pattern_name = db.Column(db.String(100), nullable=False)
    pattern_type = db.Column(db.String(50), nullable=False, index=True)  # 'avoidance', 'preference', 'enhancement'
    context_signature = db.Column(db.String(200), nullable=False, index=True)
    
    # Pattern definition
    conditions = db.Column(JSON, nullable=False)  # When to apply this pattern
    recommendations = db.Column(JSON, nullable=False)  # What to recommend
    confidence = db.Column(db.Numeric(4,3), nullable=False)
    
    # Source tracking
    derived_from_feedback = db.Column(UUID(as_uuid=True), db.ForeignKey('orchestration_feedback.id'))
    researcher_authority = db.Column(JSON)  # Authority assessment of source researcher
    
    # Usage tracking
    times_applied = db.Column(db.Integer, default=0)
    success_rate = db.Column(db.Numeric(4,3))  # How often this pattern led to better outcomes
    last_applied = db.Column(db.DateTime(timezone=True))
    
    # Pattern evolution
    pattern_status = db.Column(db.String(20), default='active', index=True)  # active, deprecated, under_review
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    source_feedback = db.relationship('OrchestrationFeedback', backref='derived_patterns')
    
    # Constraints
    __table_args__ = (
        db.CheckConstraint("pattern_type IN ('avoidance', 'preference', 'enhancement', 'domain_specific')"),
        db.CheckConstraint("pattern_status IN ('active', 'deprecated', 'under_review', 'experimental')"),
        db.CheckConstraint("confidence >= 0 AND confidence <= 1"),
        db.CheckConstraint("success_rate >= 0 AND success_rate <= 1"),
        db.Index('idx_pattern_context_type', 'context_signature', 'pattern_type'),
    )
    
    @classmethod
    def find_applicable_patterns(cls, orchestration_context: Dict[str, Any]) -> List['LearningPattern']:
        """Find learning patterns applicable to given orchestration context"""
        
        # Generate context signature for matching
        context_sig = cls._generate_context_signature(orchestration_context)
        
        # Find patterns with matching or similar contexts
        applicable_patterns = []
        
        # Exact match patterns
        exact_matches = cls.query.filter(
            cls.context_signature == context_sig,
            cls.pattern_status == 'active'
        ).all()
        
        applicable_patterns.extend(exact_matches)
        
        # Fuzzy match patterns (similar contexts)
        similar_patterns = cls.query.filter(
            cls.context_signature.contains(orchestration_context.get('domain', '')),
            cls.pattern_status == 'active'
        ).all()
        
        for pattern in similar_patterns:
            if pattern not in applicable_patterns and cls._context_matches(pattern.conditions, orchestration_context):
                applicable_patterns.append(pattern)
        
        # Sort by confidence and success rate
        applicable_patterns.sort(
            key=lambda p: (float(p.confidence or 0) * float(p.success_rate or 0.5)),
            reverse=True
        )
        
        return applicable_patterns
    
    @staticmethod
    def _generate_context_signature(context: Dict[str, Any]) -> str:
        """Generate context signature for pattern matching"""
        
        signature_elements = []
        
        if context.get('year'):
            decade = (int(context['year']) // 10) * 10
            signature_elements.append(f"decade:{decade}s")
        
        if context.get('domain'):
            signature_elements.append(f"domain:{context['domain']}")
        
        if context.get('complexity'):
            signature_elements.append(f"complexity:{context['complexity']}")
        
        return "|".join(sorted(signature_elements))
    
    @staticmethod
    def _context_matches(pattern_conditions: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Check if pattern conditions match the given context"""
        
        # Year range matching
        if 'year_range' in pattern_conditions and 'year' in context:
            year_range = pattern_conditions['year_range']
            context_year = int(context['year'])
            if not (year_range['min'] <= context_year <= year_range['max']):
                return False
        
        # Domain matching
        if 'domains' in pattern_conditions and 'domain' in context:
            if context['domain'] not in pattern_conditions['domains']:
                return False
        
        # Complexity matching
        if 'complexity_levels' in pattern_conditions and 'complexity' in context:
            if context['complexity'] not in pattern_conditions['complexity_levels']:
                return False
        
        return True
    
    def apply_to_decision(self, base_decision: Dict[str, Any]) -> Dict[str, Any]:
        """Apply this learning pattern to modify a base orchestration decision"""
        
        enhanced_decision = base_decision.copy()
        recommendations = self.recommendations
        
        # Apply tool recommendations
        if 'tools' in recommendations:
            if self.pattern_type == 'avoidance':
                # Remove tools to avoid
                current_tools = set(enhanced_decision.get('primary_tools', []))
                avoid_tools = set(recommendations['tools'])
                enhanced_decision['primary_tools'] = list(current_tools - avoid_tools)
            
            elif self.pattern_type == 'preference':
                # Add or prioritize preferred tools
                current_tools = enhanced_decision.get('primary_tools', [])
                prefer_tools = recommendations['tools']
                
                # Add preferred tools if not present
                for tool in prefer_tools:
                    if tool not in current_tools:
                        current_tools.append(tool)
                
                enhanced_decision['primary_tools'] = current_tools
        
        # Apply embedding model recommendations
        if 'embedding_model' in recommendations:
            enhanced_decision['embedding_model'] = recommendations['embedding_model']
        
        # Apply processing strategy recommendations
        if 'processing_strategy' in recommendations:
            enhanced_decision['processing_strategy'] = recommendations['processing_strategy']
        
        # Enhance reasoning with pattern insights
        pattern_reasoning = f" [Pattern {self.pattern_name}: {recommendations.get('reasoning', 'Applied learned preferences')}]"
        enhanced_decision['reasoning'] = enhanced_decision.get('reasoning', '') + pattern_reasoning
        
        # Adjust confidence based on pattern confidence
        if 'confidence' in enhanced_decision:
            pattern_weight = float(self.confidence) * (float(self.success_rate) if self.success_rate else 0.5)
            adjusted_confidence = (enhanced_decision['confidence'] + pattern_weight) / 2
            enhanced_decision['confidence'] = min(1.0, adjusted_confidence)
        
        return enhanced_decision
    
    def record_application(self, success: bool = True):
        """Record that this pattern was applied and update success metrics"""
        
        self.times_applied += 1
        self.last_applied = datetime.utcnow()
        
        # Update success rate using exponential moving average
        if self.success_rate is None:
            self.success_rate = Decimal('1.0' if success else '0.0')
        else:
            alpha = 0.1  # Learning rate
            new_success = 1.0 if success else 0.0
            self.success_rate = Decimal(str(
                float(self.success_rate) * (1 - alpha) + new_success * alpha
            ))
        
        self.updated_at = datetime.utcnow()
        
        logger.info(f"Pattern {self.pattern_name} applied (success: {success}). New success rate: {self.success_rate}")
    
    def __repr__(self):
        return f'<LearningPattern {self.pattern_name} ({self.pattern_type})>'


class OrchestrationOverride(db.Model):
    """Manual overrides applied by researchers to specific orchestration decisions"""
    
    __tablename__ = 'orchestration_overrides'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Reference to decision being overridden
    orchestration_decision_id = db.Column(UUID(as_uuid=True), 
                                        db.ForeignKey('orchestration_decisions.id'), 
                                        nullable=False, index=True)
    
    # Researcher applying override
    researcher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Override details
    override_type = db.Column(db.String(50), nullable=False)  # 'full_replacement', 'tool_addition', 'tool_removal', 'model_change'
    original_decision = db.Column(JSON, nullable=False)
    overridden_decision = db.Column(JSON, nullable=False)
    
    # Justification
    justification = db.Column(db.Text, nullable=False)
    expert_knowledge_applied = db.Column(JSON)  # Specific domain knowledge used
    
    # Execution tracking
    override_applied = db.Column(db.Boolean, default=False)
    execution_results = db.Column(JSON)  # Results of executing overridden decision
    performance_comparison = db.Column(JSON)  # Comparison with original decision
    
    # Temporal metadata
    applied_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    orchestration_decision = db.relationship('OrchestrationDecision', backref='manual_overrides')
    researcher = db.relationship('User', backref='applied_overrides')
    
    # Constraints
    __table_args__ = (
        db.CheckConstraint("override_type IN ('full_replacement', 'tool_addition', 'tool_removal', 'model_change', 'strategy_change')"),
        db.Index('idx_override_decision_researcher', 'orchestration_decision_id', 'researcher_id'),
    )
    
    def execute_override(self) -> Dict[str, Any]:
        """Execute the overridden decision and track results"""
        
        # This would integrate with the actual tool execution system
        # For now, return a simulated result structure
        
        execution_result = {
            'override_id': str(self.id),
            'execution_status': 'completed',
            'tools_executed': self.overridden_decision.get('primary_tools', []),
            'execution_time': 45,  # seconds
            'results_quality': 0.92,
            'researcher_satisfaction': 'high'
        }
        
        self.override_applied = True
        self.execution_results = execution_result
        
        logger.info(f"Override {self.id} executed with results: {execution_result}")
        
        return execution_result
    
    def generate_improvement_insights(self) -> Dict[str, Any]:
        """Generate insights for improving future orchestration based on this override"""
        
        insights = {
            'override_pattern': self.override_type,
            'domain_knowledge_gap': self.expert_knowledge_applied,
            'decision_improvement': {
                'original': self.original_decision,
                'improved': self.overridden_decision,
                'key_changes': self._identify_key_changes()
            },
            'applicability': {
                'context_signature': self._generate_override_context(),
                'generalization_potential': self._assess_generalization()
            }
        }
        
        return insights
    
    def _identify_key_changes(self) -> List[str]:
        """Identify the key changes made in the override"""
        
        changes = []
        original = self.original_decision
        overridden = self.overridden_decision
        
        # Tool changes
        orig_tools = set(original.get('primary_tools', []))
        new_tools = set(overridden.get('primary_tools', []))
        
        if orig_tools != new_tools:
            added = new_tools - orig_tools
            removed = orig_tools - new_tools
            
            if added:
                changes.append(f"Added tools: {', '.join(added)}")
            if removed:
                changes.append(f"Removed tools: {', '.join(removed)}")
        
        # Model changes
        if original.get('embedding_model') != overridden.get('embedding_model'):
            changes.append(f"Changed model: {original.get('embedding_model')} → {overridden.get('embedding_model')}")
        
        # Strategy changes
        if original.get('processing_strategy') != overridden.get('processing_strategy'):
            changes.append(f"Changed strategy: {original.get('processing_strategy')} → {overridden.get('processing_strategy')}")
        
        return changes
    
    def _generate_override_context(self) -> str:
        """Generate context signature for this override"""
        
        decision = self.orchestration_decision
        input_meta = decision.input_metadata or {}
        
        context_elements = []
        
        if input_meta.get('domain'):
            context_elements.append(f"domain:{input_meta['domain']}")
        
        if input_meta.get('year'):
            decade = (int(input_meta['year']) // 10) * 10
            context_elements.append(f"decade:{decade}s")
        
        context_elements.append(f"override_type:{self.override_type}")
        
        return "|".join(sorted(context_elements))
    
    def _assess_generalization(self) -> str:
        """Assess how generalizable this override is to other decisions"""
        
        if self.expert_knowledge_applied and len(self.expert_knowledge_applied) > 2:
            return 'high'  # Rich domain knowledge suggests broad applicability
        elif self.override_type in ['tool_addition', 'model_change']:
            return 'medium'  # Specific changes can often be generalized
        else:
            return 'low'  # Very specific or full replacements are harder to generalize
    
    def __repr__(self):
        return f'<OrchestrationOverride {self.override_type} by researcher {self.researcher_id}>'