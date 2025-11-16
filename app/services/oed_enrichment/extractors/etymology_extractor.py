"""
Etymology Extractor

Extracts and analyzes etymology information from OED data.
"""

from typing import Dict, Optional, Any
from datetime import datetime
from app import db
from app.models.term import Term
from app.models.oed_models import OEDEtymology


class EtymologyExtractor:
    """Handles etymology extraction and analysis"""

    def extract_and_store(self, term: Term, word_data: Dict, entry_id: str) -> Dict[str, Any]:
        """Extract etymology information and store in OEDEtymology table"""
        result = {"created": False, "errors": []}

        try:
            # Check if etymology already exists
            existing = OEDEtymology.query.filter_by(term_id=term.id).first()
            if existing:
                return result

            # Extract etymology data from word_data
            etymology_text = self._extract_text(word_data)
            origin_info = self._analyze_origin_language(etymology_text, word_data)
            first_recorded_year = self._extract_first_recorded_year(word_data)

            etymology = OEDEtymology(
                term_id=term.id,
                etymology_text=etymology_text,
                origin_language=origin_info.get('language'),
                first_recorded_year=first_recorded_year,
                etymology_confidence=self._assess_confidence(word_data),
                language_family=origin_info.get('family'),
                root_analysis=self._analyze_word_roots(etymology_text, term.term_text),
                morphology=self._analyze_morphology(term.term_text, word_data),
                source_version="OED_API_2025",
                # PROV-O Entity metadata
                generated_at_time=datetime.utcnow(),
                was_attributed_to="OED_API_Service",
                was_derived_from=entry_id,
                derivation_type="etymology_extraction"
            )

            db.session.add(etymology)
            result["created"] = True

        except Exception as e:
            result["errors"].append(f"Etymology extraction error: {str(e)}")

        return result

    def _extract_text(self, word_data: Dict) -> Optional[str]:
        """Extract etymology text from OED word data"""
        etymology_fields = ['etymology', 'etymologies', 'origin']
        for field in etymology_fields:
            if field in word_data and word_data[field]:
                if isinstance(word_data[field], list):
                    return word_data[field][0] if word_data[field] else None
                return str(word_data[field])
        return None

    def _analyze_origin_language(self, etymology_text: str, word_data: Dict) -> Dict[str, Any]:
        """Analyze origin language and language family"""
        result = {"language": None, "family": None}

        if not etymology_text:
            return result

        # Common language patterns
        language_patterns = {
            'Latin': ['Latin', 'L.'],
            'Greek': ['Greek', 'Gr.'],
            'French': ['French', 'F.', 'Old French', 'OF.'],
            'Germanic': ['Germanic', 'OHG', 'Old High German'],
            'Anglo-Saxon': ['Anglo-Saxon', 'AS.', 'Old English', 'OE.']
        }

        etymology_lower = etymology_text.lower()
        for language, patterns in language_patterns.items():
            if any(pattern.lower() in etymology_lower for pattern in patterns):
                result["language"] = language
                # Add family information
                if language in ['Latin', 'Greek']:
                    result["family"] = {"family": "Indo-European", "branch": "Classical"}
                elif language in ['French']:
                    result["family"] = {"family": "Indo-European", "branch": "Romance"}
                elif language in ['Germanic', 'Anglo-Saxon']:
                    result["family"] = {"family": "Indo-European", "branch": "Germanic"}
                break

        return result

    def _extract_first_recorded_year(self, word_data: Dict) -> Optional[int]:
        """Extract first recorded year from word data"""
        date_fields = ['first_use_date', 'earliest_date', 'date_of_first_use']
        for field in date_fields:
            if field in word_data and word_data[field]:
                try:
                    return int(word_data[field])
                except (ValueError, TypeError):
                    continue
        return None

    def _assess_confidence(self, word_data: Dict) -> str:
        """Assess confidence level of etymology data"""
        confidence_indicators = 0

        if word_data.get('etymology'):
            confidence_indicators += 1
        if word_data.get('first_use_date'):
            confidence_indicators += 1
        if word_data.get('extracted_senses') and len(word_data['extracted_senses']) > 2:
            confidence_indicators += 1

        if confidence_indicators >= 2:
            return 'high'
        elif confidence_indicators == 1:
            return 'medium'
        else:
            return 'low'

    def _analyze_word_roots(self, etymology_text: str, term_text: str) -> Optional[Dict[str, Any]]:
        """Analyze word roots from etymology"""
        if not etymology_text:
            return None

        return {
            "roots": [term_text[:3] if len(term_text) > 3 else term_text],
            "analysis": "Basic morphological analysis",
            "confidence": "low"
        }

    def _analyze_morphology(self, term_text: str, word_data: Dict) -> Optional[Dict[str, Any]]:
        """Analyze morphological structure"""
        morphology = {"type": "unknown", "components": []}

        # Simple morphological analysis
        if term_text.endswith('ent'):
            morphology["type"] = "agent_noun"
            morphology["suffixes"] = ["-ent"]
        elif term_text.endswith('er'):
            morphology["type"] = "agent_noun"
            morphology["suffixes"] = ["-er"]
        elif term_text.endswith('tion'):
            morphology["type"] = "abstract_noun"
            morphology["suffixes"] = ["-tion"]

        return morphology
