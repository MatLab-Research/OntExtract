"""
Node functions for LangGraph orchestration workflow

Each node performs a specific task in the document processing pipeline.
Latest LangGraph 1.0.2 best practices (January 2025).
"""

import os
import logging
from datetime import datetime
from typing import List, Dict, Any

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from app.orchestration.state import OrchestratorState

logger = logging.getLogger(__name__)

# Claude client - initialized lazily to avoid import-time errors
_claude_client = None

def get_claude_client():
    """Get or create Claude client (lazy initialization)"""
    global _claude_client
    if _claude_client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            logger.warning("ANTHROPIC_API_KEY not found - orchestration will fail")
        _claude_client = ChatAnthropic(
            model="claude-sonnet-4-20250514",
            api_key=api_key,
            max_tokens=2000,
            temperature=0.0  # Deterministic for tool selection
        )
    return _claude_client


async def analyze_document_node(state: OrchestratorState) -> Dict[str, Any]:
    """
    Claude analyzes document characteristics and recommends processing tools.

    This is the orchestration decision point where Claude examines the document
    and selects appropriate NLP tools based on content characteristics.

    Args:
        state: Current orchestrator state with document_text and metadata

    Returns:
        State updates with recommended_tools and orchestration_reasoning
    """

    logger.info(f"Analyzing document {state['document_id']} for tool selection")

    # Extract document sample for analysis (first 2000 chars to save tokens)
    doc_sample = state['document_text'][:2000]
    doc_length = len(state['document_text'])
    doc_metadata = state['document_metadata']

    # Construct analysis prompt
    system_prompt = """You are an expert NLP orchestration system. Analyze documents and recommend appropriate processing tools.

Available Tools:
1. segment_paragraph - Split by paragraphs (fast, preserves structure, good for organized text)
2. segment_sentence - Split by sentences (detailed, good for granular analysis)
3. segment_semantic - Cluster by meaning using embeddings (slow, best for unstructured text)
4. extract_entities_spacy - Fast entity extraction with spaCy (general purpose, reliable)
5. extract_entities_langextract - Detailed extraction with LLM (higher accuracy, slower, uses Gemini)
6. extract_temporal - Find dates and time references (good for historical documents)
7. generate_embeddings - Create vector representations (enables semantic search)

Your task:
1. Analyze the document characteristics (length, structure, domain, complexity)
2. Recommend 2-4 tools that would be most valuable for this document
3. Explain your reasoning clearly
4. Provide a confidence score (0.0-1.0)

Return your response in this exact format:
RECOMMENDED_TOOLS: [tool1, tool2, tool3]
CONFIDENCE: 0.85
REASONING: Your detailed explanation here..."""

    user_prompt = f"""Analyze this document and recommend processing tools:

Document Metadata:
- Length: {doc_length} characters
- Format: {doc_metadata.get('format', 'unknown')}
- Title: {doc_metadata.get('title', 'Unknown')}

Document Sample (first 2000 characters):
{doc_sample}

What tools should we use and why?"""

    try:
        # Get Claude client (lazy initialization)
        claude_client = get_claude_client()

        # Call Claude for analysis
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]

        response = await claude_client.ainvoke(messages)
        response_text = response.content

        # Parse Claude's response
        recommended_tools = _extract_tools_from_response(response_text)
        confidence = _extract_confidence_from_response(response_text)
        reasoning = _extract_reasoning_from_response(response_text)

        # Analyze document characteristics (simple heuristics for now)
        characteristics = {
            "length": doc_length,
            "estimated_words": doc_length // 5,  # Rough estimate
            "has_structure": "\n\n" in state['document_text'],
            "format": doc_metadata.get('format', 'unknown')
        }

        logger.info(f"Claude recommended tools: {recommended_tools}")
        logger.info(f"Confidence: {confidence}")

        # Add to execution trace
        trace_entry = {
            "node": "analyze_document",
            "timestamp": datetime.utcnow().isoformat(),
            "tools_recommended": recommended_tools,
            "confidence": confidence,
            "reasoning_summary": reasoning[:200] + "..." if len(reasoning) > 200 else reasoning
        }

        return {
            "document_characteristics": characteristics,
            "recommended_tools": recommended_tools,
            "orchestration_reasoning": reasoning,
            "confidence_score": confidence,
            "execution_trace": [trace_entry]  # Will be appended to existing list
        }

    except Exception as e:
        logger.error(f"Error in analyze_document_node: {e}")

        # Fallback to safe defaults
        return {
            "document_characteristics": {"length": doc_length},
            "recommended_tools": ["segment_paragraph", "extract_entities_spacy"],  # Safe defaults
            "orchestration_reasoning": f"Error in analysis: {str(e)}. Using default tools.",
            "confidence_score": 0.5,
            "errors": [f"Analysis error: {str(e)}"],
            "execution_trace": [{
                "node": "analyze_document",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
                "fallback_used": True
            }]
        }


async def segment_paragraph_node(state: OrchestratorState) -> Dict[str, Any]:
    """
    Segment document by paragraphs using existing OntExtract code.

    Args:
        state: Current state with document_text

    Returns:
        State updates with segmentation_results
    """

    logger.info(f"Executing paragraph segmentation for document {state['document_id']}")

    try:
        from app.services.text_processing import TextProcessingService

        processor = TextProcessingService()

        # Simple paragraph splitting (your existing code would go here)
        paragraphs = [p.strip() for p in state['document_text'].split('\n\n') if p.strip()]

        results = {
            "method": "paragraph",
            "segments": paragraphs,
            "count": len(paragraphs),
            "metadata": {
                "avg_length": sum(len(p) for p in paragraphs) // len(paragraphs) if paragraphs else 0
            }
        }

        logger.info(f"Created {len(paragraphs)} paragraph segments")

        return {
            "segmentation_results": results,
            "execution_trace": [{
                "node": "segment_paragraph",
                "timestamp": datetime.utcnow().isoformat(),
                "segments_created": len(paragraphs)
            }]
        }

    except Exception as e:
        logger.error(f"Error in segment_paragraph_node: {e}")
        return {
            "errors": [f"Paragraph segmentation error: {str(e)}"],
            "execution_trace": [{
                "node": "segment_paragraph",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }]
        }


async def extract_entities_spacy_node(state: OrchestratorState) -> Dict[str, Any]:
    """
    Extract entities using spaCy NER.

    Args:
        state: Current state with document_text

    Returns:
        State updates with entity_results
    """

    logger.info(f"Executing spaCy entity extraction for document {state['document_id']}")

    try:
        import spacy

        # Load spaCy model (cache this in production)
        try:
            nlp = spacy.load("en_core_web_sm")
        except OSError:
            logger.warning("spaCy model not found, downloading...")
            os.system("python -m spacy download en_core_web_sm")
            nlp = spacy.load("en_core_web_sm")

        # Process document
        doc = nlp(state['document_text'][:100000])  # Limit to avoid memory issues

        # Extract entities
        entities = [
            {
                "text": ent.text,
                "label": ent.label_,
                "start": ent.start_char,
                "end": ent.end_char
            }
            for ent in doc.ents
        ]

        # Group by type
        entity_types = {}
        for ent in entities:
            label = ent['label']
            if label not in entity_types:
                entity_types[label] = []
            entity_types[label].append(ent['text'])

        results = {
            "method": "spacy",
            "entities": entities,
            "count": len(entities),
            "entity_types": entity_types,
            "metadata": {
                "model": "en_core_web_sm",
                "unique_entities": len(set(e['text'] for e in entities))
            }
        }

        logger.info(f"Extracted {len(entities)} entities using spaCy")

        return {
            "entity_results": results,
            "execution_trace": [{
                "node": "extract_entities_spacy",
                "timestamp": datetime.utcnow().isoformat(),
                "entities_found": len(entities)
            }]
        }

    except Exception as e:
        logger.error(f"Error in extract_entities_spacy_node: {e}")
        return {
            "errors": [f"Entity extraction error: {str(e)}"],
            "execution_trace": [{
                "node": "extract_entities_spacy",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }]
        }


async def synthesize_results_node(state: OrchestratorState) -> Dict[str, Any]:
    """
    Claude synthesizes all tool results and generates insights.

    Args:
        state: Current state with all tool results

    Returns:
        State updates with synthesis and insights
    """

    logger.info(f"Synthesizing results for document {state['document_id']}")

    try:
        # Construct synthesis prompt
        system_prompt = """You are an expert at analyzing NLP processing results.
Given the results from multiple tools, provide:
1. A concise synthesis of key findings
2. 3-5 specific insights
3. Recommended next steps for analysis

Be specific and reference actual findings from the results."""

        results_summary = f"""Document Processing Results:

Document: {state['document_metadata'].get('title', 'Unknown')}
Length: {state['document_characteristics'].get('length', 0)} characters

Tools Used: {', '.join(state.get('recommended_tools', []))}

Segmentation: {state.get('segmentation_results', {}).get('count', 0)} segments created

Entities: {state.get('entity_results', {}).get('count', 0)} entities found
Entity Types: {', '.join(state.get('entity_results', {}).get('entity_types', {}).keys())}

Sample Entities: {', '.join(list(set(
    ent['text'] for ent in state.get('entity_results', {}).get('entities', [])[:20]
)))}

Provide your synthesis, insights, and recommendations."""

        # Get Claude client (lazy initialization)
        claude_client = get_claude_client()

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=results_summary)
        ]

        response = await claude_client.ainvoke(messages)
        synthesis_text = response.content

        # Parse synthesis (simple parsing for now)
        insights = _extract_insights_from_synthesis(synthesis_text)
        next_steps = _extract_next_steps_from_synthesis(synthesis_text)

        logger.info("Synthesis complete")

        return {
            "synthesis": synthesis_text,
            "insights": insights,
            "suggested_next_steps": next_steps,
            "execution_trace": [{
                "node": "synthesize_results",
                "timestamp": datetime.utcnow().isoformat(),
                "insights_generated": len(insights)
            }]
        }

    except Exception as e:
        logger.error(f"Error in synthesize_results_node: {e}")
        return {
            "synthesis": "Error generating synthesis.",
            "errors": [f"Synthesis error: {str(e)}"],
            "execution_trace": [{
                "node": "synthesize_results",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }]
        }


# Helper functions for parsing Claude's responses

def _extract_tools_from_response(response: str) -> List[str]:
    """Extract tool names from Claude's response"""
    try:
        if "RECOMMENDED_TOOLS:" in response:
            tools_line = [line for line in response.split('\n') if 'RECOMMENDED_TOOLS:' in line][0]
            tools_str = tools_line.split('RECOMMENDED_TOOLS:')[1].strip()
            tools_str = tools_str.strip('[]')
            tools = [t.strip() for t in tools_str.split(',')]
            return tools
    except:
        pass

    # Fallback: look for tool names anywhere in response
    all_tools = [
        "segment_paragraph", "segment_sentence", "segment_semantic",
        "extract_entities_spacy", "extract_entities_langextract",
        "extract_temporal", "generate_embeddings"
    ]
    return [tool for tool in all_tools if tool in response]


def _extract_confidence_from_response(response: str) -> float:
    """Extract confidence score from Claude's response"""
    try:
        if "CONFIDENCE:" in response:
            conf_line = [line for line in response.split('\n') if 'CONFIDENCE:' in line][0]
            conf_str = conf_line.split('CONFIDENCE:')[1].strip()
            return float(conf_str)
    except:
        pass
    return 0.7  # Default


def _extract_reasoning_from_response(response: str) -> str:
    """Extract reasoning text from Claude's response"""
    try:
        if "REASONING:" in response:
            reasoning = response.split('REASONING:')[1].strip()
            return reasoning
    except:
        pass
    return response  # Return full response if can't parse


def _extract_insights_from_synthesis(synthesis: str) -> List[str]:
    """Extract insights from synthesis text"""
    # Simple extraction - look for numbered lists
    insights = []
    lines = synthesis.split('\n')
    for line in lines:
        if line.strip() and (line.strip()[0].isdigit() or line.strip().startswith('-')):
            insights.append(line.strip())
    return insights[:5]  # Max 5


def _extract_next_steps_from_synthesis(synthesis: str) -> List[str]:
    """Extract next steps from synthesis text"""
    # Look for "next steps" section
    if "next step" in synthesis.lower():
        parts = synthesis.lower().split("next step")
        if len(parts) > 1:
            next_steps_text = parts[1]
            lines = next_steps_text.split('\n')
            steps = [l.strip() for l in lines if l.strip() and (l.strip()[0].isdigit() or l.strip().startswith('-'))]
            return steps[:3]
    return []
