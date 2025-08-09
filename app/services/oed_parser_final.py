"""
Production OED Parser using LangExtract

This is the final, production-ready version that properly uses LangExtract
for extracting structured data from OED PDFs.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
import PyPDF2
import langextract as lx
from langextract import data

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
        # Step 1: Extract text from PDF
        try:
            text = self._extract_pdf_text(pdf_path)
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
        
        return result
    
    def _extract_pdf_text(self, pdf_path: str) -> str:
        """Extract text from PDF using PyPDF2"""
        text = ""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                num_pages = len(pdf_reader.pages)
                
                for page_num in range(num_pages):
                    page = pdf_reader.pages[page_num]
                    text += page.extract_text()
            
            # Clean null characters that break PostgreSQL
            text = text.replace('\x00', '')
            return text
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            raise
    
    def _parse_with_langextract(self, text: str) -> Dict[str, Any]:
        """Parse OED text using LangExtract for structured extraction"""
        
        # Define extraction schema
        prompt_description = """
        Extract dictionary entries from this Oxford English Dictionary text.
        
        For each entry, extract the main word and its attributes including:
        - headword: The main word being defined
        - etymology: The word's origin and etymology
        - first_year: The earliest recorded year (just the 4-digit year)
        - definitions: JSON array of all definitions with number and text
        - quotations: JSON array of ALL historical quotations with year, author, and text
        
        Extract ALL historical quotations - do not skip any.
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
        
        client = anthropic.Anthropic(api_key=self.api_key)
        
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
                model="claude-3-5-sonnet-20241022",
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
