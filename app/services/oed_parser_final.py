"""
Production OED Parser using LangExtract

This is the final, production-ready version that properly uses LangExtract
for extracting structured data from OED PDFs.
"""

import os
import json
import logging
import re
from typing import Dict, List, Any, Optional
import pypdf
import langextract as lx
from langextract import data
import importlib.util
PDFPLUMBER_AVAILABLE = importlib.util.find_spec("pdfplumber") is not None

logger = logging.getLogger(__name__)


class OEDParser:
    """Production OED parser using LangExtract for structured extraction"""
    
    def __init__(self):
        """Initialize the OED parser with LangExtract"""
        # Check for Gemini API key (required for LangExtract)
        self.api_key = os.environ.get('GOOGLE_GEMINI_API_KEY') or os.environ.get('LANGEXTRACT_API_KEY')
        
        if not self.api_key:
            # Fall back to Anthropic if available
            self.api_key = os.environ.get('ANTHROPIC_API_KEY')
            self.use_anthropic_fallback = True
            logger.info("Using Anthropic fallback - LangExtract works best with Gemini API")
        else:
            self.use_anthropic_fallback = False
            logger.info("Using LangExtract with Gemini API")
        
        if not self.api_key:
            raise ValueError(
                "API key required. Set one of: GOOGLE_GEMINI_API_KEY, LANGEXTRACT_API_KEY, or ANTHROPIC_API_KEY"
            )
    
    def parse_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        Parse OED PDF and extract structured data using LangExtract
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dictionary with extracted OED entry data
        """
        # Step 1: Extract text (and layout if available) from PDF
        try:
            if PDFPLUMBER_AVAILABLE:
                layout = self._extract_pdf_layout(pdf_path)
                text = self._serialize_structured_text(layout)
                quote_candidates = self._extract_quote_candidates(layout)
            else:
                text = self._extract_pdf_text(pdf_path)
                quote_candidates = []
        except Exception as e:
            logger.error(f"Failed to extract text from PDF: {e}")
            raise ValueError(f"Could not extract text from PDF: {e}")
        
        if not text:
            raise ValueError("No text could be extracted from PDF")
        
        # Step 2: Parse with LangExtract or fallback
        if self.use_anthropic_fallback:
            result = self._parse_with_anthropic(text)
        else:
            result = self._parse_with_langextract(text)
        
        # Step 3: Add temporal analysis
        result['temporal_data'] = self._extract_temporal_patterns(result)
        # Merge detected quote candidates when helpful
        if quote_candidates:
            result = self._merge_quote_candidates(result, quote_candidates)
        
        return result
    
    def _extract_pdf_text(self, pdf_path: str) -> str:
        """Extract text from PDF using pypdf (successor of PyPDF2)"""
        text = ""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = pypdf.PdfReader(file)
                num_pages = len(pdf_reader.pages)
                
                for page_num in range(num_pages):
                    page = pdf_reader.pages[page_num]
                    text += page.extract_text() or ""
            
            # Clean null characters that break PostgreSQL
            text = text.replace('\x00', '')
            return text
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            raise
    
    def _parse_with_langextract(self, text: str) -> Dict[str, Any]:
        """Parse OED text using LangExtract for structured extraction"""
        
    # Define extraction schema and instruct usage of [QUOTE] lines if present
        prompt_description = """
        Extract dictionary entries from this Oxford English Dictionary text.
        
        For each entry, extract the main word and its attributes including:
        - headword: The main word being defined
        - etymology: The word's origin and etymology
        - first_year: The earliest recorded year (just the 4-digit year)
        - definitions: JSON array of all definitions with number and text
        - quotations: JSON array of ALL historical quotations with year, author, and text
        
    If the input includes lines formatted as:
    [QUOTE] year=1832 | text=Some quotation text ...
    prefer using those for quotations (they preserve the PDF's column alignment).
    Only include the year digits (strip prefixes like 'a' or 'c').
        
    Extract ALL historical quotations - do not skip any. Avoid mistakenly treating etymology text as quotations.
        """
        
        # Provide examples to guide extraction
        examples = [
            lx.data.ExampleData(
                text="ontology (n.) Etymology: From Latin ontologia. 1. The study of being. 1663 Harvey: 'Metaphysics is Ontology'",
                extractions=[
                    lx.data.Extraction(
                        extraction_class="dictionary_entry",
                        extraction_text="ontology",
                        attributes={
                            "headword": "ontology",
                            "etymology": "From Latin ontologia",
                            "first_year": "1663",
                            "definitions": json.dumps([{"number": "1", "text": "The study of being"}]),
                            "quotations": json.dumps([{
                                "year": "1663",
                                "author": "Harvey", 
                                "text": "Metaphysics is Ontology"
                            }])
                        }
                    )
                ]
            )
        ]
        
        try:
            # Extract using LangExtract
            result = lx.extract(
                text_or_documents=text[:20000],  # Process up to 20k chars
                prompt_description=prompt_description,
                examples=examples,
                model_id="gemini-2.0-flash-exp",
                api_key=self.api_key,
                format_type=lx.data.FormatType.JSON,
                temperature=0.1,
                max_char_buffer=3000,
                fence_output=False,
                use_schema_constraints=True,
                extraction_passes=2  # Multiple passes for better recall
            )
            
            # Process LangExtract results
            return self._process_langextract_results(result, text)
            
        except Exception as e:
            logger.error(f"Error using LangExtract: {e}")
            # Fall back to simple extraction
            return self._simple_extraction_fallback(text)

    def _extract_pdf_layout(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Extract layout-aware text using pdfplumber: words with coordinates grouped into lines/columns.
        Returns a list of pages; each page has 'width', 'height', and 'lines':
          line: { 'y': float, 'left': str, 'right': str }
        where 'left' is text of the left column segment (e.g., dates) and 'right' is the remaining text.
        """
        import importlib
        if not PDFPLUMBER_AVAILABLE:
            raise RuntimeError("pdfplumber not available")
        pdfplumber = importlib.import_module("pdfplumber")

        pages = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                width = page.width
                mid_x = width / 2.0
                words = page.extract_words(use_text_flow=True, keep_blank_chars=False)
                # Group by line using y0 within tolerance
                lines_map: Dict[int, List[Dict[str, Any]]] = {}
                tol = 2  # pixels
                for w in words:
                    y = int(round(w['top']))
                    bucket = None
                    for key in (y, y-1, y+1, y-2, y+2):
                        if key in lines_map:
                            bucket = key
                            break
                    if bucket is None:
                        lines_map[y] = [w]
                    else:
                        lines_map[bucket].append(w)
                # Assemble lines
                lines = []
                for y, ws in sorted(lines_map.items(), key=lambda kv: kv[0]):
                    left_tokens = []
                    right_tokens = []
                    for w in sorted(ws, key=lambda d: d['x0']):
                        (left_tokens if w['x1'] < mid_x * 0.9 else right_tokens).append(w['text'])
                    left_text = ' '.join(left_tokens).strip()
                    right_text = ' '.join(right_tokens).strip()
                    if left_text or right_text:
                        lines.append({'y': y, 'left': left_text, 'right': right_text})
                pages.append({'width': width, 'height': page.height, 'lines': lines})
        return pages

    def _extract_quote_candidates(self, pages: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Detect quote lines pairing dates (left column) with text (right column)."""
        candidates: List[Dict[str, str]] = []
        date_re = re.compile(r"^(?:[ac]\s*)?\d{3,4}(?:[–-]\d{1,2})?\??$", re.IGNORECASE)
        current: Optional[Dict[str, str]] = None
        for page in pages:
            for line in page['lines']:
                left = line['left']
                right = line['right']
                if left and date_re.match(left.strip()):
                    # Start a new quote block
                    if current and current.get('text'):
                        candidates.append(current)
                    year = re.sub(r"[^0-9]", "", left)[:4]
                    current = {'year': year, 'text': right.strip() if right else ''}
                else:
                    # Continuation of quote text
                    if current and right:
                        if current['text']:
                            current['text'] += ' ' + right.strip()
                        else:
                            current['text'] = right.strip()
        if current and current.get('text'):
            candidates.append(current)
        # Filter empty texts and deduplicate simple duplicates
        seen = set()
        deduped = []
        for c in candidates:
            key = (c.get('year'), (c.get('text') or '')[:80])
            if key not in seen and c.get('year') and c.get('text'):
                seen.add(key)
                deduped.append(c)
        return deduped

    def _serialize_structured_text(self, pages: List[Dict[str, Any]]) -> str:
        """Serialize layout into a structured text the LLM can reliably interpret, preserving order.
        Quote lines are emitted as [QUOTE] year=YYYY | text=....
        Other lines are emitted with [L] and [R] markers to keep left/right content visible.
        """
        out_lines: List[str] = []
        date_re = re.compile(r"^(?:[ac]\s*)?\d{3,4}(?:[–-]\d{1,2})?\??$", re.IGNORECASE)
        for i, page in enumerate(pages, start=1):
            out_lines.append(f"[PAGE {i}]")
            for line in page['lines']:
                left = (line.get('left') or '').strip()
                right = (line.get('right') or '').strip()
                if left and date_re.match(left):
                    year = re.sub(r"[^0-9]", "", left)[:4]
                    out_lines.append(f"[QUOTE] year={year} | text={right}")
                else:
                    # Keep both columns so the LLM can recover other structure
                    if left or right:
                        out_lines.append(f"[L] {left}")
                        if right:
                            out_lines.append(f"[R] {right}")
            out_lines.append("")
        return "\n".join(out_lines)

    def _merge_quote_candidates(self, result: Dict[str, Any], candidates: List[Dict[str, str]]) -> Dict[str, Any]:
        """Merge geometry-detected quotes with LLM results to preserve correct date→text pairing."""
        existing = result.get('historical_quotations') or []
        # Basic heuristic: if LLM provided few or mismatched quotes, enrich/replace
        if len(existing) < max(2, len(candidates) // 2):
            merged = []
            for c in candidates:
                merged.append({
                    'year': c.get('year'),
                    'author': None,
                    'text': c.get('text')
                })
            result['historical_quotations'] = merged
        else:
            # Ensure each LLM quote has a year; fill from nearest candidate if missing
            for q in existing:
                if not q.get('year') and candidates:
                    q['year'] = candidates[0].get('year')
        return result
    
    def _process_langextract_results(self, result: Any, original_text: str) -> Dict[str, Any]:
        """Process LangExtract results into our expected format"""
        
        extracted_data = {
            "headword": None,
            "etymology": None,
            "pronunciation": None,
            "first_recorded_use": None,
            "definitions": [],
            "historical_quotations": [],
            "related_terms": [],
            "full_text": None
        }
        
        # Combine extractions from all entries
        all_quotations = []
        all_definitions = []
        
        if hasattr(result, 'extractions'):
            for extraction in result.extractions:
                if extraction.attributes:
                    attrs = extraction.attributes
                    
                    # Get headword from first extraction
                    if not extracted_data['headword']:
                        extracted_data['headword'] = attrs.get('headword')
                        extracted_data['etymology'] = attrs.get('etymology')
                        extracted_data['first_recorded_use'] = attrs.get('first_year')
                    
                    # Parse and collect definitions
                    defs_str = attrs.get('definitions', '[]')
                    try:
                        defs = json.loads(defs_str) if isinstance(defs_str, str) else defs_str
                        if isinstance(defs, list):
                            all_definitions.extend(defs)
                    except:
                        pass
                    
                    # Parse and collect quotations
                    quotes_str = attrs.get('quotations', '[]')
                    try:
                        quotes = json.loads(quotes_str) if isinstance(quotes_str, str) else quotes_str
                        if isinstance(quotes, list):
                            all_quotations.extend(quotes)
                    except:
                        pass
        
        # Store combined results
        extracted_data['definitions'] = all_definitions
        extracted_data['historical_quotations'] = all_quotations
        
        # Clean and store full text
        extracted_data['full_text'] = self._clean_text_for_storage(original_text)
        
        # Ensure first_recorded_use is set from quotations if needed
        if not extracted_data['first_recorded_use'] and all_quotations:
            years = []
            for q in all_quotations:
                year_str = str(q.get('year', '')).strip('a')  # Remove 'a' prefix from dates like 'a1832'
                try:
                    year = int(year_str)
                    years.append(year)
                except:
                    pass
            if years:
                extracted_data['first_recorded_use'] = str(min(years))
        
        logger.info(f"Extracted {len(all_definitions)} definitions and {len(all_quotations)} quotations")
        
        return extracted_data
    
    def _clean_text_for_storage(self, text: str) -> str:
        """Remove website boilerplate and clean text for storage"""
        
        # Patterns to remove
        remove_patterns = [
            "Oxford University Press uses cookies",
            "Cookie Policy",
            "Accept All",
            "Cookie Settings",
            "https://www.oed.com",
            "Google Books Ngrams",
            "By selecting 'accept all'"
        ]
        
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Skip lines containing unwanted patterns
            if not any(pattern in line for pattern in remove_patterns):
                cleaned_lines.append(line)
        
        cleaned = '\n'.join(cleaned_lines)
        return cleaned[:50000]  # Limit to 50k chars
    
    def _parse_with_anthropic(self, text: str) -> Dict[str, Any]:
        """Fallback parser using Anthropic Claude"""
        import anthropic
        
        client: Any = anthropic.Anthropic(api_key=self.api_key)
        
        prompt = """
        Extract structured data from this Oxford English Dictionary entry.
        Remove all website navigation and cookie text.
        
        Return JSON with this structure:
        {
            "headword": "main word",
            "etymology": "word origin",
            "first_recorded_use": "earliest year",
            "definitions": [{"number": "1", "text": "definition"}],
            "historical_quotations": [
                {"year": "1663", "author": "Author", "text": "quotation"}
            ]
        }
        
        Include ALL historical quotations.
        
        Text:
        """ + text[:20000]
        
        try:
            message = client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=8000,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response = message.content[0].text.strip()
            
            # Extract JSON
            if '```' in response:
                response = response.split('```')[1]
                if response.startswith('json'):
                    response = response[4:]
            
            result = json.loads(response)
            result['full_text'] = self._clean_text_for_storage(text)
            
            return result
            
        except Exception as e:
            logger.error(f"Anthropic parsing failed: {e}")
            return self._simple_extraction_fallback(text)
    
    def _simple_extraction_fallback(self, text: str) -> Dict[str, Any]:
        """Simple fallback when other methods fail"""
        
        lines = text.split('\n')
        headword = "unknown"
        
        for line in lines[:10]:
            line = line.strip()
            if line and not line.startswith('http') and len(line.split()) <= 3:
                headword = line.split(',')[0].split()[0]
                break
        
        return {
            "headword": headword,
            "etymology": None,
            "pronunciation": None,
            "first_recorded_use": None,
            "definitions": [{"number": "1", "text": text[:500]}],
            "historical_quotations": [],
            "related_terms": [],
            "full_text": self._clean_text_for_storage(text)
        }
    
    def _extract_temporal_patterns(self, oed_data: Dict) -> Dict:
        """Extract temporal patterns for experiments"""
        
        temporal = {
            "first_use": None,
            "usage_timeline": [],
            "semantic_shifts": [],
            "peak_periods": [],
            "century_distribution": {}
        }
        
        all_dates = []
        
        for quote in oed_data.get('historical_quotations', []):
            year_str = str(quote.get('year', '')).strip('a')
            try:
                year = int(year_str)
                all_dates.append({
                    'year': year,
                    'text': quote.get('text', ''),
                    'author': quote.get('author', '')
                })
            except:
                continue
        
        # Sort chronologically
        all_dates.sort(key=lambda x: x['year'])
        
        if all_dates:
            temporal['first_use'] = all_dates[0]['year']
            temporal['usage_timeline'] = all_dates
            
            # Calculate century distribution
            for entry in all_dates:
                century = (entry['year'] // 100) + 1
                century_key = f"{century}th century"
                temporal['century_distribution'][century_key] = \
                    temporal['century_distribution'].get(century_key, 0) + 1
        
        # Get first use from field if not from quotations
        if not temporal['first_use'] and oed_data.get('first_recorded_use'):
            try:
                temporal['first_use'] = int(oed_data['first_recorded_use'])
            except:
                pass
        
        return temporal
