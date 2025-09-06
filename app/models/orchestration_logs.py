"""
LLM Orchestration Decision Logging Models

PROV-O compliant models for logging LLM orchestration decisions, tool selections,
and provenance chains for academic research and audit trails.
"""

from sqlalchemy.dialects.postgresql import UUID, JSON, ARRAY
from datetime import datetime
from app import db
import uuid
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class OrchestrationDecision(db.Model):
    """PROV-O Activity: LLM orchestration decisions for tool selection and coordination"""
    
    __tablename__ = 'orchestration_decisions'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # PROV-O Activity metadata
    activity_type = db.Column(db.String(50), default='llm_orchestration', nullable=False)
    started_at_time = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    ended_at_time = db.Column(db.DateTime(timezone=True))
    activity_status = db.Column(db.String(20), default='completed', index=True)
    
    # Document context
    document_id = db.Column(UUID(as_uuid=True), db.ForeignKey('documents.id'), index=True)
    experiment_id = db.Column(UUID(as_uuid=True), db.ForeignKey('experiments.id'), index=True)
    term_text = db.Column(db.String(255), index=True)
    
    # Input metadata that influenced decision
    input_metadata = db.Column(JSON)  # year, domain, format, length, etc.
    document_characteristics = db.Column(JSON)  # detected features
    
    # LLM orchestration details
    orchestrator_provider = db.Column(db.String(50))  # claude, gpt4, gemini
    orchestrator_model = db.Column(db.String(100))
    orchestrator_prompt = db.Column(db.Text)
    orchestrator_response = db.Column(db.Text)
    orchestrator_response_time_ms = db.Column(db.Integer)
    
    # Decision outputs
    selected_tools = db.Column(ARRAY(db.String))  # ['spacy', 'embeddings', 'word2vec']
    embedding_model = db.Column(db.String(100))
    processing_strategy = db.Column(db.String(50))  # sequential, parallel
    expected_runtime_seconds = db.Column(db.Integer)
    
    # Confidence and reasoning
    decision_confidence = db.Column(db.Numeric(4,3))  # 0.000 to 1.000
    reasoning_summary = db.Column(db.Text)
    decision_factors = db.Column(JSON)  # structured reasoning components
    
    # Validation and outcomes
    decision_validated = db.Column(db.Boolean)
    actual_runtime_seconds = db.Column(db.Integer)
    tool_execution_success = db.Column(JSON)  # per-tool success rates
    
    # PROV-O relationships
    was_associated_with = db.Column(UUID(as_uuid=True), db.ForeignKey('analysis_agents.id'))
    used_entity = db.Column(UUID(as_uuid=True), db.ForeignKey('term_versions.id'))
    
    # Audit trail
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, index=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relationships
    document = db.relationship('Document', backref='orchestration_decisions')
    experiment = db.relationship('Experiment', backref='orchestration_decisions')
    analysis_agent = db.relationship('AnalysisAgent', backref='orchestration_decisions')
    term_version = db.relationship('TermVersion', backref='orchestration_decisions')
    creator = db.relationship('User', backref='created_orchestration_decisions')
    
    # Constraints
    __table_args__ = (
        db.CheckConstraint("activity_status IN ('running', 'completed', 'error', 'timeout')"),
        db.CheckConstraint("decision_confidence >= 0 AND decision_confidence <= 1"),
        db.Index('idx_orchestration_term_time', 'term_text', 'created_at'),
        db.Index('idx_orchestration_experiment', 'experiment_id', 'created_at'),
    )
    
    def __init__(self, **kwargs):
        """Initialize orchestration decision with metadata"""
        super().__init__()
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def log_decision_start(self, prompt: str, input_metadata: Dict[str, Any]):
        """Log the start of an orchestration decision"""
        self.orchestrator_prompt = prompt
        self.input_metadata = input_metadata
        self.activity_status = 'running'
        self.started_at_time = datetime.utcnow()
        
        # Extract document characteristics
        self.document_characteristics = self._extract_document_characteristics(input_metadata)
        
        logger.info(f"Orchestration decision started for term: {self.term_text}")
    
    def log_decision_complete(self, response: str, decision_data: Dict[str, Any], 
                            provider: str, response_time_ms: int):
        """Log the completion of an orchestration decision"""
        self.orchestrator_response = response
        self.orchestrator_provider = provider
        self.orchestrator_response_time_ms = response_time_ms
        self.ended_at_time = datetime.utcnow()
        self.activity_status = 'completed'
        
        # Extract decision details
        self.selected_tools = decision_data.get('primary_tools', [])
        self.embedding_model = decision_data.get('embedding_model')
        self.processing_strategy = decision_data.get('processing_strategy', 'sequential')
        self.expected_runtime_seconds = decision_data.get('expected_runtime', 0)
        self.decision_confidence = decision_data.get('confidence', 0.5)
        self.reasoning_summary = decision_data.get('reasoning', '')
        
        # Structure decision factors for analysis
        self.decision_factors = self._extract_decision_factors(decision_data)
        
        logger.info(f"Orchestration decision completed: {self.selected_tools} (confidence: {self.decision_confidence})")
    
    def log_execution_results(self, tool_success: Dict[str, bool], actual_runtime: int):
        """Log the results of executing the orchestrated tools"""
        self.tool_execution_success = tool_success
        self.actual_runtime_seconds = actual_runtime
        self.decision_validated = all(tool_success.values()) if tool_success else False
        
        logger.info(f"Tool execution completed: {sum(tool_success.values())}/{len(tool_success)} successful")
    
    def _extract_document_characteristics(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Extract structured document characteristics for decision analysis"""
        characteristics = {}
        
        # Temporal characteristics
        year = metadata.get('year')
        if year:
            characteristics['temporal_period'] = self._classify_temporal_period(year)
            characteristics['historical_distance'] = abs(datetime.now().year - int(year))
        
        # Content characteristics
        text_length = metadata.get('text_length', 0)
        characteristics['text_complexity'] = self._classify_text_complexity(text_length)
        
        # Domain characteristics
        domain = metadata.get('domain', 'general')
        characteristics['domain_specificity'] = domain
        characteristics['requires_specialized_models'] = domain in ['scientific', 'legal', 'medical']
        
        # Format characteristics
        format_type = metadata.get('format', 'unknown')
        characteristics['format_type'] = format_type
        characteristics['structured_content'] = format_type in ['json', 'xml', 'csv']
        
        return characteristics
    
    def _classify_temporal_period(self, year: int) -> str:
        """Classify year into temporal processing periods"""
        if year < 1800:
            return 'pre_modern'
        elif year < 1950:
            return 'historical'
        elif year < 2000:
            return 'late_modern'
        else:
            return 'contemporary'
    
    def _classify_text_complexity(self, length: int) -> str:
        """Classify text complexity based on length"""
        if length < 1000:
            return 'simple'
        elif length < 5000:
            return 'moderate'
        elif length < 20000:
            return 'complex'
        else:
            return 'extensive'
    
    def _extract_decision_factors(self, decision_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract structured decision factors for analysis"""
        factors = {}
        
        # Tool selection rationale
        factors['tool_selection_rationale'] = {
            'primary_tools': decision_data.get('primary_tools', []),
            'tool_count': len(decision_data.get('primary_tools', [])),
            'processing_strategy': decision_data.get('processing_strategy')
        }
        
        # Model selection rationale
        factors['model_selection_rationale'] = {
            'embedding_model': decision_data.get('embedding_model'),
            'model_type': self._classify_model_type(decision_data.get('embedding_model', '')),
            'specialization': self._get_model_specialization(decision_data.get('embedding_model', ''))
        }
        
        # Confidence factors
        factors['confidence_factors'] = {
            'overall_confidence': decision_data.get('confidence', 0.5),
            'confidence_level': self._classify_confidence_level(decision_data.get('confidence', 0.5)),
            'uncertainty_sources': self._identify_uncertainty_sources(decision_data)
        }
        
        return factors
    
    def _classify_model_type(self, model_name: str) -> str:
        """Classify embedding model type"""
        if 'bert' in model_name.lower():
            if 'scibert' in model_name.lower():
                return 'scientific_bert'
            elif 'legal' in model_name.lower():
                return 'legal_bert'
            else:
                return 'general_bert'
        elif 'sentence-transformer' in model_name.lower():
            return 'sentence_transformer'
        else:
            return 'unknown'
    
    def _get_model_specialization(self, model_name: str) -> str:
        """Get model domain specialization"""
        if 'sci' in model_name.lower():
            return 'scientific'
        elif 'legal' in model_name.lower():
            return 'legal'
        elif 'bio' in model_name.lower():
            return 'biomedical'
        else:
            return 'general'
    
    def _classify_confidence_level(self, confidence: float) -> str:
        """Classify confidence level"""
        if confidence >= 0.8:
            return 'high'
        elif confidence >= 0.6:
            return 'moderate'
        elif confidence >= 0.4:
            return 'low'
        else:
            return 'very_low'
    
    def _identify_uncertainty_sources(self, decision_data: Dict[str, Any]) -> List[str]:
        """Identify sources of uncertainty in decision"""
        sources = []
        
        if decision_data.get('confidence', 1.0) < 0.7:
            sources.append('low_overall_confidence')
        
        if not decision_data.get('reasoning'):
            sources.append('limited_reasoning_provided')
        
        if len(decision_data.get('primary_tools', [])) > 3:
            sources.append('complex_tool_selection')
        
        if decision_data.get('processing_strategy') == 'parallel':
            sources.append('parallel_processing_complexity')
        
        return sources
    
    def get_decision_summary(self) -> Dict[str, Any]:
        """Get a structured summary of the orchestration decision"""
        return {
            'decision_id': str(self.id),
            'timestamp': self.started_at_time.isoformat() if self.started_at_time else None,
            'term': self.term_text,
            'selected_tools': self.selected_tools,
            'embedding_model': self.embedding_model,
            'confidence': float(self.decision_confidence) if self.decision_confidence else None,
            'processing_strategy': self.processing_strategy,
            'provider': self.orchestrator_provider,
            'response_time_ms': self.orchestrator_response_time_ms,
            'success': self.decision_validated,
            'reasoning': self.reasoning_summary
        }
    
    def __repr__(self):
        return f'<OrchestrationDecision {self.term_text} -> {self.selected_tools}>'


class ToolExecutionLog(db.Model):
    """PROV-O Activity: Individual NLP tool execution logs with performance metrics"""
    
    __tablename__ = 'tool_execution_logs'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Reference to parent orchestration decision
    orchestration_decision_id = db.Column(UUID(as_uuid=True), 
                                        db.ForeignKey('orchestration_decisions.id'), 
                                        nullable=False, index=True)
    
    # Tool execution details
    tool_name = db.Column(db.String(50), nullable=False, index=True)
    tool_version = db.Column(db.String(50))
    execution_order = db.Column(db.Integer)  # Order in processing pipeline
    
    # Execution timing
    started_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    completed_at = db.Column(db.DateTime(timezone=True))
    execution_time_ms = db.Column(db.Integer)
    
    # Execution results
    execution_status = db.Column(db.String(20), default='running', index=True)
    output_data = db.Column(JSON)  # Tool-specific outputs
    error_message = db.Column(db.Text)
    
    # Performance metrics
    memory_usage_mb = db.Column(db.Integer)
    cpu_usage_percent = db.Column(db.Numeric(5,2))
    output_quality_score = db.Column(db.Numeric(4,3))
    
    # Relationships
    orchestration_decision = db.relationship('OrchestrationDecision', 
                                           backref='tool_execution_logs')
    
    # Constraints
    __table_args__ = (
        db.CheckConstraint("execution_status IN ('running', 'completed', 'error', 'timeout', 'skipped')"),
        db.CheckConstraint("output_quality_score >= 0 AND output_quality_score <= 1"),
        db.Index('idx_tool_execution_decision_order', 'orchestration_decision_id', 'execution_order'),
    )
    
    def log_execution_start(self, tool_name: str, execution_order: int = 0):
        """Log the start of tool execution"""
        self.tool_name = tool_name
        self.execution_order = execution_order
        self.execution_status = 'running'
        self.started_at = datetime.utcnow()
        
        logger.debug(f"Tool execution started: {tool_name} (order: {execution_order})")
    
    def log_execution_complete(self, output_data: Dict[str, Any], 
                             quality_score: Optional[float] = None):
        """Log successful completion of tool execution"""
        self.completed_at = datetime.utcnow()
        self.execution_time_ms = int((self.completed_at - self.started_at).total_seconds() * 1000)
        self.execution_status = 'completed'
        self.output_data = output_data
        
        if quality_score is not None:
            self.output_quality_score = quality_score
        
        logger.debug(f"Tool execution completed: {self.tool_name} in {self.execution_time_ms}ms")
    
    def log_execution_error(self, error_message: str):
        """Log tool execution error"""
        self.completed_at = datetime.utcnow()
        self.execution_time_ms = int((self.completed_at - self.started_at).total_seconds() * 1000)
        self.execution_status = 'error'
        self.error_message = error_message
        
        logger.error(f"Tool execution error: {self.tool_name} - {error_message}")
    
    def __repr__(self):
        return f'<ToolExecutionLog {self.tool_name} ({self.execution_status})>'


class MultiModelConsensus(db.Model):
    """PROV-O Activity: Multi-model validation and consensus logging"""
    
    __tablename__ = 'multi_model_consensus'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Reference to parent orchestration
    orchestration_decision_id = db.Column(UUID(as_uuid=True), 
                                        db.ForeignKey('orchestration_decisions.id'), 
                                        nullable=False, index=True)
    
    # Consensus process metadata
    validation_type = db.Column(db.String(50), default='multi_model_consensus')
    models_involved = db.Column(ARRAY(db.String))  # ['claude-3.5', 'gpt-4', 'gemini-1.5']
    consensus_method = db.Column(db.String(50))  # majority_vote, weighted_average, threshold
    
    # Model-specific results
    model_responses = db.Column(JSON)  # Per-model detailed responses
    model_confidence_scores = db.Column(JSON)  # Per-model confidence
    model_agreement_matrix = db.Column(JSON)  # Pairwise agreement scores
    
    # Consensus outcomes
    consensus_reached = db.Column(db.Boolean)
    consensus_confidence = db.Column(db.Numeric(4,3))
    final_decision = db.Column(JSON)
    disagreement_areas = db.Column(JSON)  # Areas where models disagreed
    
    # Timing and metadata
    started_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    completed_at = db.Column(db.DateTime(timezone=True))
    total_processing_time_ms = db.Column(db.Integer)
    
    # Relationships
    orchestration_decision = db.relationship('OrchestrationDecision', 
                                           backref='consensus_validations')
    
    # Constraints
    __table_args__ = (
        db.CheckConstraint("consensus_confidence >= 0 AND consensus_confidence <= 1"),
    )
    
    def calculate_consensus(self, model_results: Dict[str, Dict[str, Any]], 
                          method: str = 'majority_vote') -> Dict[str, Any]:
        """Calculate consensus from multiple model results"""
        self.models_involved = list(model_results.keys())
        self.model_responses = model_results
        self.consensus_method = method
        
        # Extract confidence scores
        confidence_scores = {}
        for model, result in model_results.items():
            confidence_scores[model] = result.get('confidence', 0.5)
        
        self.model_confidence_scores = confidence_scores
        
        # Calculate consensus based on method
        if method == 'majority_vote':
            return self._majority_vote_consensus(model_results)
        elif method == 'weighted_average':
            return self._weighted_average_consensus(model_results)
        elif method == 'threshold':
            return self._threshold_consensus(model_results)
        else:
            raise ValueError(f"Unknown consensus method: {method}")
    
    def _majority_vote_consensus(self, model_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate consensus using majority vote"""
        # Implementation for majority vote consensus
        decisions = {}
        for model, result in model_results.items():
            primary_tools = result.get('primary_tools', [])
            for tool in primary_tools:
                decisions[tool] = decisions.get(tool, 0) + 1
        
        # Select tools with majority support
        majority_threshold = len(model_results) / 2
        consensus_tools = [tool for tool, count in decisions.items() if count > majority_threshold]
        
        # Calculate overall confidence
        confidences = [result.get('confidence', 0.5) for result in model_results.values()]
        avg_confidence = sum(confidences) / len(confidences)
        
        self.consensus_reached = len(consensus_tools) > 0
        self.consensus_confidence = avg_confidence
        self.final_decision = {'primary_tools': consensus_tools}
        
        return self.final_decision
    
    def _weighted_average_consensus(self, model_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate consensus using weighted average"""
        # Implementation for weighted average consensus
        # Weight decisions by model confidence scores
        total_weight = sum(result.get('confidence', 0.5) for result in model_results.values())
        
        if total_weight == 0:
            return self._majority_vote_consensus(model_results)
        
        # Weighted tool selection
        tool_weights = {}
        for model, result in model_results.items():
            weight = result.get('confidence', 0.5) / total_weight
            for tool in result.get('primary_tools', []):
                tool_weights[tool] = tool_weights.get(tool, 0) + weight
        
        # Select tools above weighted threshold
        weighted_threshold = 0.3
        consensus_tools = [tool for tool, weight in tool_weights.items() if weight >= weighted_threshold]
        
        # Weighted confidence
        weighted_confidence = sum(
            result.get('confidence', 0.5) * (result.get('confidence', 0.5) / total_weight)
            for result in model_results.values()
        )
        
        self.consensus_reached = len(consensus_tools) > 0
        self.consensus_confidence = weighted_confidence
        self.final_decision = {'primary_tools': consensus_tools}
        
        return self.final_decision
    
    def _threshold_consensus(self, model_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate consensus using confidence threshold"""
        threshold = 0.7
        high_confidence_results = {
            model: result for model, result in model_results.items()
            if result.get('confidence', 0) >= threshold
        }
        
        if not high_confidence_results:
            # Fall back to majority vote if no high-confidence results
            return self._majority_vote_consensus(model_results)
        
        # Use majority vote among high-confidence results
        return self._majority_vote_consensus(high_confidence_results)
    
    def __repr__(self):
        return f'<MultiModelConsensus {len(self.models_involved)} models, consensus: {self.consensus_reached}>'