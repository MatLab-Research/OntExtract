"""
OED Enrichment Coordinator

Main orchestrator for OED data enrichment process.
Coordinates extraction and analysis of etymology, definitions, quotations, and statistics.
"""

from typing import Dict, Any
from flask import current_app
from app import db
from app.models.term import Term
from app.services.oed_service import OEDService
from .extractors.etymology_extractor import EtymologyExtractor
from .extractors.definition_extractor import DefinitionExtractor
from .extractors.quotation_extractor import QuotationExtractor
from .analyzers.historical_analyzer import HistoricalAnalyzer


class OEDEnrichmentService:
    """Service for enriching terms with OED etymology, definitions, and statistics"""

    def __init__(self):
        self.oed_service = OEDService()
        self.etymology_extractor = EtymologyExtractor()
        self.definition_extractor = DefinitionExtractor()
        self.quotation_extractor = QuotationExtractor()
        self.historical_analyzer = HistoricalAnalyzer()

    def enrich_term_with_oed_data(self, term_id: str, entry_id: str = None) -> Dict[str, Any]:
        """
        Enrich a term with comprehensive OED data including etymology, definitions, and statistics

        Args:
            term_id: UUID of the term to enrich
            entry_id: Optional specific OED entry ID (e.g., 'agent_nn01')

        Returns:
            Dict with enrichment results and statistics
        """
        term = Term.query.get(term_id)
        if not term:
            return {"success": False, "error": "Term not found"}

        results = {
            "success": True,
            "term_text": term.term_text,
            "etymology_created": False,
            "definitions_created": 0,
            "historical_stats_created": 0,
            "quotation_summaries_created": 0,
            "errors": []
        }

        try:
            # If no entry_id provided, try to find suggestions
            if not entry_id:
                suggestions_result = self.oed_service.suggest_ids(term.term_text, limit=1)
                if suggestions_result.get('success') and suggestions_result.get('suggestions'):
                    entry_id = suggestions_result['suggestions'][0]['entry_id']
                else:
                    return {"success": False, "error": "Could not find OED entry for term"}

            # Get word data from OED
            word_result = self.oed_service.get_word(entry_id)
            if not word_result.get('success'):
                return {"success": False, "error": f"Failed to get OED word data: {word_result.get('error')}"}

            word_data = word_result['data']

            # Extract and store etymology
            etymology_result = self.etymology_extractor.extract_and_store(term, word_data, entry_id)
            if etymology_result.get('created'):
                results['etymology_created'] = True
            if etymology_result.get('errors'):
                results['errors'].extend(etymology_result['errors'])

            # Extract and store definitions with temporal analysis
            definitions_result = self.definition_extractor.extract_and_store(term, word_data, entry_id)
            results['definitions_created'] = definitions_result.get('created', 0)
            if definitions_result.get('errors'):
                results['errors'].extend(definitions_result['errors'])

            # Get quotations data
            quotations_result = self.oed_service.get_quotations(entry_id, limit=100)
            if quotations_result.get('success'):
                quotations_data = quotations_result['data']

                # Extract and store quotation summaries
                quotation_summaries_result = self.quotation_extractor.extract_and_store(
                    term, quotations_data, entry_id
                )
                results['quotation_summaries_created'] = quotation_summaries_result.get('created', 0)
                if quotation_summaries_result.get('errors'):
                    results['errors'].extend(quotation_summaries_result['errors'])

            # Calculate and store historical statistics
            stats_result = self.historical_analyzer.calculate_and_store_stats(term)
            results['historical_stats_created'] = stats_result.get('created', 0)
            if stats_result.get('errors'):
                results['errors'].extend(stats_result['errors'])

            db.session.commit()

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error enriching term {term.term_text} with OED data: {str(e)}")
            return {"success": False, "error": str(e)}

        return results


def enrich_term_with_oed(term_text: str, entry_id: str = None) -> Dict[str, Any]:
    """
    Convenience function to enrich a term with OED data

    Args:
        term_text: The term text to look up
        entry_id: Optional specific OED entry ID

    Returns:
        Dict with enrichment results
    """
    term = Term.query.filter_by(term_text=term_text).first()
    if not term:
        return {"success": False, "error": "Term not found in database"}

    service = OEDEnrichmentService()
    return service.enrich_term_with_oed_data(str(term.id), entry_id)
