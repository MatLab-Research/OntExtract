"""
Enhanced OED (Oxford English Dictionary) PDF Parser using LangExtract

Uses LangExtract for intelligent structured extraction from OED PDFs.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
import pypdf
import langextract as lx
from langextract import data

logger = logging.getLogger(__name__)


class OEDParserLangExtract:
    """Enhanced OED parser using LangExtract for structured extraction"""
    
    def __init__(self):
        """Initialize the OED parser with LangExtract"""
        # Check for API key - can use either Anthropic or Gemini
        self.api_key = os.environ.get('ANTHROPIC_API_KEY') or os.environ.get('GOOGLE_GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("API key required: Set either ANTHROPIC_API_KEY or GOOGLE_GEMINI_API_KEY")
        
        # Determine which model to use based on available API key
        if os.environ.get('GOOGLE_GEMINI_API_KEY'):
            self.model_id = "gemini-2.0-flash-exp"
            self.language_model_type = lx.inference.GeminiLanguageModel
        else:
            # For Anthropic, we'll still need to use the existing approach
            # as LangExtract primarily supports Gemini natively
            self.model_id = "claude-3-5-sonnet-20241022"
            self.use_anthropic_fallback = True
    
    def parse_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        Parse OED PDF and extract structured data using LangExtract
        
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
        
        # Clean null characters that break PostgreSQL
        text = text.replace('\x00', '')
        
        # Parse with LangExtract
        result = self._parse_with_langextract(text)
        
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
    
    def _parse_with_langextract(self, text: str) -> Dict[str, Any]:
        """Parse OED text using LangExtract for structured extraction"""
        
        # Define the extraction schema for OED entries
        prompt_description = """
        Extract structured information from an Oxford English Dictionary entry.
        
        IMPORTANT: Extract ALL historical quotations with their dates. Do not skip any.
        Remove any website navigation, cookie policies, or non-dictionary content.
        
        For each entry, extract:
        - headword: The main word being defined (e.g., "ontology")
        - etymology: Complete etymology and origin information
        - pronunciation: Pronunciation guide (British and US if available)
        - first_recorded_use: The earliest year the word was used (just the year number)
        - definitions: Array of all definitions with their numbers and text
        - historical_quotations: ALL dated quotations showing word usage through history
        - related_terms: Any related words, compounds, or derivatives
        """
        
        # Provide examples to guide the extraction
        examples = [
            data.ExampleData(
                text="""ontology, n.
                Etymology: < post-classical Latin ontologia
                Pronunciation: Brit. /ɒnˈtɒlədʒi/, U.S. /ɑnˈtɑlədʒi/
                
                1. Philosophy. The science or study of being.
                
                1663 G. Harvey Archelogia: Metaphysics..is called also Ontology
                1721 N. Bailey: Ontology, an Account of being in the Abstract
                1776 A. Smith: the cobweb science of Ontology""",
                extractions=[
                    data.Extraction(
                        extraction_class="oed_entry",
                        extraction_text="ontology",
                        attributes={
                            "headword": "ontology",
                            "etymology": "< post-classical Latin ontologia",
                            "pronunciation": "Brit. /ɒnˈtɒlədʒi/, U.S. /ɑnˈtɑlədʒi/",
                            "first_recorded_use": "1663",
                            "definitions": [
                                "1. Philosophy. The science or study of being."
                            ],
                            "historical_quotations": [
                                "1663 G. Harvey (Archelogia): Metaphysics..is called also Ontology",
                                "1721 N. Bailey: Ontology, an Account of being in the Abstract",
                                "1776 A. Smith: the cobweb science of Ontology"
                            ],
                        },
                    )
                ],
            )
        ]
        
        try:
            # Use LangExtract with Gemini if API key available
            if os.environ.get('GOOGLE_GEMINI_API_KEY'):
                # Extract using LangExtract with Gemini
                annotated_doc = lx.extract(
                    text_or_documents=text[:20000],  # Limit text length for processing
                    prompt_description=prompt_description,
                    examples=examples,
                    model_id=self.model_id,
                    api_key=self.api_key,
                    language_model_type=self.language_model_type,
                    format_type=data.FormatType.JSON,
                    temperature=0.1,  # Low temperature for consistent extraction
                    fence_output=False,
                    use_schema_constraints=True,
                    extraction_passes=2,  # Multiple passes to catch all quotations
                    max_char_buffer=2000,  # Process in larger chunks
                    batch_length=5,
                    max_workers=5
                )
                
                # Process the extracted data
                result = self._process_langextract_results(annotated_doc, text)
                return result
            else:
                # Fall back to Anthropic if Gemini API key not available
                logger.warning("GOOGLE_GEMINI_API_KEY not found, falling back to Anthropic Claude")
                return self._parse_with_anthropic_fallback(text)
            
        except Exception as e:
            logger.error(f"Error using LangExtract: {e}")
            # Fall back to a simpler extraction
            return self._simple_extraction_fallback(text)
    
    def _process_langextract_results(self, annotated_doc: Any, original_text: str) -> Dict[str, Any]:
        """Process LangExtract results into our expected format"""
        
        result = {
            "headword": None,
            "etymology": None,
            "pronunciation": None,
            "first_recorded_use": None,
            "definitions": [],
            "historical_quotations": [],
            "related_terms": [],
            "full_text": None
        }
        
        # Extract data from annotated document
        if annotated_doc and hasattr(annotated_doc, 'extractions'):
            for extraction in annotated_doc.extractions:
                if extraction.data:
                    # Merge extracted data into result
                    for key, value in extraction.data.items():
                        if key in result and value:
                            if isinstance(result[key], list) and isinstance(value, list):
                                result[key].extend(value)
                            elif result[key] is None:
                                result[key] = value
        
        # Store the cleaned full text (remove website boilerplate)
        result['full_text'] = self._clean_text_for_storage(original_text)
        
        # Ensure we have historical quotations as a list
        if not isinstance(result.get('historical_quotations'), list):
            result['historical_quotations'] = []
        
        # Deduplicate quotations if needed
        seen = set()
        unique_quotes = []
        for quote in result['historical_quotations']:
            key = (quote.get('year'), quote.get('text', '')[:50])
            if key not in seen:
                seen.add(key)
                unique_quotes.append(quote)
        result['historical_quotations'] = unique_quotes
        
        return result
    
    def _clean_text_for_storage(self, text: str) -> str:
        """Remove website boilerplate and clean text for storage"""
        
        # Common patterns to remove
        remove_patterns = [
            "Oxford University Press uses cookies",
            "Cookie Policy",
            "Accept All",
            "Cookie Settings",
            "https://www.oed.com",
            "Historical frequency series are derived from Google Books",
            "Smoothing has been applied to series",
            "By selecting 'accept all'",
            "More information can be found"
        ]
        
        cleaned = text
        for pattern in remove_patterns:
            # Remove lines containing these patterns
            lines = cleaned.split('\n')
            cleaned_lines = []
            for line in lines:
                if not any(pattern in line for pattern in remove_patterns):
                    cleaned_lines.append(line)
            cleaned = '\n'.join(cleaned_lines)
        
        # Limit to reasonable length
        return cleaned[:50000]
    
    def _parse_with_anthropic_fallback(self, text: str) -> Dict[str, Any]:
        """Fallback to use Anthropic Claude directly when LangExtract doesn't support it"""
        import anthropic
        
        client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))
        
        # Clean the text first
        clean_prompt = """
        Extract and format ONLY the dictionary content from this OED entry.
        Remove all website navigation, cookie policies, and non-dictionary text.
        
        Return a JSON object with this structure:
        {
            "headword": "the main word",
            "etymology": "complete etymology",
            "pronunciation": "pronunciation guide",
            "first_recorded_use": "earliest year (number only)",
            "definitions": [
                {"number": "1", "text": "definition text"}
            ],
            "historical_quotations": [
                {"year": "1663", "author": "Author Name", "text": "quotation text"}
            ],
            "related_terms": ["term1", "term2"],
            "full_text": "cleaned complete text"
        }
        
        IMPORTANT: Include ALL historical quotations, not just a sample.
        
        Text to process:
        """ + text[:20000]
        
        try:
            message = client.messages.create(  # type: ignore[attr-defined]
                model="claude-3-5-sonnet-20241022",
                max_tokens=8000,
                temperature=0.1,
                messages=[{"role": "user", "content": clean_prompt}]
            )
            
            response_text = message.content[0].text.strip()
            
            # Extract JSON from response
            if response_text.startswith('```'):
                response_text = response_text.split('```')[1]
                if response_text.startswith('json'):
                    response_text = response_text[4:]
            
            result = json.loads(response_text)
            
            # Ensure full_text is properly cleaned
            if not result.get('full_text'):
                result['full_text'] = self._clean_text_for_storage(text)
            
            return result
            
        except Exception as e:
            logger.error(f"Anthropic fallback failed: {e}")
            return self._simple_extraction_fallback(text)
    
    def _simple_extraction_fallback(self, text: str) -> Dict[str, Any]:
        """Simple fallback extraction when other methods fail"""
        
        # Extract headword (usually first word/line)
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
                        'author': quote.get('author', ''),
                        'work': quote.get('work', '')
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
        
        # Try to get first use from other fields
        if not temporal['first_use'] and oed_data.get('first_recorded_use'):
            try:
                temporal['first_use'] = int(oed_data['first_recorded_use'])
            except (ValueError, TypeError):
                pass
        
        return temporal
