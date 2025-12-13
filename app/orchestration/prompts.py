"""
Experiment-type-specific prompts for LLM orchestration.

This module generates customized prompts based on experiment type, incorporating
metadata such as term definitions, context anchors, and document bibliographic info.
"""

from typing import Dict, List, Any, Optional
import json


# Style guidelines for all LLM-generated text to avoid artificial-sounding output
LLM_STYLE_GUIDELINES = """
**Writing Style Requirements** (follow strictly):

PUNCTUATION AND STRUCTURE:
- No em dashes or colons in body text
- Put main clause first (avoid front-loaded subordinate clauses)
- Avoid starting sentences with "-ing" words
- Prefer prose over bullet lists in descriptive sections

WORD CHOICE:
- NEVER use: seamless, nuanced, robust, intriguing, comprehensive, systematic, crucial, key, critical, vital
- NEVER use enthusiasm or sales language: remarkable, striking, dramatic, revolutionary, groundbreaking, transformative
- Use measured language: observed, found, identified, present, absent, noted, recorded, frequent, common

POSSESSIVES:
- People's names CAN use possessives: "Wooldridge's definition", "Anscombe's analysis"
- Inanimate objects should NOT: "the system's output" becomes "output of the system"

LISTS:
- Avoid the three-item pattern (X, Y, and Z) which signals AI text
- Vary item counts or restructure to avoid listing
- Use alternatives: "X and Y, as well as Z" or "X along with Y and Z"

NEGATIVE CONSTRUCTIONS:
- State what something does directly
- Avoid "rather than", "instead of" unless contrast is essential
"""


def summarize_processing_results(processing_results: Dict[str, Any], max_items_per_tool: int = 50) -> Dict[str, Any]:
    """
    Summarize processing results to avoid token limits while preserving analytical value.

    Strategy:
    - Send ALL unique items for structured data (entities, dates, definitions)
    - Skip raw text and embeddings (too large, not useful for synthesis)
    - Include frequency/count metadata for pattern analysis

    The goal is to provide enough structured data for LLM to identify patterns,
    trends, and insights that wouldn't be visible from documents alone.

    Args:
        processing_results: Raw processing results {doc_id: {tool: result, ...}}
        max_items_per_tool: Maximum number of items per tool (default 50 for meaningful analysis)

    Returns:
        Summarized results suitable for LLM synthesis
    """
    summarized = {}

    for doc_id, tools_results in processing_results.items():
        doc_summary = {}

        for tool_name, result in tools_results.items():
            if isinstance(result, dict):
                tool_summary = {}

                # Handle common result patterns
                if 'entities' in result and isinstance(result['entities'], list):
                    # Entity extraction results
                    entities = result['entities']
                    tool_summary['count'] = len(entities)
                    tool_summary['top_entities'] = entities[:max_items_per_tool]
                    if len(entities) > max_items_per_tool:
                        tool_summary['truncated'] = True

                elif 'dates' in result and isinstance(result['dates'], list):
                    # Temporal extraction results
                    dates = result['dates']
                    tool_summary['count'] = len(dates)
                    tool_summary['dates'] = dates[:max_items_per_tool]
                    if len(dates) > max_items_per_tool:
                        tool_summary['truncated'] = True

                elif 'definitions' in result and isinstance(result['definitions'], list):
                    # Definition extraction results
                    definitions = result['definitions']
                    tool_summary['count'] = len(definitions)
                    tool_summary['definitions'] = definitions[:max_items_per_tool]
                    if len(definitions) > max_items_per_tool:
                        tool_summary['truncated'] = True

                elif 'embeddings' in result:
                    # Skip embeddings entirely (too large, not useful for synthesis)
                    tool_summary['embedding_dimensions'] = len(result.get('embeddings', []))
                    tool_summary['note'] = 'Embeddings computed but excluded from summary'

                else:
                    # Generic handling: keep small dicts, summarize large ones
                    result_str = json.dumps(result)
                    if len(result_str) < 1000:
                        tool_summary = result
                    else:
                        tool_summary['summary'] = f'Large result ({len(result_str)} chars), {len(result)} keys'
                        # Keep numeric/small values
                        for k, v in result.items():
                            if isinstance(v, (int, float, bool)) or (isinstance(v, str) and len(v) < 100):
                                tool_summary[k] = v

                doc_summary[tool_name] = tool_summary

            elif isinstance(result, list):
                # List of items - take top N
                doc_summary[tool_name] = {
                    'count': len(result),
                    'items': result[:max_items_per_tool],
                    'truncated': len(result) > max_items_per_tool
                }

            elif isinstance(result, (int, float, str, bool)):
                # Simple values - keep as-is
                doc_summary[tool_name] = result

            else:
                doc_summary[tool_name] = {'type': str(type(result)), 'note': 'Complex result type'}

        summarized[doc_id] = doc_summary

    return summarized


def get_analyze_prompt(
    experiment_type: str,
    focus_term: Optional[str],
    focus_term_definition: Optional[str],
    focus_term_context_anchors: Optional[List[str]],
    focus_term_source: Optional[str],
    focus_term_domain: Optional[str],
    documents: List[Dict[str, Any]],
    document_metadata: Optional[Dict[str, Dict[str, Any]]]
) -> str:
    """
    Generate Stage 1 (Analyze) prompt customized by experiment type.

    Args:
        experiment_type: Type of experiment (temporal_evolution, domain_comparison, entity_extraction)
        focus_term: The term being analyzed (if any)
        focus_term_definition: Dictionary definition of the term
        focus_term_context_anchors: Related semantic terms (stop-word filtered)
        focus_term_source: Source of definition (OED, MW, WordNet)
        focus_term_domain: Research domain/discipline
        documents: List of documents with metadata
        document_metadata: Structured bibliographic info per document

    Returns:
        Formatted prompt string
    """

    # Build term context section
    term_section = ""
    if focus_term:
        term_section = f'\n## Focus Term: "{focus_term}"\n\n'

        if focus_term_definition:
            term_section += f"**Baseline Definition** (from {focus_term_source or 'dictionary'}):\n"
            term_section += f"{focus_term_definition}\n\n"

        if focus_term_context_anchors:
            term_section += "**Context Anchors** (semantically related terms):\n"
            term_section += ", ".join(focus_term_context_anchors) + "\n\n"
            term_section += "These anchors represent core semantic components of the term's meaning.\n\n"

        if focus_term_domain:
            term_section += f"**Research Domain**: {focus_term_domain}\n\n"

    # Build document summary with enhanced metadata
    doc_summary_lines = []
    for i, doc in enumerate(documents):
        doc_id = str(doc.get('id', i+1))
        title = doc.get('title', f'Document {i+1}')

        meta_str = ""
        if document_metadata and doc_id in document_metadata:
            meta = document_metadata[doc_id]
            parts = []
            if meta.get('authors'):
                parts.append(f"Authors: {meta['authors']}")
            if meta.get('year'):
                parts.append(f"Year: {meta['year']}")
            if meta.get('journal'):
                parts.append(f"Journal: {meta['journal']}")
            if meta.get('domain'):
                parts.append(f"Domain: {meta['domain']}")
            if parts:
                meta_str = " | " + " | ".join(parts)

        doc_summary_lines.append(f"- Document {doc_id}: {title}{meta_str}")

    doc_summary = "\n".join(doc_summary_lines)

    # Experiment-type-specific instructions
    type_specific_instructions = {
        'temporal_evolution': """
**Experiment Type: Temporal Evolution**

Focus on:
1. How the term's usage has evolved across different time periods
2. Which context anchors are present or absent in different eras
3. Semantic drift from the baseline definition
4. Historical changes in meaning and application
""",
        'domain_comparison': """
**Experiment Type: Domain Comparison**

Focus on:
1. How the term's meaning varies across different research domains
2. Which context anchors are universal vs. domain-specific
3. Semantic shifts when crossing disciplinary boundaries
4. Specialized usage patterns in each field
""",
        'entity_extraction': """
**Experiment Type: Entity Extraction**

Focus on:
1. Entities, concepts, and relationships in the documents
2. How entities relate to the focus term (if present)
3. Patterns in entity usage and co-occurrence
4. Hierarchical or categorical relationships
"""
    }

    instructions = type_specific_instructions.get(experiment_type, """
**General Document Analysis**

Focus on:
1. Main themes and topics across documents
2. Primary concepts and terminology
3. Document characteristics and content patterns
""")

    # Build the complete prompt
    prompt = f"""You are analyzing an experiment to understand its research goals.

{term_section}
## Documents in Experiment

{doc_summary}

{instructions}

Based on the term definition, context anchors, and documents above, provide a clear analysis:

1. **Experiment Goal**: What is the researcher trying to discover or understand?
2. **Term Context**: Why does the focus term matter for this analysis? How might it be used differently across documents?
3. **Considerations**: What aspects of the term's meaning or usage should be tracked?

Return your analysis as a JSON object with these fields:
- experiment_goal: String describing the research objective
- term_context: String explaining the term's significance (if applicable)
"""

    return prompt


def get_recommend_strategy_prompt(
    experiment_type: str,
    experiment_goal: str,
    term_context: Optional[str],
    focus_term: Optional[str],
    focus_term_definition: Optional[str],
    focus_term_context_anchors: Optional[List[str]],
    documents: List[Dict[str, Any]],
    document_metadata: Optional[Dict[str, Dict[str, Any]]],
    available_tools: List[str],
    tool_descriptions: Dict[str, str]
) -> str:
    """
    Generate Stage 2 (Recommend Strategy) prompt customized by experiment type.

    Returns:
        Formatted prompt string
    """

    # Build term reference section
    term_ref = ""
    if focus_term and focus_term_definition:
        term_ref = f"""
## Term Reference: "{focus_term}"

**Baseline Meaning**: {focus_term_definition}

**Semantic Anchors**: {", ".join(focus_term_context_anchors) if focus_term_context_anchors else "N/A"}
"""

    # Experiment-type-specific tool prioritization
    # NOTE: Tool names must match those in tool_registry.py
    tool_priorities = {
        'temporal_evolution': {
            'high': ['extract_temporal', 'period_aware_embedding', 'extract_definitions'],
            'rationale': 'Temporal experiments benefit from date extraction, period-aware embeddings, and definition extraction to track meaning evolution over time.'
        },
        'domain_comparison': {
            'high': ['extract_entities_spacy', 'extract_definitions', 'period_aware_embedding'],
            'rationale': 'Domain comparison requires entity extraction, definition extraction, and embeddings to identify usage patterns across fields.'
        },
        'entity_extraction': {
            'high': ['extract_entities_spacy', 'extract_definitions'],
            'rationale': 'Entity extraction experiments need NER and definition extraction tools.'
        }
    }

    priority_info = tool_priorities.get(experiment_type, {
        'high': [],
        'rationale': 'General analysis benefits from a balanced mix of tools.'
    })

    # Build document list with metadata
    doc_list = []
    for i, doc in enumerate(documents):
        doc_id = str(doc.get('id', i+1))
        title = doc.get('title', f'Document {i+1}')

        meta_info = {}
        if document_metadata and doc_id in document_metadata:
            meta = document_metadata[doc_id]
            if meta.get('year'):
                meta_info['year'] = meta['year']
            if meta.get('domain'):
                meta_info['domain'] = meta['domain']
            if meta.get('has_abstract'):
                meta_info['has_abstract'] = True

        doc_list.append({
            'id': doc_id,
            'title': title,
            'metadata': meta_info
        })

    # Build tools list
    tools_section = "\n".join([
        f"- {tool}: {tool_descriptions.get(tool, 'No description')}"
        for tool in available_tools
    ])

    prompt = f"""You are recommending a processing strategy for this experiment.

## Experiment Goal
{experiment_goal}

{term_ref}

## Experiment Type: {experiment_type}

**Prioritized Tools for this type**: {", ".join(priority_info['high']) if priority_info['high'] else "No specific priority"}
**Rationale**: {priority_info['rationale']}

## Documents
{json.dumps(doc_list, indent=2).replace('{', '{{').replace('}', '}}')}

## Available Processing Tools
{tools_section}

Based on the experiment goal, term context, and document characteristics, recommend which tools to apply to each document.

**Strategy Guidelines**:
- Consider the experiment type and prioritized tools
- Use document metadata (year, domain) to guide tool selection
- For temporal evolution: emphasize temporal extraction and semantic tracking
- For domain comparison: focus on entity extraction and semantic comparison
- Select 2-4 tools per document (avoid over-processing)
- Explain your reasoning

Return your recommendation as a JSON object with these fields:
- recommended_strategy: Dict mapping document IDs to lists of tool names
- strategy_reasoning: String explaining your choices
- confidence: Float between 0.0 and 1.0
"""

    return prompt


def get_synthesis_prompt(
    experiment_type: str,
    experiment_goal: str,
    focus_term: Optional[str],
    focus_term_definition: Optional[str],
    focus_term_context_anchors: Optional[List[str]],
    processing_results: Dict[str, Any],
    document_metadata: Optional[Dict[str, Dict[str, Any]]]
) -> str:
    """
    Generate Stage 5 (Synthesize) prompt customized by experiment type.

    For temporal_evolution experiments, this will also request structured term cards.

    Returns:
        Formatted prompt string
    """

    # Build term baseline section
    term_baseline = ""
    if focus_term and focus_term_definition:
        term_baseline = f"""
## Term Baseline: "{focus_term}"

**Dictionary Definition**: {focus_term_definition}

**Context Anchors**: {", ".join(focus_term_context_anchors) if focus_term_context_anchors else "N/A"}

Use this baseline to identify semantic drift, evolution, or domain-specific variations.
"""

    # Summarize processing results to avoid token limits while preserving analytical value
    summarized_results = summarize_processing_results(processing_results, max_items_per_tool=50)

    # Build processing results summary with metadata
    results_with_metadata = []
    for doc_id, results in summarized_results.items():
        doc_info = {'document_id': doc_id, 'results': results}

        if document_metadata and doc_id in document_metadata:
            doc_info['metadata'] = document_metadata[doc_id]

        results_with_metadata.append(doc_info)

    # Experiment-type-specific synthesis instructions
    synthesis_instructions = {
        'temporal_evolution': f"""
## Temporal Evolution Analysis

**Your Task**: Organize tool-extracted data by time period to enable temporal analysis.

**Organization Steps**:
1. **Group by time**: Use temporal extraction results to identify distinct time periods in the documents
2. **Summarize per period**: For each period, gather entity counts, co-occurrences, and frequencies from tool results
3. **List anchors**: Show which semantic anchors (from entity extraction) appear in each period
4. **Present side-by-side**: Structure data so researchers can easily compare across periods
5. **Cite sources**: Include document IDs and tool names for all data points

**Example Organization**:
"**Period 1 (1960-1980)**: 2 documents [Docs 393-394]. Entity extraction found '{focus_term}' co-occurring with: 'program' (12×), 'system' (8×), 'autonomous' (6×) [extract_entities_spacy]. Term frequency: 0.23 per 1000 words [extract_definitions].

**Period 2 (2000-2020)**: 3 documents [Docs 397-399]. Entity extraction found '{focus_term}' co-occurring with: 'learning' (23×), 'intelligent' (15×), 'adaptive' (11×) [extract_entities_spacy]. Term frequency: 0.47 per 1000 words [extract_definitions]."

**IMPORTANT**: Generate structured term cards as DATA SUMMARIES (not interpretations).

For each time period found in temporal extraction results, create a card with:
- **period_label**: Time range from tool outputs (e.g., "1960-1980")
- **definition**: Most common co-occurring terms from entity extraction (just list the data with counts)
- **frequency**: Relative frequency from tool counts (normalize to 0.0-1.0 across all periods)
- **context_changes**: New semantic anchors that appear in this period vs. previous ones (just list new terms, no interpretation)
- **narrative**: 2-3 factual sentences presenting primary data points (counts, entities, frequencies). Use neutral language: "found", "observed", "present", "absent". Include document sources [Doc IDs]. NO interpretation or value judgments.

Return JSON with:
{{
    "cross_document_insights": "Markdown text with overall data organization and patterns (neutral tone, with source citations)",
    "term_evolution_analysis": "Markdown text focused on term usage patterns across time (neutral tone, with source citations)",
    "generated_term_cards": [
        {{
            "term": "{focus_term}",
            "period_label": "Period range",
            "definition": "Usage in this period (data only)",
            "frequency": 0.5,
            "context_changes": ["new", "anchor", "terms"],
            "narrative": "Factual summary with document sources [Doc IDs]"
        }}
    ]
}}
""",
        'domain_comparison': f"""
## Domain Comparison Analysis

**Your Task**: Compare how "{focus_term}" is used across different research domains.

1. **Cross-Document Insights**: Identify usage patterns across domains
2. **Domain-Specific Meanings**: How does the definition vary by field?
3. **Universal vs. Specialized Anchors**: Which semantic components are consistent vs. domain-specific?
4. **Semantic Shifts**: What happens when the term crosses disciplinary boundaries?

Return JSON with:
{{
    "cross_document_insights": "Markdown text with overall analysis",
    "term_evolution_analysis": "Markdown text focused on cross-domain usage"
}}
""",
        'entity_extraction': """
## Entity Analysis

**Your Task**: Synthesize entity extraction results across documents.

1. **Cross-Document Insights**: Common entities, patterns, and relationships
2. **Entity Categories**: How entities cluster or relate hierarchically
3. **Findings**: Most frequent entities and their relationships

Return JSON with:
{{
    "cross_document_insights": "Markdown text with overall analysis"
}}
"""
    }

    instructions = synthesis_instructions.get(experiment_type, """
## General Analysis

Synthesize the processing results to identify patterns, themes, and insights across all documents.

Return JSON with:
{{
    "cross_document_insights": "Markdown text with your analysis"
}}
""")

    prompt = f"""You are synthesizing insights from multi-document processing results.

## Experiment Goal
{experiment_goal}

{term_baseline}

## Processing Results

**Important Context**:
The results below come from specialized NLP tools that extracted structured data from documents:
- **Entity extraction** (spaCy): Identified all named entities, their types, and frequencies
- **Temporal extraction**: Found all dates, time periods, and temporal expressions
- **Definition extraction**: Located formal definitions and usage contexts
- **Semantic analysis**: Measured term frequencies and co-occurrences

Your task is to ORGANIZE these tool findings into a clear structure that enables the researcher to identify patterns and draw conclusions.

{json.dumps(results_with_metadata, indent=2).replace('{', '{{').replace('}', '}}')}

{instructions}

**Organization Guidelines**:
1. **Group by time/domain**: Organize tool findings into clear periods or domains
2. **Present primary data points**: Surface the most relevant counts, entities, and frequencies
3. **Highlight contrasts**: Show where tool results differ across documents (without interpreting why)
4. **Structure for analysis**: Format data so patterns are easily visible to the researcher
5. **Preserve specificity**: Include exact numbers, entity names, and dates from tool outputs
6. **Cite sources**: For every claim, include document ID and tool name in brackets like [Doc 393: extract_entities_spacy] or [Docs 393-395: extract_temporal]

Example organization: "**1960-1980 Period** (2 documents): Entity extraction found 15 mentions of 'autonomous' [Doc 393: extract_entities_spacy], co-occurring with: 'program' (12×), 'system' (8×), 'control' (6×). **2000-2020 Period** (3 documents): Entity extraction found 47 mentions of 'autonomous' [Docs 397-398: extract_entities_spacy], co-occurring with: 'learning' (23×), 'agent' (18×), 'intelligent' (15×)."

{LLM_STYLE_GUIDELINES}

**Note**: Your role is to organize data, not interpret it. The researcher will draw their own conclusions from the structured presentation. Users will be concerned about potential hallucination, so ground every statement in specific tool outputs with clear source citations.
"""

    return prompt
