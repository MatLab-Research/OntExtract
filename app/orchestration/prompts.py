"""
Experiment-type-specific prompts for LLM orchestration.

This module generates customized prompts based on experiment type, incorporating
metadata such as term definitions, context anchors, and document bibliographic info.
"""

from typing import Dict, List, Any, Optional
import json


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
1. Key entities, concepts, and relationships in the documents
2. How entities relate to the focus term (if present)
3. Patterns in entity usage and co-occurrence
4. Hierarchical or categorical relationships
"""
    }

    instructions = type_specific_instructions.get(experiment_type, """
**General Document Analysis**

Focus on:
1. Main themes and topics across documents
2. Key concepts and terminology
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
3. **Key Considerations**: What aspects of the term's meaning or usage are most important to track?

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
    tool_priorities = {
        'temporal_evolution': {
            'high': ['extract_temporal', 'semantic_similarity'],
            'rationale': 'Temporal experiments benefit from date extraction and semantic comparison to track meaning evolution over time.'
        },
        'domain_comparison': {
            'high': ['extract_entities_spacy', 'semantic_similarity'],
            'rationale': 'Domain comparison requires entity extraction and semantic analysis to identify usage patterns across fields.'
        },
        'entity_extraction': {
            'high': ['extract_entities_spacy', 'llm_extract_concepts'],
            'rationale': 'Entity extraction experiments need comprehensive NER and concept extraction.'
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

    # Build processing results summary with metadata
    results_with_metadata = []
    for doc_id, results in processing_results.items():
        doc_info = {'document_id': doc_id, 'results': results}

        if document_metadata and doc_id in document_metadata:
            doc_info['metadata'] = document_metadata[doc_id]

        results_with_metadata.append(doc_info)

    # Experiment-type-specific synthesis instructions
    synthesis_instructions = {
        'temporal_evolution': f"""
## Temporal Evolution Analysis

**Your Task**: Analyze how "{focus_term}" has evolved across time periods.

1. **Cross-Document Insights**: Identify patterns in how the term is used across different time periods
2. **Semantic Drift**: Compare current usage to the baseline definition
3. **Context Anchor Tracking**: Which anchors appear/disappear over time?
4. **Term Evolution**: What new meanings or applications emerged? When?

**IMPORTANT**: Also generate structured term cards for visualization.

For each time period found in the documents, create a card with:
- period_label: e.g., "1650-1750"
- definition: How the term was used in this period
- frequency: Relative usage frequency (0.0 to 1.0)
- context_changes: List of new/changed semantic anchors
- narrative: 2-3 sentences explaining the evolution

Return JSON with:
{{
    "cross_document_insights": "Markdown text with overall analysis",
    "term_evolution_analysis": "Markdown text focused on the term",
    "generated_term_cards": [
        {{
            "term": "{focus_term}",
            "period_label": "Period range",
            "definition": "Usage in this period",
            "frequency": 0.5,
            "context_changes": ["new", "anchor", "terms"],
            "narrative": "Explanation of changes"
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
3. **Key Findings**: Most significant entities and their relationships

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
{json.dumps(results_with_metadata, indent=2).replace('{', '{{').replace('}', '}}')}

{instructions}

**Guidelines**:
- Reference specific results and documents
- Compare usage to baseline definition (if applicable)
- Use markdown formatting for readability
- Be specific and cite evidence from the results
"""

    return prompt
