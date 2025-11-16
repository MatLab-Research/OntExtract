"""
Quotation Extractor

Extracts and analyzes quotation information from OED data.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import re
from app import db
from app.models.term import Term
from app.models.oed_models import OEDQuotationSummary


class QuotationExtractor:
    """Handles quotation extraction and analysis"""

    def extract_and_store(self, term: Term, quotations_data: Dict, entry_id: str) -> Dict[str, Any]:
        """Extract quotation metadata and store in OEDQuotationSummary table"""
        result = {"created": 0, "errors": []}

        try:
            quotations = self._parse_quotations(quotations_data)

            for i, quotation in enumerate(quotations):
                try:
                    summary = OEDQuotationSummary(
                        term_id=term.id,
                        quotation_year=quotation.get('year'),
                        author_name=quotation.get('author'),
                        work_title=quotation.get('work_title'),
                        domain_context=self._infer_domain_context(quotation.get('work_title', '')),
                        usage_type=self._classify_usage_type(quotation.get('text', '')),
                        has_technical_usage=self._detect_technical_usage(quotation.get('text', '')),
                        represents_semantic_shift=self._detect_semantic_shift(quotation.get('text', ''), i, quotations),
                        chronological_rank=i + 1,
                        # PROV-O Entity metadata
                        generated_at_time=datetime.utcnow(),
                        was_attributed_to="OED_Quotation_Extractor",
                        was_derived_from=f"{entry_id}_quotation_{i+1}",
                        derivation_type="metadata_extraction"
                    )

                    db.session.add(summary)
                    result["created"] += 1

                except Exception as e:
                    result["errors"].append(f"Quotation {i+1} extraction error: {str(e)}")
                    continue

        except Exception as e:
            result["errors"].append(f"Quotations extraction error: {str(e)}")

        return result

    def _parse_quotations(self, quotations_data: Dict) -> List[Dict[str, Any]]:
        """Parse quotations from OED quotations data"""
        quotations = []

        # Handle different possible structures
        if 'quotations' in quotations_data:
            quotes = quotations_data['quotations']
        elif isinstance(quotations_data, list):
            quotes = quotations_data
        else:
            return quotations

        for quote in quotes:
            if isinstance(quote, dict):
                quotations.append({
                    'year': self._extract_year(quote),
                    'author': quote.get('author', ''),
                    'work_title': quote.get('work_title', quote.get('source', '')),
                    'text': quote.get('text', quote.get('quotation', ''))
                })

        return sorted(quotations, key=lambda x: x['year'] or 0)

    def _extract_year(self, quotation: Dict) -> Optional[int]:
        """Extract year from quotation data"""
        year_fields = ['year', 'date', 'publication_date']
        for field in year_fields:
            if field in quotation and quotation[field]:
                try:
                    year_str = str(quotation[field])
                    year_match = re.search(r'\b(1[0-9]{3}|20[0-2][0-9])\b', year_str)
                    if year_match:
                        return int(year_match.group(1))
                except (ValueError, TypeError):
                    continue
        return None

    def _infer_domain_context(self, work_title: str) -> Optional[str]:
        """Infer domain context from work title"""
        domain_keywords = {
            'Law': ['law', 'legal', 'court', 'statute', 'constitution'],
            'Philosophy': ['philosophy', 'ethics', 'logic', 'metaphysics'],
            'Literature': ['novel', 'poem', 'poetry', 'literature'],
            'Science': ['science', 'nature', 'natural', 'experiment'],
            'Economics': ['economics', 'wealth', 'money', 'commerce']
        }

        title_lower = work_title.lower()
        for domain, keywords in domain_keywords.items():
            if any(keyword in title_lower for keyword in keywords):
                return domain

        return None

    def _classify_usage_type(self, quotation_text: str) -> str:
        """Classify the type of usage in quotation"""
        if not quotation_text:
            return "unknown"

        text_lower = quotation_text.lower()

        if any(indicator in text_lower for indicator in ['metaphor', 'like', 'as if']):
            return "metaphorical"
        elif any(indicator in text_lower for indicator in ['technical', 'specifically', 'defined as']):
            return "technical"
        else:
            return "literal"

    def _detect_technical_usage(self, quotation_text: str) -> bool:
        """Detect if quotation represents technical usage"""
        technical_indicators = ['defined', 'technical', 'specifically', 'terminology', 'jargon']
        text_lower = quotation_text.lower() if quotation_text else ""
        return any(indicator in text_lower for indicator in technical_indicators)

    def _detect_semantic_shift(self, quotation_text: str, index: int, all_quotations: List[Dict]) -> bool:
        """Detect if quotation represents a semantic shift"""
        # Simple heuristic: if usage differs significantly from previous quotations
        if index == 0:
            return False

        # More sophisticated analysis could be implemented here
        return False
