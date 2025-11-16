"""
Definition Extractor

Extracts and analyzes definition information from OED data.
"""

from typing import Dict, Optional, Any
from datetime import datetime
import re
from app import db
from app.models.term import Term
from app.models.oed_models import OEDDefinition


class DefinitionExtractor:
    """Handles definition extraction and analysis"""

    def extract_and_store(self, term: Term, word_data: Dict, entry_id: str) -> Dict[str, Any]:
        """Extract definitions with temporal context and store in OEDDefinition table"""
        result = {"created": 0, "errors": []}

        try:
            # Get extracted senses from OED service
            senses = word_data.get('extracted_senses', [])

            for i, sense in enumerate(senses):
                try:
                    # Extract temporal information from definition
                    temporal_info = self._extract_temporal_context(sense.get('definition', ''))

                    # Determine historical period
                    historical_period = self._map_to_historical_period(
                        temporal_info.get('first_year'),
                        temporal_info.get('last_year')
                    )

                    # Create excerpt (first 300 chars) and OED URL
                    definition_text = sense.get('definition', '')
                    definition_excerpt = (definition_text[:297] + '...') if len(definition_text) > 300 else definition_text

                    # Generate OED URL for this sense
                    sense_id = sense.get('sense_id') or f"{entry_id}#{i+1}"
                    oed_url = f"https://www.oed.com/dictionary/{term.term_text.lower()}_{entry_id.split('_')[-1]}#{sense_id}"

                    definition = OEDDefinition(
                        term_id=term.id,
                        definition_number=sense.get('label', f"{i+1}"),
                        definition_excerpt=definition_excerpt,
                        oed_sense_id=sense_id,
                        oed_url=oed_url,
                        first_cited_year=temporal_info.get('first_year'),
                        last_cited_year=temporal_info.get('last_year'),
                        part_of_speech=self._extract_part_of_speech(word_data, sense),
                        domain_label=self._extract_domain_label(sense.get('definition', '')),
                        status=self._determine_status(sense.get('definition', '')),
                        quotation_count=temporal_info.get('quotation_count', 0),
                        sense_frequency_rank=i + 1,
                        historical_period=historical_period,
                        period_start_year=temporal_info.get('first_year'),
                        period_end_year=temporal_info.get('last_year'),
                        definition_confidence='medium',
                        # PROV-O Entity metadata
                        generated_at_time=datetime.utcnow(),
                        was_attributed_to="OED_API_Service",
                        was_derived_from=f"{entry_id}#{sense.get('label', f'{i+1}')}",
                        derivation_type="definition_extraction"
                    )

                    db.session.add(definition)
                    result["created"] += 1

                except Exception as e:
                    result["errors"].append(f"Definition {i+1} extraction error: {str(e)}")
                    continue

        except Exception as e:
            result["errors"].append(f"Definitions extraction error: {str(e)}")

        return result

    def _extract_temporal_context(self, definition_text: str) -> Dict[str, Any]:
        """Extract temporal context from definition text"""
        result = {"first_year": None, "last_year": None, "quotation_count": 0}

        # Look for year patterns in definition
        year_pattern = r'\b(1[0-9]{3}|20[0-2][0-9])\b'
        years = re.findall(year_pattern, definition_text)

        if years:
            years = [int(y) for y in years]
            result["first_year"] = min(years)
            result["last_year"] = max(years)

        return result

    def _map_to_historical_period(self, first_year: Optional[int], last_year: Optional[int]) -> str:
        """Map years to historical periods"""
        if not first_year:
            return "contemporary"

        if first_year < 1850:
            return "historical_pre1950"
        elif first_year < 2000:
            return "modern_2000plus"
        else:
            return "contemporary"

    def _extract_part_of_speech(self, word_data: Dict, sense: Dict) -> Optional[str]:
        """Extract part of speech from word data or sense"""
        pos_fields = ['pos', 'part_of_speech', 'grammatical_category']
        for field in pos_fields:
            if field in word_data and word_data[field]:
                return str(word_data[field])
            if field in sense and sense[field]:
                return str(sense[field])
        return None

    def _extract_domain_label(self, definition_text: str) -> Optional[str]:
        """Extract domain label from definition text"""
        domain_patterns = {
            'Law': ['legal', 'law', 'court', 'statute'],
            'Philosophy': ['philosophy', 'philosophical', 'metaphysical'],
            'Computing': ['computer', 'computing', 'software', 'algorithm'],
            'Economics': ['economic', 'economics', 'market', 'financial'],
            'Medicine': ['medical', 'medicine', 'clinical', 'therapeutic']
        }

        definition_lower = definition_text.lower()
        for domain, patterns in domain_patterns.items():
            if any(pattern in definition_lower for pattern in patterns):
                return domain

        return None

    def _determine_status(self, definition_text: str) -> str:
        """Determine if definition is current, historical, or obsolete"""
        obsolete_indicators = ['obsolete', 'archaic', 'historical', 'no longer']
        definition_lower = definition_text.lower()

        if any(indicator in definition_lower for indicator in obsolete_indicators):
            return 'obsolete'

        return 'current'
