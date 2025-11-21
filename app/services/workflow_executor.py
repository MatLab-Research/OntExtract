"""
Workflow Executor Service

Manages execution of the LangGraph experiment orchestration workflow.
Connects LangGraph nodes to database persistence and provides controlled
execution of the 5-stage workflow.
"""

import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from uuid import UUID

from app import db
from app.models import Experiment, Document
from app.models.term import Term, TermVersion
from app.models.experiment_orchestration_run import ExperimentOrchestrationRun
from app.orchestration.experiment_graph import get_experiment_graph
from app.orchestration.experiment_state import ExperimentOrchestrationState, create_initial_experiment_state
from app.services.extraction_tools import get_tool_registry

logger = logging.getLogger(__name__)


class WorkflowExecutor:
    """
    Executes the LangGraph experiment orchestration workflow.

    Handles:
    - Building graph state from experiments
    - Executing recommendation phase (Stages 1-2)
    - Executing processing phase (Stages 4-5)
    - Updating database with results
    - Error handling and recovery
    """

    def __init__(self):
        """Initialize the workflow executor."""
        self.graph = get_experiment_graph()

    def execute_recommendation_phase(
        self,
        run_id: UUID,
        review_choices: bool = True
    ) -> Dict[str, Any]:
        """
        Execute Stages 1-2: Analyze + Recommend

        Args:
            run_id: ExperimentOrchestrationRun ID
            review_choices: Whether to pause for user review

        Returns:
            Dictionary with recommended strategy and reasoning

        Raises:
            ValueError: If run not found or invalid state
            RuntimeError: If execution fails
        """
        try:
            # Load orchestration run
            run = ExperimentOrchestrationRun.query.get(run_id)
            if not run:
                raise ValueError(f"Orchestration run {run_id} not found")

            # Update status
            run.status = 'analyzing'
            run.current_stage = 'analyzing'
            db.session.commit()

            # Build initial state
            logger.info(f"Building state for orchestration run {run_id}")
            state = self._build_graph_state(run.experiment_id, run_id, review_choices)

            # Execute graph (Stages 1-2 only)
            logger.info(f"Executing recommendation phase for run {run_id}")
            result = asyncio.run(self._execute_graph(state))

            # Update database with results
            run.status = 'reviewing' if review_choices else 'executing'
            run.current_stage = 'reviewing' if review_choices else 'executing'
            run.experiment_goal = result.get('experiment_goal')
            run.term_context = result.get('term_context')
            run.recommended_strategy = result.get('recommended_strategy')
            run.strategy_reasoning = result.get('strategy_reasoning')
            run.confidence = result.get('confidence')
            run.strategy_approved = result.get('strategy_approved', False)

            db.session.commit()

            logger.info(
                f"Recommendation phase completed for run {run_id}. "
                f"Status: {run.status}, Confidence: {run.confidence}"
            )

            return {
                'run_id': str(run_id),
                'status': run.status,
                'experiment_goal': run.experiment_goal,
                'recommended_strategy': run.recommended_strategy,
                'strategy_reasoning': run.strategy_reasoning,
                'confidence': run.confidence,
                'awaiting_approval': review_choices
            }

        except Exception as e:
            logger.error(f"Error in recommendation phase for run {run_id}: {e}", exc_info=True)

            # Update run with error
            if run:
                run.status = 'failed'
                run.error_message = str(e)
                db.session.commit()

            raise RuntimeError(f"Recommendation phase failed: {str(e)}") from e

    def execute_processing_phase(
        self,
        run_id: UUID,
        modified_strategy: Optional[Dict[str, Any]] = None,
        review_notes: Optional[str] = None,
        reviewer_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute Stages 4-5: Execute + Synthesize

        Args:
            run_id: ExperimentOrchestrationRun ID
            modified_strategy: User-modified strategy (if any)
            review_notes: User's review notes
            reviewer_id: ID of user who reviewed

        Returns:
            Dictionary with processing results and insights

        Raises:
            ValueError: If run not found or invalid state
            RuntimeError: If execution fails
        """
        try:
            # Load orchestration run
            run = ExperimentOrchestrationRun.query.get(run_id)
            if not run:
                raise ValueError(f"Orchestration run {run_id} not found")

            # Update approval information
            if modified_strategy:
                run.modified_strategy = modified_strategy
            if review_notes:
                run.review_notes = review_notes
            if reviewer_id:
                run.reviewed_by = reviewer_id
                run.reviewed_at = datetime.utcnow()

            run.strategy_approved = True
            run.status = 'executing'
            run.current_stage = 'executing'
            db.session.commit()

            # Build state for processing
            logger.info(f"Building state for processing phase of run {run_id}")
            state = self._build_processing_state(run)

            # Execute processing nodes
            logger.info(f"Executing processing phase for run {run_id}")
            result = asyncio.run(self._execute_processing(state))

            # Update database with results
            run.status = 'completed'
            run.current_stage = 'completed'
            run.processing_results = result.get('processing_results')
            run.execution_trace = result.get('execution_trace')
            run.cross_document_insights = result.get('cross_document_insights')
            run.term_evolution_analysis = result.get('term_evolution_analysis')
            run.comparative_summary = result.get('comparative_summary')

            # Save structured card data (experiment-type specific)
            run.generated_term_cards = result.get('generated_term_cards')
            run.generated_domain_cards = result.get('generated_domain_cards')
            run.generated_entity_cards = result.get('generated_entity_cards')

            run.completed_at = datetime.utcnow()

            db.session.commit()

            logger.info(f"Processing phase completed for run {run_id}")

            return {
                'run_id': str(run_id),
                'status': 'completed',
                'processing_results': run.processing_results,
                'cross_document_insights': run.cross_document_insights,
                'term_evolution_analysis': run.term_evolution_analysis,
                'execution_time': (run.completed_at - run.started_at).total_seconds()
            }

        except Exception as e:
            logger.error(f"Error in processing phase for run {run_id}: {e}", exc_info=True)

            # Update run with error
            if run:
                run.status = 'failed'
                run.error_message = str(e)
                db.session.commit()

            raise RuntimeError(f"Processing phase failed: {str(e)}") from e

    def _build_graph_state(
        self,
        experiment_id: int,
        run_id: UUID,
        review_choices: bool
    ) -> Dict[str, Any]:
        """
        Build initial state for LangGraph execution with rich metadata.

        Queries:
        - Experiment type
        - Focus term metadata (definition, context anchors, source, domain)
        - Document bibliographic metadata (authors, year, journal, etc.)

        Args:
            experiment_id: Experiment ID
            run_id: Orchestration run ID
            review_choices: Whether to pause for review

        Returns:
            Initial state dictionary
        """
        experiment = Experiment.query.get(experiment_id)
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")

        # Get documents
        documents = Document.query.filter_by(experiment_id=experiment_id).all()

        # Build document list for graph
        doc_list = []
        document_metadata = {}

        for doc in documents:
            doc_id = str(doc.id)

            # Basic document info
            doc_list.append({
                'id': doc_id,
                'uuid': str(doc.uuid),
                'title': doc.title or 'Untitled Document',
                'content': doc.content or '',
                'metadata': {
                    'filename': doc.original_filename or '',
                    'created_at': doc.created_at.isoformat() if doc.created_at else None,
                    'document_type': doc.document_type or '',
                    'word_count': doc.word_count or 0
                }
            })

            # Enhanced bibliographic metadata for LLM prompts
            doc_meta = {
                'title': doc.title or 'Untitled Document',
            }

            if doc.authors:
                doc_meta['authors'] = doc.authors
            if doc.publication_date:
                # Extract year from publication_date
                try:
                    year = doc.publication_date.year if hasattr(doc.publication_date, 'year') else None
                    if year:
                        doc_meta['year'] = year
                except:
                    pass
            if doc.journal:
                doc_meta['journal'] = doc.journal
            if doc.publisher:
                doc_meta['publisher'] = doc.publisher
            if doc.doi:
                doc_meta['doi'] = doc.doi
            if doc.abstract:
                doc_meta['abstract'] = doc.abstract
                doc_meta['has_abstract'] = True

            # Add domain if available (could come from classification or user input)
            # For now, this might be None, but structure is ready
            # TODO: Could potentially extract from document classification

            document_metadata[doc_id] = doc_meta

        # Get focus term from experiment configuration
        focus_term = None
        focus_term_definition = None
        focus_term_context_anchors = None
        focus_term_source = None
        focus_term_domain = None

        if experiment.configuration:
            import json
            config = json.loads(experiment.configuration) if isinstance(experiment.configuration, str) else experiment.configuration
            target_terms = config.get('target_terms', [])
            if target_terms:
                focus_term = target_terms[0]

                # Query term metadata from database
                term = Term.query.filter_by(term_text=focus_term).first()
                if term:
                    focus_term_domain = term.research_domain

                    # Get the most recent term version for this term
                    term_version = TermVersion.query.filter_by(term_id=term.id)\
                        .order_by(TermVersion.generated_at_time.desc())\
                        .first()

                    if term_version:
                        focus_term_definition = term_version.meaning_description
                        focus_term_source = term_version.corpus_source

                        # Extract context anchors from JSON field
                        if term_version.context_anchor:
                            # context_anchor is stored as JSON array
                            if isinstance(term_version.context_anchor, list):
                                focus_term_context_anchors = term_version.context_anchor
                            elif isinstance(term_version.context_anchor, dict):
                                # Sometimes might be stored as dict with 'anchors' key
                                focus_term_context_anchors = term_version.context_anchor.get('anchors', [])

        # Use create_initial_experiment_state with all metadata
        state = create_initial_experiment_state(
            experiment_id=experiment_id,
            run_id=str(run_id),
            documents=doc_list,
            focus_term=focus_term,
            user_preferences={'review_choices': review_choices},
            experiment_type=experiment.experiment_type,
            focus_term_definition=focus_term_definition,
            focus_term_context_anchors=focus_term_context_anchors,
            focus_term_source=focus_term_source,
            focus_term_domain=focus_term_domain,
            document_metadata=document_metadata if document_metadata else None
        )

        return state

    def _build_processing_state(self, run: ExperimentOrchestrationRun) -> Dict[str, Any]:
        """
        Build state for processing phase from existing run.

        Re-uses the metadata-rich state building from recommendation phase,
        then overlays the recommendation results.

        Args:
            run: ExperimentOrchestrationRun with completed recommendation phase

        Returns:
            State dictionary ready for processing
        """
        # Build full state with metadata (same as recommendation phase)
        state = self._build_graph_state(run.experiment_id, run.id, False)

        # Overlay existing recommendation results
        state['current_stage'] = 'executing'
        state['experiment_goal'] = run.experiment_goal
        state['term_context'] = run.term_context
        state['recommended_strategy'] = run.recommended_strategy
        state['strategy_reasoning'] = run.strategy_reasoning
        state['confidence'] = run.confidence
        state['strategy_approved'] = True
        state['modified_strategy'] = run.modified_strategy
        state['review_notes'] = run.review_notes

        return state

    async def _execute_graph(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the LangGraph (Stages 1-2 only).

        Args:
            state: Initial state

        Returns:
            Updated state after execution
        """
        result = await self.graph.ainvoke(state)
        return result

    async def _execute_processing(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute processing nodes (Stages 4-5).

        Args:
            state: State with approved strategy

        Returns:
            Updated state with results
        """
        # Import nodes
        from app.orchestration.experiment_nodes import (
            execute_strategy_node,
            synthesize_experiment_node
        )

        # Execute Stage 4 and merge results
        stage4_results = await execute_strategy_node(state)
        state.update(stage4_results)

        # Execute Stage 5 and merge results
        stage5_results = await synthesize_experiment_node(state)
        state.update(stage5_results)

        return state


# Singleton instance
_workflow_executor = None


def get_workflow_executor() -> WorkflowExecutor:
    """
    Get or create the workflow executor singleton.

    Returns:
        WorkflowExecutor instance
    """
    global _workflow_executor
    if _workflow_executor is None:
        _workflow_executor = WorkflowExecutor()
    return _workflow_executor
