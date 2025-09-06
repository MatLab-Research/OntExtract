"""
Period-Aware Excerpt Service - Extracts relevant excerpts from OED definitions
based on specific time periods using LLM analysis for semantic evolution visualization
"""

from typing import Dict, List, Optional, Any, Tuple
import json
import re
import os
from datetime import datetime
import anthropic


class PeriodExcerptService:
    """Service for extracting period-relevant excerpts from OED definitions"""
    
    def __init__(self):
        # Initialize Anthropic client using existing pattern
        api_key = os.environ.get('ANTHROPIC_API_KEY')
        self.use_llm = bool(api_key)
        
        if self.use_llm:
            try:
                self.client = anthropic.Anthropic(api_key=api_key)
            except Exception as e:
                print(f"Warning: Could not initialize Anthropic client: {e}")
                self.use_llm = False
    
    def extract_period_relevant_excerpts(self, 
                                       definition_text: str, 
                                       target_years: List[int],
                                       term: str,
                                       context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Extract excerpts from definition that are relevant to specific time periods
        
        Args:
            definition_text: Full OED definition text
            target_years: List of years we're analyzing (e.g., [1957, 1976, 1995, 2018])
            term: The term being analyzed
            context: Optional context about the experiment/analysis
        
        Returns:
            Dict with period-relevant excerpts and analysis
        """
        
        if not definition_text or not target_years:
            return {
                "success": False,
                "error": "Missing definition text or target years"
            }
        
        # Create LLM prompt for period-aware excerpt extraction
        prompt = self._create_excerpt_prompt(definition_text, target_years, term, context)
        
        if self.use_llm:
            try:
                # Get LLM analysis using Anthropic client
                message = self.client.messages.create(
                    model=os.environ.get("CLAUDE_DEFAULT_MODEL", "claude-3-5-sonnet-20241022"),
                    max_tokens=800,
                    messages=[{"role": "user", "content": prompt}]
                )
                
                # Parse the response
                result = self._parse_llm_response(message.content[0].text, definition_text, target_years)
                
                return {
                    "success": True,
                    "excerpts": result["excerpts"],
                    "temporal_relevance": result["temporal_relevance"],
                    "semantic_shift_indicators": result["semantic_shifts"],
                    "confidence": result["confidence"],
                    "full_definition_url": context.get("oed_url") if context else None
                }
                
            except Exception as e:
                print(f"LLM analysis failed: {e}, falling back to simple extraction")
        
        # Fallback to simple excerpt extraction
        return {
            "success": True,
            "excerpts": [{
                "text": self._create_fallback_excerpt(definition_text, target_years),
                "relevance_to_periods": target_years,
                "semantic_significance": f"Definition excerpt relevant to years: {', '.join(map(str, target_years))}",
                "excerpt_type": "fallback"
            }],
            "temporal_relevance": {},
            "semantic_shifts": [],
            "confidence": 0.5,
            "full_definition_url": context.get("oed_url") if context else None
        }
    
    def _create_excerpt_prompt(self, definition_text: str, target_years: List[int], 
                              term: str, context: Optional[Dict] = None) -> str:
        """Create LLM prompt for extracting period-relevant excerpts"""
        
        years_str = ", ".join(map(str, target_years))
        
        prompt = f"""
You are analyzing the semantic evolution of the term "{term}" across specific time periods: {years_str}.

Given this OED definition, extract the most relevant excerpts that help understand how the term's meaning relates to these specific years. Focus on:

1. Parts of the definition that mention time periods, historical contexts, or usage evolution
2. Sections that indicate semantic shifts around these years
3. Examples or quotations that fall within or near these periods
4. Domain-specific usage that emerged in these eras

**OED Definition:**
{definition_text}

**Target Analysis Years:** {years_str}

Please respond with a JSON object containing:
{{
    "excerpts": [
        {{
            "text": "relevant excerpt text (max 150 chars)",
            "relevance_to_periods": [1957, 1976],
            "semantic_significance": "brief explanation",
            "excerpt_type": "temporal_marker|domain_shift|usage_evolution|quotation_period"
        }}
    ],
    "temporal_relevance": {{
        "1957": "how definition relates to this period",
        "1976": "how definition relates to this period",
        // ... for each target year
    }},
    "semantic_shifts": [
        "key semantic changes relevant to these periods"
    ],
    "confidence": 0.8
}}

If no specific temporal relevance is found, extract the most generally relevant parts of the definition that would help understand semantic evolution.
"""
        return prompt
    
    def _parse_llm_response(self, response_text: str, original_definition: str, 
                           target_years: List[int]) -> Dict[str, Any]:
        """Parse LLM response and validate the extracted excerpts"""
        
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                raise ValueError("No JSON found in response")
            
            # Validate and clean excerpts
            validated_excerpts = []
            for excerpt in result.get("excerpts", []):
                if self._validate_excerpt(excerpt, original_definition):
                    validated_excerpts.append(excerpt)
            
            # If no valid excerpts found, create fallback
            if not validated_excerpts:
                validated_excerpts = [{
                    "text": self._create_fallback_excerpt(original_definition, target_years),
                    "relevance_to_periods": target_years,
                    "semantic_significance": "General definition excerpt",
                    "excerpt_type": "fallback"
                }]
            
            return {
                "excerpts": validated_excerpts,
                "temporal_relevance": result.get("temporal_relevance", {}),
                "semantic_shifts": result.get("semantic_shifts", []),
                "confidence": min(result.get("confidence", 0.5), 1.0)
            }
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            # Fallback to simple extraction
            return {
                "excerpts": [{
                    "text": self._create_fallback_excerpt(original_definition, target_years),
                    "relevance_to_periods": target_years,
                    "semantic_significance": "Definition excerpt (LLM parsing failed)",
                    "excerpt_type": "fallback"
                }],
                "temporal_relevance": {},
                "semantic_shifts": [],
                "confidence": 0.3
            }
    
    def _validate_excerpt(self, excerpt: Dict, original_definition: str) -> bool:
        """Validate that excerpt is reasonable and exists in original definition"""
        
        if not isinstance(excerpt, dict):
            return False
            
        text = excerpt.get("text", "")
        if not text or len(text) < 10 or len(text) > 200:
            return False
        
        # Check if excerpt text appears in original (allowing for minor variations)
        text_words = set(text.lower().split())
        orig_words = set(original_definition.lower().split())
        
        # At least 60% of excerpt words should appear in original
        overlap = len(text_words.intersection(orig_words))
        if len(text_words) > 0 and overlap / len(text_words) < 0.6:
            return False
        
        return True
    
    def _create_fallback_excerpt(self, definition_text: str, target_years: List[int]) -> str:
        """Create a simple fallback excerpt when LLM analysis fails"""
        
        # Look for years or temporal indicators first
        year_pattern = r'\b(19|20)\d{2}\b'
        years_in_text = re.findall(year_pattern, definition_text)
        
        if years_in_text:
            # Find sentence containing years
            sentences = re.split(r'[.!?]+', definition_text)
            for sentence in sentences:
                if re.search(year_pattern, sentence):
                    excerpt = sentence.strip()
                    if len(excerpt) > 150:
                        excerpt = excerpt[:147] + "..."
                    return excerpt
        
        # Otherwise, take first substantial sentence
        sentences = re.split(r'[.!?]+', definition_text)
        for sentence in sentences:
            if len(sentence.strip()) > 20:
                excerpt = sentence.strip()
                if len(excerpt) > 150:
                    excerpt = excerpt[:147] + "..."
                return excerpt
        
        # Ultimate fallback
        return definition_text[:147] + "..." if len(definition_text) > 150 else definition_text
    
    def batch_extract_excerpts(self, definitions: List[Dict], target_years: List[int], 
                              term: str) -> List[Dict]:
        """
        Extract period-relevant excerpts for multiple definitions
        
        Args:
            definitions: List of definition dicts with 'definition_text' or 'text'
            target_years: Years being analyzed
            term: Term being analyzed
        
        Returns:
            List of definitions enhanced with period-relevant excerpts
        """
        
        enhanced_definitions = []
        
        for definition in definitions:
            definition_text = definition.get('definition_text') or definition.get('text', '')
            
            if definition_text:
                excerpt_result = self.extract_period_relevant_excerpts(
                    definition_text, target_years, term, definition
                )
                
                # Add excerpt information to definition
                enhanced_def = definition.copy()
                
                if excerpt_result["success"] and excerpt_result["excerpts"]:
                    # Use the first (most relevant) excerpt
                    best_excerpt = excerpt_result["excerpts"][0]
                    enhanced_def["period_relevant_excerpt"] = best_excerpt["text"]
                    enhanced_def["excerpt_relevance"] = best_excerpt["semantic_significance"]
                    enhanced_def["relevant_periods"] = best_excerpt["relevance_to_periods"]
                else:
                    # Fallback
                    enhanced_def["period_relevant_excerpt"] = excerpt_result.get("fallback_excerpt", definition_text[:150] + "...")
                    enhanced_def["excerpt_relevance"] = "General definition excerpt"
                    enhanced_def["relevant_periods"] = target_years
                
                enhanced_definitions.append(enhanced_def)
            else:
                enhanced_definitions.append(definition)
        
        return enhanced_definitions