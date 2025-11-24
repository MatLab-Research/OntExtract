"""
LangGraph nodes for experiment-level orchestration.

These nodes implement the 5-stage workflow:
1. Analyze Experiment - Understand goals and context
2. Recommend Strategy - Suggest processing tools per document
3. Human Review - Optional approval/modification (conditional)
4. Execute Strategy - Process all documents with chosen tools
5. Synthesize Experiment - Generate cross-document insights
"""

from typing import Dict, Any, List
from datetime import datetime
import asyncio
import os
import logging

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import JsonOutputParser

from .experiment_state import ExperimentOrchestrationState
from ..services.extraction_tools import get_tool_registry
from .retry_utils import call_llm_with_retry, LLMTimeoutError, LLMRetryExhaustedError
from .config import config
from .prompts import get_analyze_prompt, get_recommend_strategy_prompt, get_synthesis_prompt

# Database imports for progress tracking
from app import db
from app.models.experiment_orchestration_run import ExperimentOrchestrationRun

logger = logging.getLogger(__name__)


# Lazy initialization of Claude client
_claude_client = None


def get_claude_client():
    """Get or create Claude client (lazy initialization)."""
    global _claude_client
    if _claude_client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")

        _claude_client = ChatAnthropic(
            model="claude-sonnet-4-20250514",
            api_key=api_key,
            temperature=0.2,
            max_tokens=4096
        )
    return _claude_client


async def analyze_experiment_node(state: ExperimentOrchestrationState) -> Dict[str, Any]:
    """
    Stage 1: Analyze the experiment to understand its goals.

    Uses experiment-type-specific prompts with rich metadata including:
    - Term definitions and context anchors
    - Document bibliographic metadata
    - Experiment type and domain

    Returns:
        - experiment_goal: Clear statement of experiment purpose
        - term_context: Why the focus term is significant (if present)
        - current_stage: Updated to "recommending"
    """
    claude_client = get_claude_client()

    # Extract metadata from state
    experiment_type = state.get('experiment_type', 'entity_extraction')
    focus_term = state.get('focus_term')
    focus_term_definition = state.get('focus_term_definition')
    focus_term_context_anchors = state.get('focus_term_context_anchors')
    focus_term_source = state.get('focus_term_source')
    focus_term_domain = state.get('focus_term_domain')
    documents = state['documents']
    document_metadata = state.get('document_metadata')

    # Generate experiment-type-specific prompt with metadata
    prompt_text = get_analyze_prompt(
        experiment_type=experiment_type,
        focus_term=focus_term,
        focus_term_definition=focus_term_definition,
        focus_term_context_anchors=focus_term_context_anchors,
        focus_term_source=focus_term_source,
        focus_term_domain=focus_term_domain,
        documents=documents,
        document_metadata=document_metadata
    )

    # Use JSON output parser for structured response
    json_parser = JsonOutputParser()
    chain = claude_client | json_parser

    # Execute LLM call with timeout and retry
    try:
        response = await call_llm_with_retry(
            coro_factory=lambda: chain.ainvoke([HumanMessage(content=prompt_text)]),
            operation_name="Analyze Experiment (Stage 1)"
        )

        # Extract fields from JSON response
        experiment_goal = response.get('experiment_goal', 'Analyze document collection')
        term_context = response.get('term_context', focus_term)

        logger.info(f"Stage 1 complete: Goal={experiment_goal[:50]}...")

        return {
            "experiment_goal": experiment_goal,
            "term_context": term_context,
            "current_stage": "recommending"
        }

    except (LLMTimeoutError, LLMRetryExhaustedError) as e:
        logger.error(f"Failed to analyze experiment: {e}")
        return {
            "experiment_goal": None,
            "term_context": focus_term,
            "current_stage": "failed",
            "error_message": f"LLM analysis failed: {str(e)}"
        }


async def recommend_strategy_node(state: ExperimentOrchestrationState) -> Dict[str, Any]:
    """
    Stage 2: Recommend processing tools for each document.

    Uses experiment-type-specific prompts with:
    - Term metadata (definition, anchors) for semantic guidance
    - Document metadata for context-aware recommendations
    - Type-specific tool prioritization

    Returns:
        - recommended_strategy: {doc_id: [tool_names]}
        - strategy_reasoning: Why this approach was chosen
        - confidence: 0.0-1.0 confidence score
        - current_stage: "reviewing" or "executing" (based on user_preferences)
    """
    claude_client = get_claude_client()

    # Extract metadata from state
    experiment_type = state.get('experiment_type', 'entity_extraction')
    experiment_goal = state['experiment_goal']
    term_context = state.get('term_context')
    focus_term = state.get('focus_term')
    focus_term_definition = state.get('focus_term_definition')
    focus_term_context_anchors = state.get('focus_term_context_anchors')
    documents = state['documents']
    document_metadata = state.get('document_metadata')

    # Get available tools from registry
    from app.services.tool_registry import get_available_tools
    available_tools_dict = get_available_tools(include_stubs=True)

    # Build list of tool names and descriptions dictionary
    available_tools = list(available_tools_dict.keys())
    tool_descriptions = {
        name: tool.description
        for name, tool in available_tools_dict.items()
    }

    # Generate experiment-type-specific prompt with metadata
    prompt_text = get_recommend_strategy_prompt(
        experiment_type=experiment_type,
        experiment_goal=experiment_goal,
        term_context=term_context,
        focus_term=focus_term,
        focus_term_definition=focus_term_definition,
        focus_term_context_anchors=focus_term_context_anchors,
        documents=documents,
        document_metadata=document_metadata,
        available_tools=available_tools,
        tool_descriptions=tool_descriptions
    )

    chain = claude_client | JsonOutputParser()

    # Execute LLM call with timeout and retry
    try:
        response = await call_llm_with_retry(
            coro_factory=lambda: chain.ainvoke([HumanMessage(content=prompt_text)]),
            operation_name="Recommend Strategy (Stage 2)"
        )

        # Determine next stage based on user preferences
        review_choices = state['user_preferences'].get('review_choices', False)
        next_stage = "reviewing" if review_choices else "executing"

        logger.info(f"Stage 2 complete: {len(response.get('recommended_strategy', {}))} docs, confidence={response.get('confidence', 0)}")

        return {
            "recommended_strategy": response.get('recommended_strategy'),
            "strategy_reasoning": response.get('strategy_reasoning'),
            "confidence": response.get('confidence', 0.0),
            "current_stage": next_stage,
            "strategy_approved": not review_choices  # Auto-approve if no review
        }

    except (LLMTimeoutError, LLMRetryExhaustedError) as e:
        logger.error(f"Failed to recommend strategy: {e}")
        return {
            "recommended_strategy": None,
            "strategy_reasoning": None,
            "confidence": 0.0,
            "current_stage": "failed",
            "error_message": f"Strategy recommendation failed: {str(e)}"
        }


async def human_review_node(state: ExperimentOrchestrationState) -> Dict[str, Any]:
    """
    Stage 3: Wait for human approval/modification of strategy.

    This node is only reached if review_choices=True. It stores the current
    state and waits for the user to review the strategy via the UI.

    The graph execution pauses here. A separate Flask endpoint will update
    the state and resume execution after user approval.

    Returns:
        - current_stage: "waiting_for_review"
    """
    # In practice, this node doesn't do much - it's a placeholder for the
    # UI review workflow. The actual approval happens via a Flask callback.

    return {
        "current_stage": "waiting_for_review"
    }


def update_current_operation(run_id: str, operation_text: str):
    """
    Update current_operation field in database for progress tracking.

    Minimal overhead - just one UPDATE query.
    """
    try:
        run = ExperimentOrchestrationRun.query.filter_by(id=run_id).first()
        if run:
            run.current_operation = operation_text
            db.session.commit()
    except Exception as e:
        logger.error(f"Error updating current_operation: {e}")
        # Don't fail execution if progress update fails
        db.session.rollback()


async def execute_strategy_node(state: ExperimentOrchestrationState) -> Dict[str, Any]:
    """
    Stage 4: Execute the approved processing strategy.

    Processes all documents in parallel using the recommended (or modified)
    tools. Tracks execution provenance for PROV-O compliance.

    Returns:
        - processing_results: {doc_id: {tool: result, ...}}
        - execution_trace: List of execution events
        - current_stage: "synthesizing"
    """
    strategy = state.get('modified_strategy') or state['recommended_strategy']
    documents = state['documents']
    run_id = state['run_id']

    processing_results = {}
    execution_trace = []

    # Get tool registry
    tool_registry = get_tool_registry()

    # Calculate total operations for progress tracking
    total_tools = sum(len(tools) for tools in strategy.values())
    completed_tools = 0

    async def process_document(doc: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
        """Process a single document with its recommended tools."""
        nonlocal completed_tools

        doc_id = doc['id']
        tool_names = strategy.get(doc_id, [])
        doc_content = doc.get('content', '')

        results = {}

        for tool_name in tool_names:
            tool = tool_registry.get(tool_name)
            if tool:
                try:
                    # Update progress in database
                    update_current_operation(
                        run_id,
                        f"Processing document {doc_id} with {tool_name} ({completed_tools + 1}/{total_tools} operations)"
                    )

                    logger.info(f"[Run {run_id}] Processing doc {doc_id} with tool {tool_name}")

                    # Execute tool with 60 second timeout
                    result = await asyncio.wait_for(
                        tool.execute(doc_content),
                        timeout=60.0
                    )
                    results[tool_name] = result

                    logger.info(f"[Run {run_id}] Successfully executed {tool_name} on doc {doc_id}")

                    # Increment completed counter
                    completed_tools += 1

                    # Track execution
                    execution_trace.append({
                        "run_id": run_id,
                        "document_id": doc_id,
                        "tool": tool_name,
                        "timestamp": datetime.utcnow().isoformat(),
                        "status": "success"
                    })

                except asyncio.TimeoutError:
                    # Tool execution timed out
                    logger.warning(f"[Run {run_id}] Timeout executing {tool_name} on doc {doc_id}")
                    execution_trace.append({
                        "run_id": run_id,
                        "document_id": doc_id,
                        "tool": tool_name,
                        "timestamp": datetime.utcnow().isoformat(),
                        "status": "timeout",
                        "error": "Tool execution exceeded 60 second timeout"
                    })
                    results[tool_name] = {
                        "status": "error",
                        "error": "Execution timeout",
                        "tool": tool_name
                    }

                except Exception as e:
                    # Log failure
                    logger.error(f"[Run {run_id}] Error executing {tool_name} on doc {doc_id}: {e}", exc_info=True)
                    execution_trace.append({
                        "run_id": run_id,
                        "document_id": doc_id,
                        "tool": tool_name,
                        "timestamp": datetime.utcnow().isoformat(),
                        "status": "failed",
                        "error": str(e)
                    })

        return doc_id, results

    # Execute all documents in parallel
    tasks = [process_document(doc) for doc in documents]
    results_list = await asyncio.gather(*tasks)

    # Collect results
    for doc_id, results in results_list:
        processing_results[doc_id] = results

    return {
        "processing_results": processing_results,
        "execution_trace": execution_trace,
        "current_stage": "synthesizing"
    }


async def synthesize_experiment_node(state: ExperimentOrchestrationState) -> Dict[str, Any]:
    """
    Stage 5: Synthesize insights across all documents.

    Uses experiment-type-specific prompts with metadata.
    For temporal_evolution experiments, generates structured term cards for visualization.

    Returns:
        - cross_document_insights: Main insights (markdown)
        - term_evolution_analysis: Term-specific analysis (if applicable)
        - generated_term_cards: Structured card data (for temporal_evolution)
        - generated_domain_cards: Structured card data (for domain_comparison)
        - generated_entity_cards: Structured card data (for entity_extraction)
        - current_stage: "completed"
    """
    claude_client = get_claude_client()

    # Extract metadata from state
    experiment_type = state.get('experiment_type', 'entity_extraction')
    experiment_goal = state['experiment_goal']
    focus_term = state.get('focus_term')
    focus_term_definition = state.get('focus_term_definition')
    focus_term_context_anchors = state.get('focus_term_context_anchors')
    processing_results = state['processing_results']
    documents = state['documents']
    document_metadata = state.get('document_metadata')

    # Generate experiment-type-specific synthesis prompt with metadata
    prompt_text = get_synthesis_prompt(
        experiment_type=experiment_type,
        experiment_goal=experiment_goal,
        focus_term=focus_term,
        focus_term_definition=focus_term_definition,
        focus_term_context_anchors=focus_term_context_anchors,
        processing_results=processing_results,
        document_metadata=document_metadata
    )

    # Use JSON parser to get structured response
    chain = claude_client | JsonOutputParser()

    # Execute LLM call with timeout and retry
    try:
        response = await call_llm_with_retry(
            coro_factory=lambda: chain.ainvoke([HumanMessage(content=prompt_text)]),
            operation_name="Synthesize Experiment (Stage 5)"
        )

        # Extract common fields
        cross_document_insights = response.get('cross_document_insights', 'No insights generated')
        term_evolution_analysis = response.get('term_evolution_analysis')

        # Extract structured card data (experiment-type specific)
        generated_term_cards = response.get('generated_term_cards')
        generated_domain_cards = response.get('generated_domain_cards')
        generated_entity_cards = response.get('generated_entity_cards')

        # Log card generation success
        if generated_term_cards:
            logger.info(f"Stage 5 complete: Generated {len(generated_term_cards)} term cards for temporal_evolution")
        elif generated_domain_cards:
            logger.info(f"Stage 5 complete: Generated {len(generated_domain_cards)} domain cards")
        elif generated_entity_cards:
            logger.info(f"Stage 5 complete: Generated {len(generated_entity_cards)} entity cards")
        else:
            logger.info("Stage 5 complete: Text insights only (no structured cards)")

        return {
            "cross_document_insights": cross_document_insights,
            "term_evolution_analysis": term_evolution_analysis,
            "generated_term_cards": generated_term_cards,
            "generated_domain_cards": generated_domain_cards,
            "generated_entity_cards": generated_entity_cards,
            "current_stage": "completed"
        }

    except (LLMTimeoutError, LLMRetryExhaustedError) as e:
        logger.error(f"Failed to synthesize: {e}")
        return {
            "cross_document_insights": f"Synthesis failed: {str(e)}",
            "term_evolution_analysis": None,
            "generated_term_cards": None,
            "generated_domain_cards": None,
            "generated_entity_cards": None,
            "current_stage": "failed",
            "error_message": f"Synthesis failed: {str(e)}"
        }
