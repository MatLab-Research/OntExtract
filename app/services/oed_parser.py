"""
Simplified OED (Oxford English Dictionary) PDF Parser Service

Uses pypdf for text extraction and Claude for structured parsing.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
import anthropic
import pypdf
import re

logger = logging.getLogger(__name__)


class OEDParser:
    """Simplified OED parser using LangExtract and Claude"""
    
    def __init__(self):
        """Initialize the OED parser"""
        api_key = os.environ.get('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        
        # Create client (dynamic API surface; silence strict checkers)
        self.client = anthropic.Anthropic(api_key=api_key)
    
    def parse_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        Parse OED PDF and extract structured data
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dictionary with extracted OED entry data
        """
        # Extract text using pypdf
        try:
            text = self._extract_pdf_text(pdf_path)
        except Exception as e:
            logger.error(f"Failed to extract text from PDF: {e}")
            raise ValueError(f"Could not extract text from PDF: {e}")
        
        if not text:
            raise ValueError("No text could be extracted from PDF")
        
        # Parse with Claude
        result = self._parse_with_llm(text)
        
        # Add temporal analysis
        result['temporal_data'] = self._extract_temporal_patterns(result)
        
        return result
    
    def _extract_pdf_text(self, pdf_path: str) -> str:
        """Extract text from PDF using pypdf"""
        text = ""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = pypdf.PdfReader(file)
                num_pages = len(pdf_reader.pages)
                
                for page_num in range(num_pages):
                    page = pdf_reader.pages[page_num]
                    text += page.extract_text()
            
            return text
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            raise
    
    def _parse_with_llm(self, text: str) -> Dict[str, Any]:
        """Parse OED text using Claude - extract and format properly"""
        
        # Clean text to remove null characters that break PostgreSQL storage
        text = text.replace('\x00', '')  # Remove null characters

        # If the installed anthropic client doesn't support the messages API, fall back to
        # a lightweight local parse so tests can run without network or newer SDK features.
        try:
            has_messages = hasattr(self.client, "messages") and hasattr(self.client.messages, "create")  # type: ignore[attr-defined]
        except Exception:
            has_messages = False
        if not has_messages:
            logger.warning("Anthropic client lacks messages API; using minimal local parse fallback")
            return self._minimal_local_parse(text)
        
        # First, have Claude clean and extract only relevant OED content
        clean_prompt = """
        You are processing text extracted from an Oxford English Dictionary PDF. 
        The text contains the actual dictionary entry mixed with website navigation, cookie policies, and other irrelevant content.
        
        PRESERVE ALL dictionary content including:
        - Etymology (complete)
        - Pronunciations
        - ALL definitions and sub-definitions
        - ALL historical quotations with dates (CRITICAL: include EVERY dated quotation)
        - ALL usage notes
        - First recorded use
        - Related terms and compounds
        
        REMOVE ONLY:
        - Cookie policy and privacy text
        - Website navigation elements (e.g., "Accept All", "Cookie Settings")
        - Copyright notices
        - URLs like "https://www.oed.com/..."
        - Statistical methodology explanations about Google Books Ngrams
        - Browser interface elements
        - Text about "Oxford University Press uses cookies..."
        
        IMPORTANT: You must include EVERY historical quotation with its date and full text. Do not summarize or skip any quotations.
        Format the cleaned text preserving the complete dictionary structure.
        
        Text to clean:
        """ + text[:20000]  # Send more text to ensure we get all quotations
        
        try:
            # First pass: Clean the text
            clean_message = self.client.messages.create(  # type: ignore[attr-defined]
                model=os.environ.get("CLAUDE_DEFAULT_MODEL", "claude-sonnet-4-5-20250929"),
                max_tokens=8000,
                temperature=0.1,
                messages=[
                    {"role": "user", "content": clean_prompt}
                ]
            )
            
            cleaned_text = clean_message.content[0].text.strip()
            
            # Second pass: Extract structured data
            extract_prompt = """
            Extract structured data from this OED entry and return as JSON:
            
            {
                "headword": "the main term/word being defined",
                "first_recorded_use": "earliest year mentioned (just the year, e.g., 1721)",
                "historical_quotations": [
                    {
                        "year": 1721,
                        "text": "the quotation text"
                    }
                ]
            }
            
            Focus on extracting ALL dated quotations/examples for temporal tracking.
            Return ONLY the JSON object.
            
            OED Entry:
            """ + cleaned_text[:8000]
        
            # Extract structured data
            extract_message = self.client.messages.create(  # type: ignore[attr-defined]
                model=os.environ.get("CLAUDE_DEFAULT_MODEL", "claude-sonnet-4-5-20250929"),
                max_tokens=4000,
                temperature=0.2,
                messages=[
                    {"role": "user", "content": extract_prompt}
                ]
            )
            
            response_text = extract_message.content[0].text.strip()
            
            # Clean up response if it has markdown formatting
            if response_text.startswith('```'):
                response_text = response_text.split('```')[1]
                if response_text.startswith('json'):
                    response_text = response_text[4:]
            
            # Parse JSON
            result = json.loads(response_text)
            
            # Basic validation
            if not result.get('headword'):
                # Try to extract at least the headword from the beginning of text
                lines = text.split('\n')
                for line in lines[:5]:
                    line = line.strip()
                    if line and len(line.split()) <= 3:
                        result['headword'] = line.split()[0]
                        break
            
            # Store the CLEANED text, not the raw text with website junk
            result['full_text'] = cleaned_text
            
            # Ensure we have historical_quotations list
            if not result.get('historical_quotations'):
                result['historical_quotations'] = []
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude response as JSON: {e}")
            # Return minimal structure
            return {
                "headword": "Unknown",
                "definitions": [{"number": "1", "text": text[:500]}],
                "parse_error": str(e)
            }
        except Exception as e:
            logger.error(f"Error calling Claude API: {e}")
            # If Claude fails at runtime, also fall back to minimal local parse
            return self._minimal_local_parse(text)
    
    def _extract_temporal_patterns(self, oed_data: Dict) -> Dict:
        """Extract temporal patterns from OED data for experiments"""
        temporal = {
            "first_use": None,
            "usage_timeline": [],
            "semantic_shifts": [],
            "peak_periods": [],
            "century_distribution": {}
        }
        
        # Extract all dates from historical quotations
        all_dates = []
        
        for quote in oed_data.get('historical_quotations', []):
            year = quote.get('year')
            if year:
                try:
                    year_int = int(str(year))
                    all_dates.append({
                        'year': year_int,
                        'text': quote.get('text', ''),
                        'source': quote.get('source', ''),
                        'definition_context': quote.get('definition_context', '')
                    })
                except (ValueError, TypeError):
                    continue
        
        # Sort chronologically
        all_dates.sort(key=lambda x: x['year'])
        
        if all_dates:
            temporal['first_use'] = all_dates[0]['year']
            temporal['usage_timeline'] = all_dates
            
            # Calculate century distribution
            for date_info in all_dates:
                century = (date_info['year'] // 100) + 1
                century_key = f"{century}th century"
                temporal['century_distribution'][century_key] = \
                    temporal['century_distribution'].get(century_key, 0) + 1
            
            # Detect semantic shifts
            temporal['semantic_shifts'] = self._detect_semantic_shifts(all_dates)
        
        # Try to get first use from other fields
        if not temporal['first_use'] and oed_data.get('first_recorded_use'):
            try:
                temporal['first_use'] = int(oed_data['first_recorded_use'])
            except (ValueError, TypeError):
                pass
        
        return temporal
    
    def _detect_semantic_shifts(self, dated_entries: List[Dict]) -> List[Dict]:
        """Detect semantic shifts based on definition context changes over time"""
        shifts = []
        
        if len(dated_entries) < 2:
            return shifts
        
        # Group by century and track definition contexts
        century_contexts = {}
        for entry in dated_entries:
            century = (entry['year'] // 100) + 1
            context = entry.get('definition_context', '')
            
            if century not in century_contexts:
                century_contexts[century] = set()
            if context:
                century_contexts[century].add(context)
        
        # Detect when new contexts/meanings appear
        centuries = sorted(century_contexts.keys())
        for i in range(1, len(centuries)):
            prev_century = centuries[i-1]
            curr_century = centuries[i]
            
            new_contexts = century_contexts[curr_century] - century_contexts[prev_century]
            if new_contexts:
                shifts.append({
                    'period': f"{curr_century}th century",
                    'type': 'new_meanings',
                    'contexts': list(new_contexts)
                })
        
        return shifts

    def _minimal_local_parse(self, text: str) -> Dict[str, Any]:
        """Best-effort local parse when LLM is unavailable.

        - Headword: first short non-empty line (<= 3 words)
        - First recorded use: first 4-digit year found
        - Historical quotations: empty (we don't infer without LLM)
        - full_text: original text (trimmed)
        """
        lines = [ln.strip() for ln in text.splitlines()]
        headword: Optional[str] = None
        for ln in lines[:20]:
            if ln and len(ln.split()) <= 3:
                headword = ln.split()[0]
                break
        if not headword:
            headword = "Unknown"

        # Find first 4-digit year
        m = re.search(r"\b(1[5-9]\d{2}|20\d{2})\b", text)
        first_year: Optional[str] = m.group(0) if m else None

        result: Dict[str, Any] = {
            "headword": headword,
            "first_recorded_use": first_year,
            "historical_quotations": [],
            "full_text": text.strip(),
        }

        return result
