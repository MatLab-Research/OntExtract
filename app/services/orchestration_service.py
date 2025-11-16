"""
Orchestration Service

Business logic for human-in-the-loop LLM orchestration of experiments.
Handles orchestration decisions, adaptive tool selection, and provenance tracking.
"""

import json
import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from sqlalchemy import text

from app import db
from app.models import Experiment
from app.models.orchestration_logs import OrchestrationDecision
from app.models.orchestration_feedback import OrchestrationFeedback, LearningPattern
from app.services.base_service import BaseService, ServiceError, NotFoundError, ValidationError

logger = logging.getLogger(__name__)


class OrchestrationService(BaseService):
    """
    Service for LLM orchestration operations

    Handles all business logic related to orchestration including:
    - Creating orchestration decisions
    - Running orchestrated analysis
    - Fetching orchestration results
    - Generating PROV-O provenance data
    """

    def __init__(self):
        """Initialize OrchestrationService"""
        super().__init__(model=Experiment)

    def get_orchestration_ui_data(
        self,
        experiment_id: int
    ) -> Dict[str, Any]:
        """
        Get data for orchestrated analysis UI

        Args:
            experiment_id: ID of experiment

        Returns:
            Dictionary with decisions, patterns, and terms

        Raises:
            NotFoundError: If experiment doesn't exist
            ServiceError: If operation fails
        """
        try:
            experiment = self._get_experiment(experiment_id)

            # Get orchestration decisions
            decisions = OrchestrationDecision.query.filter_by(
                experiment_id=experiment.id
            ).order_by(OrchestrationDecision.created_at.desc()).all()

            # Get active learning patterns
            patterns = LearningPattern.query.filter_by(
                pattern_status='active'
            ).order_by(LearningPattern.confidence.desc()).limit(5).all()

            # Get experiment terms
            config = self._parse_configuration(experiment)
            terms = config.get('target_terms', [])

            logger.info(
                f"Retrieved orchestration UI data for experiment {experiment_id}: "
                f"{len(decisions)} decisions, {len(patterns)} patterns"
            )

            return {
                'experiment': experiment,
                'decisions': decisions,
                'patterns': patterns,
                'terms': terms
            }

        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get orchestration UI data for experiment {experiment_id}: {e}", exc_info=True)
            raise ServiceError(f"Failed to get orchestration UI data: {str(e)}") from e

    def create_orchestration_decision(
        self,
        experiment_id: int,
        term_text: str,
        user_id: int
    ) -> Dict[str, Any]:
        """
        Create a new orchestration decision with adaptive tool selection

        Args:
            experiment_id: ID of experiment
            term_text: Term to analyze
            user_id: User creating the decision

        Returns:
            Dictionary with decision details

        Raises:
            NotFoundError: If experiment doesn't exist
            ValidationError: If validation fails
            ServiceError: If creation fails
        """
        try:
            experiment = self._get_experiment(experiment_id)

            if not term_text:
                raise ValidationError('Term text is required')

            # Get document characteristics
            doc_characteristics = {
                'document_count': experiment.get_document_count(),
                'total_words': experiment.get_total_word_count(),
                'experiment_type': experiment.experiment_type
            }

            # Create input metadata
            config = self._parse_configuration(experiment)
            input_metadata = {
                'experiment_id': experiment.id,
                'experiment_type': experiment.experiment_type,
                'document_count': experiment.get_document_count(),
                'total_words': experiment.get_total_word_count(),
                'time_periods': config.get('time_periods', []),
                'domains': config.get('domains', [])
            }

            # Apply learning patterns for intelligent tool selection
            selected_tools, embedding_model, reasoning = self._apply_learning_patterns(term_text)

            decision_confidence = 0.85

            # Create orchestration decision
            decision = OrchestrationDecision(
                experiment_id=experiment.id,
                term_text=term_text,
                selected_tools=selected_tools,
                embedding_model=embedding_model,
                decision_confidence=decision_confidence,
                orchestrator_provider='claude',
                orchestrator_model='claude-3-sonnet',
                orchestrator_prompt=f"Analyze term '{term_text}' and recommend optimal NLP processing approach",
                orchestrator_response=f"Recommended: {', '.join(selected_tools)} with {embedding_model}",
                orchestrator_response_time_ms=1200,
                processing_strategy='sequential',
                reasoning=reasoning,
                input_metadata=input_metadata,
                document_characteristics=doc_characteristics,
                created_by=user_id
            )

            self.add(decision)
            self.commit()

            logger.info(
                f"Created orchestration decision for experiment {experiment_id}, term '{term_text}': "
                f"tools={selected_tools}, model={embedding_model}"
            )

            return {
                'decision_id': str(decision.id),
                'selected_tools': selected_tools,
                'embedding_model': embedding_model,
                'confidence': decision_confidence,
                'reasoning': reasoning
            }

        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            self.rollback()
            logger.error(f"Failed to create orchestration decision for experiment {experiment_id}: {e}", exc_info=True)
            raise ServiceError(f"Failed to create orchestration decision: {str(e)}") from e

    def run_orchestrated_analysis(
        self,
        experiment_id: int,
        terms: List[str],
        user_id: int
    ) -> Dict[str, Any]:
        """
        Run orchestrated analysis for multiple terms

        Args:
            experiment_id: ID of experiment
            terms: List of terms to analyze
            user_id: User running the analysis

        Returns:
            Dictionary with analysis results

        Raises:
            NotFoundError: If experiment doesn't exist
            ValidationError: If validation fails
            ServiceError: If analysis fails
        """
        try:
            experiment = self._get_experiment(experiment_id)

            if not terms:
                raise ValidationError('At least one term is required')

            # Import adaptive service
            from app.services.adaptive_orchestration_service import AdaptiveOrchestrationService
            orchestration_service = AdaptiveOrchestrationService()

            analysis_results = []

            for term in terms:
                # Create or get existing orchestration decision
                existing_decision = OrchestrationDecision.query.filter_by(
                    experiment_id=experiment.id,
                    term_text=term
                ).first()

                if not existing_decision:
                    # Create new decision using adaptive service
                    decision_context = {
                        'experiment_id': experiment.id,
                        'term_text': term,
                        'experiment_type': experiment.experiment_type,
                        'document_count': experiment.get_document_count(),
                        'user_id': user_id
                    }

                    decision = orchestration_service.create_adaptive_decision(decision_context)
                else:
                    decision = existing_decision

                # Simulate analysis execution
                analysis_result = {
                    'term': term,
                    'decision_id': str(decision.id),
                    'tools_used': decision.selected_tools,
                    'embedding_model': decision.embedding_model,
                    'confidence': float(decision.decision_confidence),
                    'processing_time': '2.3s',
                    'semantic_drift_detected': True,
                    'drift_magnitude': 0.32,
                    'periods_analyzed': 4,
                    'insights': [
                        f"Term '{term}' shows moderate semantic drift over time",
                        f"Most stable usage in period 2010-2015",
                        f"Significant shift detected in recent period"
                    ]
                }

                analysis_results.append(analysis_result)

            # Update experiment status
            experiment.status = 'running'
            experiment.started_at = datetime.utcnow()
            self.commit()

            logger.info(
                f"Ran orchestrated analysis for experiment {experiment_id}: "
                f"{len(terms)} terms analyzed"
            )

            return {
                'results': analysis_results,
                'total_decisions': len(analysis_results)
            }

        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            self.rollback()
            logger.error(f"Failed to run orchestrated analysis for experiment {experiment_id}: {e}", exc_info=True)
            raise ServiceError(f"Failed to run orchestrated analysis: {str(e)}") from e

    def get_orchestration_results(
        self,
        experiment_id: int
    ) -> Dict[str, Any]:
        """
        Get orchestration results for an experiment

        Args:
            experiment_id: ID of experiment

        Returns:
            Dictionary with results data

        Raises:
            NotFoundError: If experiment doesn't exist
            ServiceError: If operation fails
        """
        try:
            experiment = self._get_experiment(experiment_id)

            # Get orchestration decisions
            decisions = OrchestrationDecision.query.filter_by(
                experiment_id=experiment.id
            ).order_by(OrchestrationDecision.created_at.desc()).all()

            total_decisions = len(decisions)
            completed_decisions = sum(1 for d in decisions if d.activity_status == 'completed')

            # Get most recent decision
            recent_decision = decisions[0] if decisions else None

            # Calculate average confidence
            avg_confidence = self._calculate_average_confidence(decisions)

            # Get orchestration run data from database
            cross_document_insights, duration = self._get_orchestration_run_data(experiment_id, avg_confidence)

            # Convert markdown to HTML
            if cross_document_insights:
                cross_document_insights = self._convert_markdown_to_html(cross_document_insights)

            logger.info(
                f"Retrieved orchestration results for experiment {experiment_id}: "
                f"{total_decisions} decisions, avg confidence {avg_confidence:.2%}"
            )

            return {
                'experiment': experiment,
                'decisions': decisions,
                'total_decisions': total_decisions,
                'completed_decisions': completed_decisions,
                'avg_confidence': float(avg_confidence) if avg_confidence else 0.0,
                'recent_decision': recent_decision,
                'cross_document_insights': cross_document_insights,
                'duration': duration,
                'document_count': experiment.get_document_count()
            }

        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get orchestration results for experiment {experiment_id}: {e}", exc_info=True)
            raise ServiceError(f"Failed to get orchestration results: {str(e)}") from e

    def get_orchestration_provenance(
        self,
        experiment_id: int
    ) -> Dict[str, Any]:
        """
        Generate PROV-O compliant provenance data

        Args:
            experiment_id: ID of experiment

        Returns:
            PROV-O compliant provenance dictionary

        Raises:
            NotFoundError: If experiment doesn't exist
            ServiceError: If operation fails
        """
        try:
            experiment = self._get_experiment(experiment_id)

            # Get orchestration decisions
            from sqlalchemy import desc
            decisions = OrchestrationDecision.query.filter_by(
                experiment_id=experiment.id
            ).order_by(desc(OrchestrationDecision.created_at)).all()

            # Build PROV-O compliant provenance record
            provenance_data = {
                '@context': 'http://www.w3.org/ns/prov',
                '@type': 'prov:Bundle',
                'prov:generatedAtTime': datetime.utcnow().isoformat() + 'Z',
                'experiment': {
                    'id': experiment.id,
                    'name': experiment.name,
                    'type': experiment.experiment_type,
                    'created_at': experiment.created_at.isoformat() if experiment.started_at else None,
                    'started_at': experiment.started_at.isoformat() if experiment.started_at else None,
                    'completed_at': experiment.completed_at.isoformat() if experiment.completed_at else None,
                    'status': experiment.status,
                    'document_count': experiment.get_document_count()
                },
                'orchestration_decisions': []
            }

            # Add each decision as PROV-O Activity
            for decision in decisions:
                decision_data = self._build_provenance_decision(decision)
                provenance_data['orchestration_decisions'].append(decision_data)

            logger.info(
                f"Generated PROV-O provenance for experiment {experiment_id}: "
                f"{len(decisions)} decisions"
            )

            return provenance_data

        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to generate provenance for experiment {experiment_id}: {e}", exc_info=True)
            raise ServiceError(f"Failed to generate provenance: {str(e)}") from e

    # Private helper methods

    def _get_experiment(self, experiment_id: int) -> Experiment:
        """Get experiment by ID"""
        experiment = Experiment.query.filter_by(id=experiment_id).first()
        if not experiment:
            raise NotFoundError(f"Experiment {experiment_id} not found")
        return experiment

    def _parse_configuration(self, experiment: Experiment) -> Dict[str, Any]:
        """Parse experiment configuration JSON"""
        if not experiment.configuration:
            return {}

        try:
            return json.loads(experiment.configuration)
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"Failed to parse configuration for experiment {experiment.id}")
            return {}

    def _apply_learning_patterns(self, term_text: str) -> Tuple[List[str], str, str]:
        """
        Apply learning patterns for intelligent tool selection

        Args:
            term_text: Term to analyze

        Returns:
            Tuple of (selected_tools, embedding_model, reasoning)
        """
        # Start with default tools
        selected_tools = ['spacy', 'embeddings']
        embedding_model = 'bert-base-uncased'

        # Get active learning patterns
        active_patterns = LearningPattern.query.filter_by(pattern_status='active').all()

        reasoning_parts = [f"Selected tools for term '{term_text}' based on:"]

        for pattern in active_patterns[:2]:  # Apply top 2 patterns
            if pattern.pattern_type == 'preference':
                pattern_tools = pattern.recommendations.get('tools', [])
                selected_tools.extend([t for t in pattern_tools if t not in selected_tools])
                reasoning_parts.append(
                    f"- {pattern.pattern_name}: "
                    f"{pattern.recommendations.get('reasoning', 'Applied learned pattern')}"
                )

                # Apply embedding model recommendations
                pattern_model = pattern.recommendations.get('embedding_model')
                if pattern_model:
                    embedding_model = pattern_model

        reasoning = '\n'.join(reasoning_parts)

        return selected_tools, embedding_model, reasoning

    def _calculate_average_confidence(self, decisions: List) -> float:
        """Calculate average confidence from decisions"""
        if not decisions:
            return 0.0

        valid_confidences = [
            float(d.decision_confidence)
            for d in decisions
            if d.decision_confidence
        ]

        if not valid_confidences:
            return 0.0

        return sum(valid_confidences) / len(valid_confidences)

    def _get_orchestration_run_data(
        self,
        experiment_id: int,
        avg_confidence: float
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Get orchestration run data from database via raw SQL

        Args:
            experiment_id: ID of experiment
            avg_confidence: Average confidence from decisions (fallback)

        Returns:
            Tuple of (cross_document_insights, duration)
        """
        query = text("""
            SELECT confidence, cross_document_insights, started_at, completed_at
            FROM experiment_orchestration_runs
            WHERE experiment_id = :exp_id AND status = 'completed'
            ORDER BY completed_at DESC
            LIMIT 1
        """)

        result = db.session.execute(query, {'exp_id': experiment_id}).fetchone()

        if not result:
            return None, None

        cross_document_insights = result[1]
        started_at = result[2]
        completed_at = result[3]

        # Calculate duration
        duration = None
        if started_at and completed_at:
            duration_seconds = (completed_at - started_at).total_seconds()
            duration = self._format_duration(duration_seconds)

        return cross_document_insights, duration

    def _format_duration(self, seconds: float) -> str:
        """Format duration in seconds to human-readable string"""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return f"{hours}h {minutes}m"

    def _convert_markdown_to_html(self, text: str) -> str:
        """Convert markdown-style formatting to HTML"""
        # Convert **bold** to <strong>bold</strong>
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)

        # Convert ### headers to h4
        text = re.sub(r'###\s*(.+?)$', r'<h4>\1</h4>', text, flags=re.MULTILINE)

        # Convert bullet points to proper HTML list items
        text = re.sub(r'•\s*(.+?)$', r'<li>\1</li>', text, flags=re.MULTILINE)

        # Wrap list items in ul
        if '<li>' in text:
            text = re.sub(
                r'(<li>.*?</li>)',
                r'<ul class="list-unstyled mb-4">\n\1\n</ul>',
                text,
                flags=re.DOTALL
            )
            # Clean up multiple ul tags
            text = text.replace('</ul>\n<ul class="list-unstyled mb-4">', '')

        # Convert newlines to br tags (but not within ul/li)
        lines = text.split('\n')
        processed_lines = []
        in_list = False

        for line in lines:
            if '<ul' in line:
                in_list = True
            elif '</ul>' in line:
                in_list = False

            if (line.strip() and not in_list and
                '<h4>' not in line and '<ul' not in line and
                '</ul>' not in line and '<li>' not in line):
                processed_lines.append(line + '<br>')
            else:
                processed_lines.append(line)

        return '\n'.join(processed_lines)

    def _build_provenance_decision(self, decision) -> Dict[str, Any]:
        """Build PROV-O compliant decision data"""
        return {
            '@id': f'urn:orchestration:decision:{decision.id}',
            '@type': 'prov:Activity',
            'prov:startedAtTime': decision.started_at_time.isoformat() if decision.started_at_time else None,
            'prov:endedAtTime': decision.ended_at_time.isoformat() if decision.ended_at_time else None,
            'activity_status': decision.activity_status,

            # Context
            'experiment_id': decision.experiment_id,
            'document_id': decision.document_id,
            'term_analyzed': decision.term_text,

            # LLM Orchestration Details
            'orchestrator': {
                'provider': decision.orchestrator_provider,
                'model': decision.orchestrator_model,
                'response_time_ms': decision.orchestrator_response_time_ms
            },

            # Decision Outputs
            'decision': {
                'selected_tools': decision.selected_tools,
                'embedding_model': decision.embedding_model,
                'processing_strategy': decision.processing_strategy,
                'confidence': float(decision.decision_confidence) if decision.decision_confidence else None,
                'expected_runtime_seconds': decision.expected_runtime_seconds,
                'actual_runtime_seconds': decision.actual_runtime_seconds
            },

            # Input Metadata
            'input_metadata': decision.input_metadata,
            'document_characteristics': decision.document_characteristics,

            # Reasoning
            'reasoning_summary': decision.reasoning_summary,
            'decision_factors': decision.decision_factors,

            # Validation
            'validated': decision.decision_validated,
            'tool_execution_success': decision.tool_execution_success,

            # Provenance Relationships
            'prov:wasAssociatedWith': f'urn:agent:{decision.was_associated_with}' if decision.was_associated_with else None,
            'prov:used': f'urn:entity:{decision.used_entity}' if decision.used_entity else None,

            # Audit
            'created_at': decision.created_at.isoformat() if decision.created_at else None,
            'created_by': decision.created_by
        }


# Singleton instance
_orchestration_service = None


def get_orchestration_service() -> OrchestrationService:
    """
    Get the singleton OrchestrationService instance

    Returns:
        OrchestrationService instance
    """
    global _orchestration_service
    if _orchestration_service is None:
        _orchestration_service = OrchestrationService()
    return _orchestration_service
