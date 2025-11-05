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

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from .experiment_state import ExperimentOrchestrationState
from ..services.extraction_tools import get_tool_registry


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

    This node examines the experiment's documents and focus term to determine
    what the researcher is trying to achieve. For term evolution tracking,
    it identifies why the term matters.

    Returns:
        - experiment_goal: Clear statement of experiment purpose
        - term_context: Why the focus term is significant (if present)
        - current_stage: Updated to "recommending"
    """
    claude_client = get_claude_client()

    focus_term = state.get('focus_term')
    documents = state['documents']

    # Build document summary
    doc_summary = "\n".join([
        f"- Document {i+1}: {doc['title']} ({len(doc.get('content', ''))} characters)"
        for i, doc in enumerate(documents)
    ])

    term_context_text = f"""
Focus Term: "{focus_term}"

This experiment tracks the semantic evolution of this term across the document set.
""" if focus_term else "No specific term focus - general document analysis."

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are analyzing a research experiment to understand its goals.

Your task:
1. What is this experiment trying to discover?
2. What makes this document collection interesting to analyze together?
3. If a focus term is provided, why might researchers care about tracking it?
4. What kinds of insights would be most valuable?

Provide a clear, 2-3 sentence summary of the experiment's purpose."""),

        ("user", f"""Experiment Analysis:

{term_context_text}

Documents in Experiment:
{doc_summary}

Number of documents: {len(documents)}

What is the goal of this experiment? What insights should we aim to extract?""")
    ])

    chain = prompt | claude_client
    response = await chain.ainvoke({})

    return {
        "experiment_goal": response.content,
        "term_context": focus_term,
        "current_stage": "recommending"
    }


async def recommend_strategy_node(state: ExperimentOrchestrationState) -> Dict[str, Any]:
    """
    Stage 2: Recommend processing tools for each document.

    The LLM analyzes all documents together and recommends a coherent
    processing strategy tailored to the experiment's goals. For term evolution
    tracking, it prioritizes tools that reveal semantic context.

    Returns:
        - recommended_strategy: {doc_id: [tool_names]}
        - strategy_reasoning: Why this approach was chosen
        - confidence: 0.0-1.0 confidence score
        - current_stage: "reviewing" or "executing" (based on user_preferences)
    """
    claude_client = get_claude_client()

    experiment_goal = state['experiment_goal']
    focus_term = state.get('focus_term')
    documents = state['documents']

    # Get available tools from registry
    from app.services.tool_registry import get_tool_descriptions
    available_tools = get_tool_descriptions()

    # Build document descriptions (include first 500 chars for context)
    doc_descriptions = "\n\n".join([
        f"""Document {i+1}: {doc['title']}
- ID: {doc['id']}
- Length: {len(doc.get('content', ''))} characters
- Metadata: {str(doc.get('metadata', {})).replace('{', '{{').replace('}', '}}')}
- Preview: {doc.get('content', '')[:500]}..."""
        for i, doc in enumerate(documents)
    ])

    term_guidance = f"""
IMPORTANT: The experiment focuses on tracking the term "{focus_term}".

For semantic evolution analysis:
- Prioritize entity extraction (reveals what co-occurs with the term)
- Include temporal extraction (tracks usage across time periods)
- Consider definitions (shows how term is explicitly defined)
- Embeddings can capture semantic shifts

Recommend tools that help answer: "How does the meaning/context of '{focus_term}' change across these documents?"
""" if focus_term else ""

    prompt = ChatPromptTemplate.from_messages([
        ("system", f"""You are an expert NLP orchestration system.

{available_tools}

Your task:
1. Analyze each document in the context of the experiment goal
2. Recommend 2-4 tools per document that will best serve the experiment
3. Ensure the strategy is coherent across all documents
4. If a focus term exists, prioritize tools for semantic evolution analysis

{term_guidance}

Respond in JSON format:
{{{{
    "strategy": {{{{
        "<document_id_1>": ["tool1", "tool2"],
        "<document_id_2>": ["tool1", "tool3"]
    }}}},
    "reasoning": "Why this strategy serves the experiment goal...",
    "confidence": 0.85
}}}}"""),

        ("user", f"""Experiment Goal:
{experiment_goal}

Documents to Process:
{doc_descriptions}

Recommend a processing strategy for each document that serves the experiment goal.""")
    ])

    chain = prompt | claude_client | JsonOutputParser()
    response = await chain.ainvoke({})

    # Determine next stage based on user preferences
    review_choices = state['user_preferences'].get('review_choices', False)
    next_stage = "reviewing" if review_choices else "executing"

    return {
        "recommended_strategy": response['strategy'],
        "strategy_reasoning": response['reasoning'],
        "confidence": response['confidence'],
        "current_stage": next_stage,
        "strategy_approved": not review_choices  # Auto-approve if no review
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

    async def process_document(doc: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
        """Process a single document with its recommended tools."""
        doc_id = doc['id']
        tool_names = strategy.get(doc_id, [])
        doc_content = doc.get('content', '')

        results = {}

        for tool_name in tool_names:
            tool = tool_registry.get(tool_name)
            if tool:
                try:
                    # Execute tool
                    result = await tool.execute(doc_content)
                    results[tool_name] = result

                    # Track execution
                    execution_trace.append({
                        "run_id": run_id,
                        "document_id": doc_id,
                        "tool": tool_name,
                        "timestamp": datetime.utcnow().isoformat(),
                        "status": "success"
                    })

                except Exception as e:
                    # Log failure
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

    For term evolution experiments, this focuses on how the term's semantic
    context changes across documents. For general experiments, it identifies
    common themes and differences.

    Returns:
        - cross_document_insights: Main insights
        - term_evolution_analysis: Term-specific analysis (if applicable)
        - comparative_summary: High-level summary
        - current_stage: "completed"
    """
    claude_client = get_claude_client()

    focus_term = state.get('focus_term')
    processing_results = state['processing_results']
    documents = state['documents']
    experiment_goal = state['experiment_goal']

    # Build results summary
    results_summary = []
    for doc in documents:
        doc_id = doc['id']
        doc_results = processing_results.get(doc_id, {})

        # Extract entities if available
        entities = []
        if 'extract_entities_spacy' in doc_results:
            entity_data = doc_results['extract_entities_spacy']
            if isinstance(entity_data, dict):
                entities = [e.get('text', str(e)) for e in entity_data.get('entities', [])]

        # Extract temporal info if available
        temporal_info = ""
        if 'extract_temporal' in doc_results:
            temporal_data = doc_results['extract_temporal']
            if isinstance(temporal_data, dict):
                temporal_info = f"Temporal expressions: {len(temporal_data.get('expressions', []))}"

        results_summary.append(f"""
Document: {doc['title']}
- ID: {doc_id}
- Entities found: {', '.join(entities[:15])}{'...' if len(entities) > 15 else ''}
- {temporal_info}
- Tools applied: {', '.join(doc_results.keys())}
""")

    results_text = "\n".join(results_summary)

    if focus_term:
        # Term evolution analysis
        prompt = ChatPromptTemplate.from_messages([
            ("system", f"""You are analyzing semantic evolution across multiple documents.

This experiment focuses on the term: "{focus_term}"

Your task:
1. How does "{focus_term}" appear in each document's context?
2. What entities/concepts co-occur with "{focus_term}" in each document?
3. How does the semantic field around "{focus_term}" change across documents?
4. What does this reveal about the term's evolution or usage patterns?

Provide:
- Per-document analysis (2-3 sentences each)
- Cross-document comparison (3-4 sentences)
- Key insights about semantic evolution (4-6 bullet points)"""),

            ("user", f"""Experiment Goal: {experiment_goal}

Focus Term: "{focus_term}"

Processing Results:
{results_text}

Analyze the semantic evolution of "{focus_term}" across these documents.""")
        ])

        chain = prompt | claude_client
        response = await chain.ainvoke({})

        return {
            "cross_document_insights": response.content,
            "term_evolution_analysis": response.content,
            "comparative_summary": f"Semantic evolution analysis of '{focus_term}' across {len(documents)} documents",
            "current_stage": "completed"
        }

    else:
        # General cross-document synthesis
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are synthesizing insights from multiple document analyses.

Your task:
1. What common themes emerge across documents?
2. What differences are most significant?
3. What insights does analyzing these documents together reveal?
4. What patterns or trends are observable?

Provide a comprehensive synthesis (5-8 sentences) with 3-5 key bullet points."""),

            ("user", f"""Experiment Goal: {experiment_goal}

Processing Results:
{results_text}

Synthesize insights across these documents.""")
        ])

        chain = prompt | claude_client
        response = await chain.ainvoke({})

        return {
            "cross_document_insights": response.content,
            "comparative_summary": f"Cross-document analysis across {len(documents)} documents",
            "current_stage": "completed"
        }
