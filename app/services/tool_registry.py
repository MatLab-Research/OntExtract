"""
Tool Registry with Implementation Status Tracking

This module maintains the authoritative list of available processing tools
and tracks which ones are fully implemented vs stubs.
"""

from typing import Dict, List, Any
from dataclasses import dataclass
from enum import Enum


class ToolStatus(Enum):
    """Tool implementation status."""
    IMPLEMENTED = "implemented"  # Fully working
    STUB = "stub"  # Interface exists but not implemented
    PLANNED = "planned"  # Planned for future implementation
    DEPRECATED = "deprecated"  # No longer recommended


@dataclass
class ToolDefinition:
    """Complete tool definition with metadata."""
    name: str
    description: str
    status: ToolStatus
    category: str  # segmentation, extraction, embedding, analysis
    dependencies: List[str]  # Required services/libraries
    notes: str = ""


# Authoritative tool registry
TOOL_REGISTRY: Dict[str, ToolDefinition] = {
    "segment_paragraph": ToolDefinition(
        name="segment_paragraph",
        description="Break document into paragraphs",
        status=ToolStatus.IMPLEMENTED,  # ✅ IMPLEMENTED
        category="segmentation",
        dependencies=[],
        notes="Simple text splitting by double newlines"
    ),
    "segment_sentence": ToolDefinition(
        name="segment_sentence",
        description="Break into sentences",
        status=ToolStatus.IMPLEMENTED,  # ✅ IMPLEMENTED
        category="segmentation",
        dependencies=["nltk"],
        notes="Requires NLTK punkt tokenizer (auto-downloaded)"
    ),
    "extract_entities_spacy": ToolDefinition(
        name="extract_entities_spacy",
        description="Extract named entities (PERSON, ORG, DATE, GPE, etc.) and concepts",
        status=ToolStatus.IMPLEMENTED,  # ✅ IMPLEMENTED
        category="extraction",
        dependencies=["spacy", "en_core_web_sm"],
        notes="Extracts standard NER entities plus noun phrases as concepts"
    ),
    "extract_temporal": ToolDefinition(
        name="extract_temporal",
        description="Extract temporal expressions, periods, and timelines",
        status=ToolStatus.IMPLEMENTED,  # ✅ IMPLEMENTED
        category="extraction",
        dependencies=["spacy", "python-dateutil"],
        notes="Uses spaCy DATE entities + regex patterns for periods/decades"
    ),
    "extract_causal": ToolDefinition(
        name="extract_causal",
        description="Extract causal relationships between events",
        status=ToolStatus.IMPLEMENTED,  # ✅ IMPLEMENTED
        category="extraction",
        dependencies=["spacy"],
        notes="Pattern matching + dependency parsing for causation"
    ),
    "extract_definitions": ToolDefinition(
        name="extract_definitions",
        description="Extract term definitions and explanations",
        status=ToolStatus.IMPLEMENTED,  # ✅ IMPLEMENTED
        category="extraction",
        dependencies=["spacy"],
        notes="Multiple definition patterns + appositive constructions"
    ),
    "period_aware_embedding": ToolDefinition(
        name="period_aware_embedding",
        description="Generate period-aware embeddings for semantic drift analysis",
        status=ToolStatus.IMPLEMENTED,  # ✅ IMPLEMENTED
        category="embedding",
        dependencies=["sentence_transformers"],
        notes="Automatic period detection from temporal markers"
    ),
}


def get_available_tools(include_stubs: bool = False) -> Dict[str, ToolDefinition]:
    """
    Get tools that can be used.

    Args:
        include_stubs: If True, include stub implementations (for testing)

    Returns:
        Dictionary of available tools
    """
    if include_stubs:
        # Include everything except deprecated
        return {
            name: tool for name, tool in TOOL_REGISTRY.items()
            if tool.status != ToolStatus.DEPRECATED
        }
    else:
        # Only fully implemented tools
        return {
            name: tool for name, tool in TOOL_REGISTRY.items()
            if tool.status == ToolStatus.IMPLEMENTED
        }


def get_tool_descriptions() -> str:
    """
    Get formatted tool descriptions for LLM prompts.

    Returns:
        Formatted string describing available tools
    """
    available = get_available_tools(include_stubs=True)

    lines = ["Available Processing Tools:"]
    for i, (name, tool) in enumerate(available.items(), 1):
        status_marker = ""
        if tool.status == ToolStatus.STUB:
            status_marker = " [STUB - Limited functionality]"
        elif tool.status == ToolStatus.PLANNED:
            status_marker = " [PLANNED - Not yet available]"

        lines.append(f"{i}. {name} - {tool.description}{status_marker}")

    return "\n".join(lines)


def validate_tool_strategy(strategy: Dict[str, List[str]]) -> Dict[str, Any]:
    """
    Validate that recommended tools are available and implemented.

    Args:
        strategy: Dictionary mapping document IDs to lists of tool names

    Returns:
        Validation result with warnings and filtered strategy
    """
    available = get_available_tools(include_stubs=True)
    all_tools = set(TOOL_REGISTRY.keys())

    warnings = []
    stub_tools = []
    unknown_tools = []

    # Check all recommended tools
    for doc_id, tools in strategy.items():
        for tool in tools:
            if tool not in all_tools:
                unknown_tools.append(tool)
            elif tool in available:
                tool_def = TOOL_REGISTRY[tool]
                if tool_def.status == ToolStatus.STUB:
                    stub_tools.append(tool)
            else:
                warnings.append(f"Tool '{tool}' is deprecated or unavailable")

    # Generate warnings
    if unknown_tools:
        warnings.append(
            f"Unknown tools recommended: {', '.join(set(unknown_tools))}. "
            f"These will be skipped during execution."
        )

    if stub_tools:
        warnings.append(
            f"Stub implementations in use: {', '.join(set(stub_tools))}. "
            f"These tools have limited functionality and should be replaced with "
            f"full implementations for production use."
        )

    # Filter strategy to only include available tools
    filtered_strategy = {}
    for doc_id, tools in strategy.items():
        filtered_tools = [
            t for t in tools
            if t in available and TOOL_REGISTRY[t].status != ToolStatus.DEPRECATED
        ]
        if filtered_tools:
            filtered_strategy[doc_id] = filtered_tools

    return {
        "valid": len(warnings) == 0,
        "warnings": warnings,
        "filtered_strategy": filtered_strategy,
        "stats": {
            "total_tools_recommended": sum(len(tools) for tools in strategy.values()),
            "unknown_tools": len(set(unknown_tools)),
            "stub_tools": len(set(stub_tools)),
            "tools_after_filtering": sum(len(tools) for tools in filtered_strategy.values())
        }
    }


def get_implementation_roadmap() -> List[Dict[str, Any]]:
    """
    Get prioritized list of tools to implement.

    Returns:
        List of tools ordered by priority for implementation
    """
    priority_order = [
        "segment_paragraph",  # Easy - basic text splitting
        "segment_sentence",   # Easy - NLTK available
        "extract_entities_spacy",  # Medium - spaCy integration
        "extract_definitions",  # Medium - pattern + LLM
        "extract_temporal",  # Hard - external parser needed
        "extract_causal",  # Hard - complex NLP
        "period_aware_embedding",  # Hard - requires research
    ]

    roadmap = []
    for tool_name in priority_order:
        if tool_name in TOOL_REGISTRY:
            tool = TOOL_REGISTRY[tool_name]
            if tool.status != ToolStatus.IMPLEMENTED:
                roadmap.append({
                    "name": tool.name,
                    "description": tool.description,
                    "status": tool.status.value,
                    "category": tool.category,
                    "dependencies": tool.dependencies,
                    "notes": tool.notes
                })

    return roadmap
