"""
OED Temporal Extraction Service

Extracts temporal timeline data from Oxford English Dictionary entries.
First node in the LangGraph temporal analysis pipeline.

Based on "Managing Semantic Change in Research" framework (Rauch et al., 2024)
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import json
import re
from pathlib import Path

from app import db
from app.models.term import Term
from app.utils.file_handler import FileHandler


@dataclass
class OEDTimelineMarker:
    """Represents a single point on the OED timeline"""
    year: Optional[int]
    period_label: str
    century: Optional[int]
    sense_number: str
    definition: str
    definition_short: str
    first_recorded_use: Optional[str]
    quotation_date: Optional[str]
    quotation_author: Optional[str]
    quotation_work: Optional[str]
    semantic_category: Optional[str]
    etymology_note: Optional[str]
    marker_type: str  # "etymology", "sense", "usage"
    display_order: int


class OEDTemporalExtractor:
    """
    Extracts temporal timeline markers from OED entries.

    This is the first node in the temporal analysis LangGraph pipeline.
    It identifies:
    - Etymology and earliest attestations
    - Historical senses and their first uses
    - Semantic shifts across time periods
    - Quotations showing usage evolution
    """

    def __init__(self, anthropic_api_key: Optional[str] = None):
        """Initialize the extractor with optional API key for LLM"""
        self.file_handler = FileHandler()
        self.api_key = anthropic_api_key

    def extract_from_pdf(self, pdf_path: str, term_text: str) -> List[OEDTimelineMarker]:
        """
        Extract timeline markers from an OED PDF entry.

        Args:
            pdf_path: Path to OED PDF file
            term_text: The term being analyzed (e.g., "agent")

        Returns:
            List of OEDTimelineMarker objects ordered chronologically
        """
        # Extract text from PDF
        content = self.file_handler.extract_text_from_file(pdf_path, Path(pdf_path).name)

        if not content:
            raise ValueError(f"Could not extract text from PDF: {pdf_path}")

        # Use LLM to parse OED structure and extract timeline data
        markers = self._parse_oed_with_llm(content, term_text)

        # Sort chronologically
        markers.sort(key=lambda m: (m.year or 9999, m.display_order))

        return markers

    def _parse_oed_with_llm(self, oed_text: str, term_text: str) -> List[OEDTimelineMarker]:
        """
        Use LLM to parse OED entry and extract structured timeline data.

        This handles the complex OED format with multiple senses, subsenses,
        quotations, and historical information.
        """
        # Import Claude only when needed (lazy import)
        try:
            from anthropic import Anthropic
        except ImportError:
            raise ImportError("anthropic package required for OED extraction. Install with: pip install anthropic")

        client = Anthropic()

        prompt = f"""Analyze this Oxford English Dictionary entry for the term "{term_text}" and extract ALL temporal information.

OED Entry Text:
{oed_text[:15000]}  # Limit to avoid token limits

Extract a comprehensive timeline of semantic evolution. For each historical period, sense, or usage:

Return a JSON array of timeline markers with this structure:
[
  {{
    "year": <integer year or null>,
    "period_label": "<string like 'Old English', 'Middle English', '15th century'>",
    "century": <integer century number or null>,
    "sense_number": "<string like '1', '1a', '2b'>",
    "definition": "<full definition text>",
    "definition_short": "<abbreviated version for timeline display, max 100 chars>",
    "first_recorded_use": "<quoted text showing first usage or null>",
    "quotation_date": "<date string from quotation or null>",
    "quotation_author": "<author name or null>",
    "quotation_work": "<work title or null>",
    "semantic_category": "<category like 'legal', 'philosophical', 'computational', 'general' or null>",
    "etymology_note": "<etymology information or null>",
    "marker_type": "<'etymology' or 'sense' or 'usage'>",
    "display_order": <integer for ordering within same year>
  }}
]

IMPORTANT INSTRUCTIONS:
1. Extract EVERY sense and subsense (1, 1a, 1b, 2, 2a, etc.) as separate markers
2. Include the etymology as a marker (marker_type='etymology')
3. For each sense, extract the FIRST quotation showing usage
4. Identify semantic categories based on the definition content:
   - "legal" if related to law, contracts, agency relationships
   - "philosophical" if related to intentionality, moral responsibility, action theory
   - "computational" if related to software, AI, autonomous systems
   - "general" for everyday usage
5. Convert period labels to approximate years when possible:
   - "Old English" → year: 1000
   - "Middle English" → year: 1300
   - "15th century" → year: 1450 (use mid-century)
   - Specific years like "1721" → year: 1721
6. Keep definition_short under 100 characters but preserve key meaning
7. Order by display_order: etymology=0, sense 1=1, sense 1a=2, sense 2=3, etc.

Return ONLY the JSON array, no other text."""

        # Call Claude API
        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4000,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )

        # Parse response
        response_text = message.content[0].text.strip()

        # Extract JSON from response (handle markdown code blocks)
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
            response_text = response_text.strip()

        try:
            markers_data = json.loads(response_text)
        except json.JSONDecodeError as e:
            raise ValueError(f"LLM returned invalid JSON: {e}\nResponse: {response_text[:500]}")

        # Convert to OEDTimelineMarker objects
        markers = []
        for data in markers_data:
            marker = OEDTimelineMarker(
                year=data.get("year"),
                period_label=data.get("period_label", ""),
                century=data.get("century"),
                sense_number=data.get("sense_number", ""),
                definition=data.get("definition", ""),
                definition_short=data.get("definition_short", "")[:100],
                first_recorded_use=data.get("first_recorded_use"),
                quotation_date=data.get("quotation_date"),
                quotation_author=data.get("quotation_author"),
                quotation_work=data.get("quotation_work"),
                semantic_category=data.get("semantic_category"),
                etymology_note=data.get("etymology_note"),
                marker_type=data.get("marker_type", "sense"),
                display_order=data.get("display_order", 99)
            )
            markers.append(marker)

        return markers

    def save_to_database(self, term_id: str, markers: List[OEDTimelineMarker],
                         oed_entry_id: str = "agent_nn01") -> int:
        """
        Save extracted timeline markers to database.

        Args:
            term_id: UUID of the term
            markers: List of extracted timeline markers
            oed_entry_id: OED entry identifier

        Returns:
            Number of markers saved
        """
        from app.models.temporal_experiment import OEDTimelineMarker as DBMarker

        # Delete existing markers for this term (fresh extraction)
        db.session.query(DBMarker).filter_by(term_id=term_id).delete()

        # Insert new markers
        for marker in markers:
            db_marker = DBMarker(
                term_id=term_id,
                year=marker.year,
                period_label=marker.period_label,
                century=marker.century,
                sense_number=marker.sense_number,
                definition=marker.definition,
                definition_short=marker.definition_short,
                first_recorded_use=marker.first_recorded_use,
                quotation_date=marker.quotation_date,
                quotation_author=marker.quotation_author,
                quotation_work=marker.quotation_work,
                semantic_category=marker.semantic_category,
                etymology_note=marker.etymology_note,
                marker_type=marker.marker_type,
                display_order=marker.display_order,
                oed_entry_id=oed_entry_id,
                extracted_by="llm",
                extraction_date=datetime.utcnow()
            )
            db.session.add(db_marker)

        db.session.commit()
        return len(markers)

    def extract_and_save(self, term_text: str, pdf_path: str,
                         oed_entry_id: str = "agent_nn01") -> Dict[str, Any]:
        """
        Complete extraction and save pipeline.

        Args:
            term_text: Term to extract timeline for
            pdf_path: Path to OED PDF
            oed_entry_id: OED entry identifier

        Returns:
            Dictionary with extraction results and statistics
        """
        # Find term in database
        term = Term.query.filter_by(term_text=term_text).first()
        if not term:
            raise ValueError(f"Term '{term_text}' not found in database")

        # Extract markers
        markers = self.extract_from_pdf(pdf_path, term_text)

        # Save to database
        saved_count = self.save_to_database(str(term.id), markers, oed_entry_id)

        # Generate summary statistics
        stats = {
            "term": term_text,
            "term_id": str(term.id),
            "markers_extracted": len(markers),
            "markers_saved": saved_count,
            "year_range": {
                "earliest": min((m.year for m in markers if m.year), default=None),
                "latest": max((m.year for m in markers if m.year), default=None)
            },
            "senses_count": len([m for m in markers if m.marker_type == "sense"]),
            "etymology_found": any(m.marker_type == "etymology" for m in markers),
            "semantic_categories": list(set(m.semantic_category for m in markers if m.semantic_category)),
            "extraction_timestamp": datetime.utcnow().isoformat()
        }

        return {
            "status": "success",
            "statistics": stats,
            "markers": [
                {
                    "year": m.year,
                    "period": m.period_label,
                    "sense": m.sense_number,
                    "definition_short": m.definition_short,
                    "category": m.semantic_category
                }
                for m in markers
            ]
        }


# Convenience function for direct usage
def extract_oed_timeline(term_text: str, oed_pdf_path: str) -> Dict[str, Any]:
    """
    Extract and save OED timeline for a term.

    Usage:
        result = extract_oed_timeline("agent", "/path/to/oed_agent.pdf")
    """
    extractor = OEDTemporalExtractor()
    return extractor.extract_and_save(term_text, oed_pdf_path)
