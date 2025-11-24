"""
Experiment Orchestration Run Model

Tracks experiment-level orchestration where an LLM analyzes all documents
together and recommends a coherent processing strategy.
"""

from app import db
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid


class ExperimentOrchestrationRun(db.Model):
    """
    Stores state for experiment-level orchestration runs.

    Workflow stages:
    1. Analyze Experiment - Understand goals and focus term
    2. Recommend Strategy - Suggest tools per document
    3. Human Review - Optional approval/modification
    4. Execute Strategy - Process all documents
    5. Synthesize Experiment - Cross-document insights
    """

    __tablename__ = 'experiment_orchestration_runs'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    experiment_id = db.Column(db.Integer, db.ForeignKey('experiments.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Timestamps
    started_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

    # Workflow status
    status = db.Column(db.String(50), nullable=False)  # analyzing, recommending, reviewing, executing, synthesizing, completed, failed
    current_stage = db.Column(db.String(50), nullable=True)
    current_operation = db.Column(db.Text, nullable=True)  # Detailed status: "Processing doc 3/7 with extract_entities_spacy"
    celery_task_id = db.Column(db.String(255), nullable=True, index=True)  # Celery task ID for background tracking
    error_message = db.Column(db.Text, nullable=True)

    # Stage 1: Experiment Understanding
    experiment_goal = db.Column(db.Text, nullable=True)
    term_context = db.Column(db.Text, nullable=True)  # Focus term if present

    # Stage 2: Strategy Recommendation
    recommended_strategy = db.Column(JSONB, nullable=True)  # {doc_id: [tools]}
    strategy_reasoning = db.Column(db.Text, nullable=True)
    confidence = db.Column(db.Float, nullable=True)

    # Stage 3: Human Review
    strategy_approved = db.Column(db.Boolean, nullable=True, default=False)
    modified_strategy = db.Column(JSONB, nullable=True)
    review_notes = db.Column(db.Text, nullable=True)
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)

    # Stage 4: Execution
    processing_results = db.Column(JSONB, nullable=True)
    execution_trace = db.Column(JSONB, nullable=True)  # PROV-O provenance

    # Stage 5: Synthesis
    cross_document_insights = db.Column(db.Text, nullable=True)
    term_evolution_analysis = db.Column(db.Text, nullable=True)  # If focus term exists
    comparative_summary = db.Column(db.Text, nullable=True)

    # Structured outputs for card-based visualizations (experiment-type specific)
    generated_term_cards = db.Column(JSONB, nullable=True)  # For temporal_evolution: period-by-period term cards
    generated_domain_cards = db.Column(JSONB, nullable=True)  # For domain_comparison: domain-specific cards
    generated_entity_cards = db.Column(JSONB, nullable=True)  # For entity_extraction: entity relationship cards

    # Relationships
    experiment = db.relationship('Experiment', backref=db.backref('orchestration_runs', passive_deletes=True))
    user = db.relationship('User', foreign_keys=[user_id], backref='orchestration_runs')
    reviewer = db.relationship('User', foreign_keys=[reviewed_by])

    def __repr__(self):
        return f'<ExperimentOrchestrationRun {self.id} - Experiment {self.experiment_id} - {self.status}>'

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'id': str(self.id),
            'experiment_id': self.experiment_id,
            'user_id': self.user_id,
            'status': self.status,
            'current_stage': self.current_stage,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'error_message': self.error_message,

            # Stage 1
            'experiment_goal': self.experiment_goal,
            'term_context': self.term_context,

            # Stage 2
            'recommended_strategy': self.recommended_strategy,
            'strategy_reasoning': self.strategy_reasoning,
            'confidence': self.confidence,

            # Stage 3
            'strategy_approved': self.strategy_approved,
            'modified_strategy': self.modified_strategy,
            'review_notes': self.review_notes,
            'reviewed_by': self.reviewed_by,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,

            # Stage 4
            'processing_results': self.processing_results,
            'execution_trace': self.execution_trace,

            # Stage 5
            'cross_document_insights': self.cross_document_insights,
            'term_evolution_analysis': self.term_evolution_analysis,
            'comparative_summary': self.comparative_summary,

            # Structured outputs
            'generated_term_cards': self.generated_term_cards,
            'generated_domain_cards': self.generated_domain_cards,
            'generated_entity_cards': self.generated_entity_cards
        }
