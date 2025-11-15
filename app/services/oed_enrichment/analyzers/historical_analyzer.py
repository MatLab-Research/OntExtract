"""
Historical Analyzer

Analyzes historical statistics and period-based data for terms.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from app import db
from app.models.term import Term
from app.models.oed_models import OEDDefinition, OEDQuotationSummary, OEDHistoricalStats


class HistoricalAnalyzer:
    """Handles historical statistics calculation and period analysis"""

    def calculate_and_store_stats(self, term: Term) -> Dict[str, Any]:
        """Calculate aggregated historical statistics and store in OEDHistoricalStats table"""
        result = {"created": 0, "errors": []}

        try:
            # Group definitions by historical period
            definitions = OEDDefinition.query.filter_by(term_id=term.id).all()
            quotations = OEDQuotationSummary.query.filter_by(term_id=term.id).all()

            periods = self._group_by_periods(definitions, quotations)

            for period_name, period_data in periods.items():
                try:
                    # Create PROV-O Activity metadata
                    used_definitions = [str(d.id) for d in period_data['definitions']]
                    used_quotations = [str(q.id) for q in period_data['quotations']]

                    stats = OEDHistoricalStats(
                        term_id=term.id,
                        time_period=period_name,
                        start_year=period_data['start_year'],
                        end_year=period_data['end_year'],
                        definition_count=len(period_data['definitions']),
                        sense_count=len(period_data['definitions']),
                        quotation_span_years=period_data['quotation_span'],
                        earliest_quotation_year=period_data['earliest_quotation'],
                        latest_quotation_year=period_data['latest_quotation'],
                        semantic_stability_score=self._calculate_semantic_stability(period_data),
                        domain_shift_indicator=self._detect_domain_shift(period_data),
                        part_of_speech_changes=self._detect_pos_changes(period_data),
                        oed_edition="OED_API_2025",
                        # PROV-O Activity metadata
                        started_at_time=datetime.utcnow(),
                        ended_at_time=datetime.utcnow(),
                        was_associated_with="Statistical_Analysis_Service",
                        used_entity={
                            "definitions": used_definitions,
                            "quotations": used_quotations,
                            "analysis_period": period_name
                        },
                        generated_entity=f"oed_historical_stats_{term.term_text}_{period_name}"
                    )

                    db.session.add(stats)
                    result["created"] += 1

                except IntegrityError:
                    # Stats for this period already exist
                    db.session.rollback()
                    continue
                except Exception as e:
                    result["errors"].append(f"Stats for period {period_name} error: {str(e)}")
                    continue

        except Exception as e:
            result["errors"].append(f"Historical stats calculation error: {str(e)}")

        return result

    def _group_by_periods(self, definitions: List[OEDDefinition], quotations: List[OEDQuotationSummary]) -> Dict[str, Any]:
        """Group definitions and quotations by historical periods"""
        periods = {}

        # Define period boundaries
        period_boundaries = {
            'historical_pre1950': (0, 1950),
            'modern_2000plus': (1950, 2000),
            'contemporary': (2000, 2030)
        }

        for period_name, (start, end) in period_boundaries.items():
            period_definitions = [d for d in definitions
                                if d.first_cited_year and start <= d.first_cited_year < end]
            period_quotations = [q for q in quotations
                               if q.quotation_year and start <= q.quotation_year < end]

            if period_definitions or period_quotations:
                quotation_years = [q.quotation_year for q in period_quotations if q.quotation_year]

                periods[period_name] = {
                    'start_year': start,
                    'end_year': end,
                    'definitions': period_definitions,
                    'quotations': period_quotations,
                    'quotation_span': max(quotation_years) - min(quotation_years) if quotation_years else 0,
                    'earliest_quotation': min(quotation_years) if quotation_years else None,
                    'latest_quotation': max(quotation_years) if quotation_years else None
                }

        return periods

    def _calculate_semantic_stability(self, period_data: Dict) -> Optional[float]:
        """Calculate semantic stability score for a period"""
        definitions = period_data['definitions']
        if not definitions:
            return None

        # Simple stability metric based on definition consistency
        stability = 1.0 - (len(definitions) - 1) * 0.1
        return max(0.0, min(1.0, stability))

    def _detect_domain_shift(self, period_data: Dict) -> bool:
        """Detect if there's a domain shift in this period"""
        definitions = period_data['definitions']
        domains = set(d.domain_label for d in definitions if d.domain_label)
        return len(domains) > 1

    def _detect_pos_changes(self, period_data: Dict) -> Optional[List[str]]:
        """Detect part of speech changes in period"""
        definitions = period_data['definitions']
        pos_values = set(d.part_of_speech for d in definitions if d.part_of_speech)
        return list(pos_values) if pos_values else None
