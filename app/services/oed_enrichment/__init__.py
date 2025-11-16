"""
OED Enrichment Package

Extracts and processes OED data for semantic evolution visualization.
Converts existing OED API responses into structured database records.
"""

from .enrichment_coordinator import OEDEnrichmentService, enrich_term_with_oed

__all__ = ['OEDEnrichmentService', 'enrich_term_with_oed']
