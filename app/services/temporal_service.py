"""
Temporal Service

Handles business logic for temporal evolution analysis.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import logging
import re

from app import db
from app.models import Experiment
from app.models.orchestration_logs import OrchestrationDecision
from app.services.base_service import BaseService, ServiceError, NotFoundError, ValidationError

logger = logging.getLogger(__name__)


class TemporalService(BaseService):
    """Service for managing temporal evolution analysis"""

    @staticmethod
    def generate_time_periods(start_year: int, end_year: int, interval: int = 5) -> List[int]:
        """
        Generate a list of time periods between start and end years.

        Args:
            start_year: Starting year
            end_year: Ending year
            interval: Years between periods (default: 5)

        Returns:
            List of years representing time periods
        """
        periods = []
        current_year = start_year
        while current_year <= end_year:
            periods.append(current_year)
            current_year += interval

        # Ensure end year is included if not already
        if periods and periods[-1] < end_year:
            periods.append(end_year)

        # If still empty, create a basic set
        if not periods:
            periods = [start_year, end_year]

        return periods

    def get_temporal_ui_data(self, experiment_id: int) -> Dict[str, Any]:
        """
        Get data for temporal term management UI

        Args:
            experiment_id: ID of the experiment

        Returns:
            Dictionary containing UI data

        Raises:
            NotFoundError: If experiment not found
            ValidationError: If experiment is not temporal evolution type
            ServiceError: On other errors
        """
        try:
            # Get experiment
            experiment = Experiment.query.filter_by(id=experiment_id).first()
            if not experiment:
                raise NotFoundError(f"Experiment {experiment_id} not found")

            # Only for temporal evolution experiments
            if experiment.experiment_type != 'temporal_evolution':
                raise ValidationError('Temporal term management is only available for temporal evolution experiments')

            # Parse configuration to get time periods and terms
            config = json.loads(experiment.configuration) if experiment.configuration else {}
            time_periods = config.get('time_periods', [])
            terms = config.get('target_terms', [])
            start_year = config.get('start_year', 2000)
            end_year = config.get('end_year', 2020)
            use_oed_periods = config.get('use_oed_periods', False)

            # If using OED periods and periods haven't been generated yet
            if use_oed_periods and (not time_periods or len(time_periods) == 0) and terms:
                # Fetch OED data for each term to generate individual periods
                oed_result = self._fetch_oed_periods_for_terms(terms)

                if oed_result['has_data']:
                    time_periods = oed_result['overall_periods']
                    start_year = oed_result['overall_min_year']
                    end_year = oed_result['overall_max_year']

                    # Update configuration with OED data
                    config['time_periods'] = time_periods
                    config['oed_period_data'] = oed_result['oed_period_data']
                    config['term_periods'] = oed_result['term_periods']
                    config['start_year'] = start_year
                    config['end_year'] = end_year

                    # Save updated configuration
                    experiment.configuration = json.dumps(config)
                    db.session.commit()

                    logger.info(f"Generated OED time periods for {oed_result['terms_with_data']} term(s): {start_year} to {end_year}")
                else:
                    logger.warning("Unable to fetch OED data for any terms. No time periods set.")
                    time_periods = []

            # If no time periods specified, leave empty - user must explicitly generate them
            elif not time_periods or len(time_periods) == 0:
                time_periods = []

            # Get orchestration decisions for this experiment
            orchestration_decisions = OrchestrationDecision.query.filter_by(
                experiment_id=experiment.id
            ).order_by(OrchestrationDecision.created_at.desc()).limit(10).all()

            return {
                'experiment': experiment,
                'time_periods': time_periods,
                'terms': terms,
                'start_year': start_year,
                'end_year': end_year,
                'use_oed_periods': use_oed_periods,
                'oed_period_data': config.get('oed_period_data', {}),
                'term_periods': config.get('term_periods', {}),
                'orchestration_decisions': orchestration_decisions,
                'period_documents': config.get('period_documents', {}),
                'period_metadata': config.get('period_metadata', {}),
                'semantic_events': config.get('semantic_events', [])
            }

        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Error getting temporal UI data for experiment {experiment_id}: {e}", exc_info=True)
            raise ServiceError(f"Failed to get temporal UI data: {str(e)}")

    def _fetch_oed_periods_for_terms(self, terms: List[str]) -> Dict[str, Any]:
        """
        Fetch OED data and generate periods for multiple terms

        Args:
            terms: List of terms to fetch OED data for

        Returns:
            Dictionary containing OED period data
        """
        from app.services.oed_service import OEDService
        oed_service = OEDService()

        oed_period_data = {}
        term_periods = {}  # Store individual periods for each term
        overall_min_year = None
        overall_max_year = None
        terms_with_data = 0

        for term in terms:
            try:
                # Get OED quotations for the term
                suggestions = oed_service.suggest_ids(term, limit=3)
                if suggestions and suggestions.get('success') and suggestions.get('suggestions'):
                    for suggestion in suggestions['suggestions'][:1]:  # Use first match
                        entry_id = suggestion.get('entry_id')
                        if entry_id:
                            quotations_result = oed_service.get_quotations(entry_id, limit=100)
                            if quotations_result and quotations_result.get('success'):
                                quotations_data = quotations_result.get('data', {})
                                results = quotations_data.get('data', [])

                                term_years = []
                                for quotation in results:
                                    year_value = quotation.get('year')
                                    if year_value:
                                        try:
                                            term_years.append(int(year_value))
                                        except (ValueError, TypeError):
                                            pass

                                if term_years:
                                    min_year = min(term_years)
                                    max_year = max(term_years)

                                    # Generate periods for this specific term
                                    periods_for_term = self.generate_time_periods(min_year, max_year)
                                    term_periods[term] = periods_for_term

                                    # Track overall range for display
                                    if overall_min_year is None or min_year < overall_min_year:
                                        overall_min_year = min_year
                                    if overall_max_year is None or max_year > overall_max_year:
                                        overall_max_year = max_year

                                    oed_period_data[term] = {
                                        'min_year': min_year,
                                        'max_year': max_year,
                                        'quotation_years': sorted(list(set(term_years))),
                                        'periods': periods_for_term
                                    }
                                    terms_with_data += 1
                                    logger.info(f"OED data for '{term}': {len(term_years)} quotations, {min_year}-{max_year}")
                                else:
                                    logger.info(f"No years found in OED data for '{term}'")
                                    term_periods[term] = []
                            break
            except Exception as e:
                logger.error(f"Error fetching OED data for term '{term}': {str(e)}")
                term_periods[term] = []
                continue

        # Generate overall periods if we have data
        overall_periods = []
        if overall_min_year and overall_max_year:
            overall_periods = self.generate_time_periods(overall_min_year, overall_max_year)

        return {
            'has_data': overall_min_year is not None and overall_max_year is not None,
            'overall_periods': overall_periods,
            'overall_min_year': overall_min_year,
            'overall_max_year': overall_max_year,
            'oed_period_data': oed_period_data,
            'term_periods': term_periods,
            'terms_with_data': terms_with_data
        }

    def update_temporal_configuration(
        self,
        experiment_id: int,
        terms: List[str],
        periods: List[int],
        temporal_data: Dict[str, Any]
    ) -> Experiment:
        """
        Update temporal terms and periods configuration

        Args:
            experiment_id: ID of the experiment
            terms: List of target terms
            periods: List of time periods
            temporal_data: Temporal data dictionary

        Returns:
            Updated experiment

        Raises:
            NotFoundError: If experiment not found
            ServiceError: On database errors
        """
        try:
            experiment = Experiment.query.filter_by(id=experiment_id).first()
            if not experiment:
                raise NotFoundError(f"Experiment {experiment_id} not found")

            # Update configuration
            config = json.loads(experiment.configuration) if experiment.configuration else {}
            config['target_terms'] = terms
            config['time_periods'] = periods
            config['temporal_data'] = temporal_data

            experiment.configuration = json.dumps(config)
            experiment.updated_at = datetime.utcnow()
            db.session.commit()

            logger.info(f"Updated temporal configuration for experiment {experiment_id}: {len(terms)} terms, {len(periods)} periods")

            return experiment

        except NotFoundError:
            raise
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating temporal configuration for experiment {experiment_id}: {e}", exc_info=True)
            raise ServiceError(f"Failed to update temporal configuration: {str(e)}")

    def get_temporal_configuration(self, experiment_id: int) -> Dict[str, Any]:
        """
        Get temporal configuration for an experiment

        Args:
            experiment_id: ID of the experiment

        Returns:
            Dictionary with terms, periods, and temporal_data

        Raises:
            NotFoundError: If experiment not found
            ServiceError: On other errors
        """
        try:
            experiment = Experiment.query.filter_by(id=experiment_id).first()
            if not experiment:
                raise NotFoundError(f"Experiment {experiment_id} not found")

            config = json.loads(experiment.configuration) if experiment.configuration else {}

            return {
                'terms': config.get('target_terms', []),
                'periods': config.get('time_periods', []),
                'temporal_data': config.get('temporal_data', {})
            }

        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error getting temporal configuration for experiment {experiment_id}: {e}", exc_info=True)
            raise ServiceError(f"Failed to get temporal configuration: {str(e)}")

    def generate_periods_from_documents(self, experiment_id: int) -> Dict[str, Any]:
        """
        Generate time periods based on document publication dates

        Args:
            experiment_id: ID of the experiment

        Returns:
            Dictionary with generated periods and metadata

        Raises:
            NotFoundError: If experiment not found
            ValidationError: If no documents have publication dates
            ServiceError: On other errors
        """
        try:
            experiment = Experiment.query.filter_by(id=experiment_id).first()
            if not experiment:
                raise NotFoundError(f"Experiment {experiment_id} not found")

            # Get all documents with publication dates
            from app.models import Document
            from app.models.temporal_experiment import DocumentTemporalMetadata
            documents = Document.query.filter_by(experiment_id=experiment_id).all()

            if not documents:
                raise ValidationError("No documents found in experiment")

            # Extract years from publication_date (single source of truth)
            # Note: Document.publication_date accepts flexible formats (year-only, year-month, full date)
            years = []
            using_fallback = False
            period_documents = {}  # Map periods to documents {year: [{id, title, date}, ...]}

            for doc in documents:
                year = None
                date_source = None

                # 1. Try Document.publication_date (primary source)
                if doc.publication_date:
                    try:
                        year = doc.publication_date.year if hasattr(doc.publication_date, 'year') else None
                        date_source = 'publication_date'
                    except:
                        pass

                # 2. Fallback to created_at (upload date) if no publication date set
                if year is None and doc.created_at:
                    try:
                        year = doc.created_at.year if hasattr(doc.created_at, 'year') else None
                        using_fallback = True
                        date_source = 'upload_date'
                    except:
                        pass

                if year:
                    years.append(year)

                    # Track which documents belong to this period
                    if year not in period_documents:
                        period_documents[year] = []

                    period_documents[year].append({
                        'id': doc.id,
                        'uuid': str(doc.uuid),
                        'title': doc.title[:50] + '...' if doc.title and len(doc.title) > 50 else doc.title or 'Untitled',
                        'date_source': date_source
                    })

            if not years:
                raise ValidationError("No documents have usable dates. Please add publication dates to your documents or ensure documents have been uploaded.")

            # Use unique years from documents as periods (one period per document)
            periods = sorted(list(set(years)))
            min_year = min(years)
            max_year = max(years)

            # Update experiment configuration
            import json
            config = json.loads(experiment.configuration) if experiment.configuration else {}
            config['time_periods'] = periods
            config['start_year'] = min_year
            config['end_year'] = max_year
            config['periods_source'] = 'documents'
            config['period_documents'] = period_documents  # Store document mapping
            config['period_metadata'] = {
                str(year): {
                    'source': 'auto-generated',
                    'document_count': len(period_documents[year])
                } for year in periods
            }

            experiment.configuration = json.dumps(config)
            db.session.commit()

            source_type = 'upload dates' if using_fallback else 'publication dates'
            logger.info(f"Generated {len(periods)} periods from {len(documents)} documents for experiment {experiment_id}: {min_year}-{max_year} (using {source_type})")

            return {
                'periods': periods,
                'document_count': len(documents),
                'documents_with_dates': len(years),
                'date_range': {
                    'min_year': min_year,
                    'max_year': max_year
                },
                'source_type': source_type,
                'using_fallback': using_fallback
            }

        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error generating periods from documents for experiment {experiment_id}: {e}", exc_info=True)
            raise ServiceError(f"Failed to generate periods from documents: {str(e)}")

    def fetch_temporal_analysis(
        self,
        experiment_id: int,
        term: str,
        periods: Optional[List[int]] = None,
        use_oed: bool = False
    ) -> Dict[str, Any]:
        """
        Fetch temporal analysis data for a term

        Args:
            experiment_id: ID of the experiment
            term: Term to analyze
            periods: List of time periods (optional if using OED)
            use_oed: Whether to use OED integration

        Returns:
            Dictionary containing analysis results

        Raises:
            NotFoundError: If experiment not found
            ValidationError: If required parameters missing
            ServiceError: On analysis errors
        """
        try:
            experiment = Experiment.query.filter_by(id=experiment_id).first()
            if not experiment:
                raise NotFoundError(f"Experiment {experiment_id} not found")

            # Check if we have term-specific periods from OED
            config = json.loads(experiment.configuration) if experiment.configuration else {}
            term_periods = config.get('term_periods', {})

            # If using OED and we have term-specific periods, use those
            if use_oed and term in term_periods and term_periods[term]:
                periods = term_periods[term]
                logger.info(f"Using term-specific periods for '{term}': {periods}")
            elif not periods:
                raise ValidationError('Periods are required when not using OED or term-specific periods')

            # Import temporal analysis service
            from shared_services.temporal import TemporalAnalysisService
            from shared_services.ontology.ontology_importer import OntologyImporter

            # Initialize services
            ontology_importer = OntologyImporter()
            temporal_service = TemporalAnalysisService(ontology_importer)

            # Get all documents from the experiment
            all_documents = list(experiment.documents) + list(experiment.references)

            # If OED integration requested, enhance with OED data
            oed_periods = []
            temporal_data_oed = None
            if use_oed:
                oed_result = self._fetch_oed_data_for_term(term)
                if oed_result['has_data']:
                    oed_periods = oed_result['periods']
                    temporal_data_oed = oed_result['data']

            # Use OED periods if available, otherwise use provided periods
            analysis_periods = oed_periods if oed_periods else periods

            # If using OED data, create hybrid analysis
            if use_oed and temporal_data_oed:
                temporal_data = self._create_hybrid_temporal_analysis(
                    temporal_service,
                    all_documents,
                    term,
                    analysis_periods,
                    temporal_data_oed
                )
            else:
                # Normal document-based analysis
                temporal_data = temporal_service.extract_temporal_data(all_documents, term, analysis_periods)

                # Ensure temporal_data is not None
                if temporal_data is None:
                    temporal_data = {}
                    for period in analysis_periods:
                        temporal_data[str(period)] = {
                            'frequency': 0,
                            'contexts': [],
                            'co_occurring_terms': [],
                            'evolution': 'absent'
                        }

            # Extract frequency data for visualization
            frequency_data = self._extract_frequency_data(temporal_data, analysis_periods)

            # Analyze semantic drift
            drift_analysis = temporal_service.analyze_semantic_drift(all_documents, term, analysis_periods)
            if drift_analysis is None:
                drift_analysis = {
                    'average_drift': 0,
                    'stable_terms': [],
                    'periods': {}
                }

            # Generate evolution narrative
            narrative = temporal_service.generate_evolution_narrative(temporal_data, term, analysis_periods)
            if narrative is None:
                narrative = f"Analysis of '{term}' across {len(analysis_periods)} time periods."

            response = {
                'temporal_data': temporal_data,
                'frequency_data': frequency_data,
                'drift_analysis': drift_analysis,
                'narrative': narrative,
                'periods_used': analysis_periods
            }

            # Add OED data if available
            if use_oed and temporal_data_oed:
                response['oed_data'] = temporal_data_oed

            logger.info(f"Completed temporal analysis for '{term}' across {len(analysis_periods)} periods")

            return response

        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Error fetching temporal analysis for experiment {experiment_id}, term '{term}': {e}", exc_info=True)
            raise ServiceError(f"Failed to fetch temporal analysis: {str(e)}")

    def _fetch_oed_data_for_term(self, term: str) -> Dict[str, Any]:
        """
        Fetch OED data for a single term

        Args:
            term: Term to fetch OED data for

        Returns:
            Dictionary with OED data and periods
        """
        try:
            from app.services.oed_service import OEDService
            oed_service = OEDService()

            # Try to get OED quotations for the term
            suggestions = oed_service.suggest_ids(term, limit=3)
            if not suggestions:
                logger.info(f"OED: No suggestions returned for term '{term}'")
                return {'has_data': False}

            if not suggestions.get('success'):
                logger.info(f"OED: Failed to get suggestions - {suggestions.get('error', 'Unknown error')}")
                return {'has_data': False}

            if not suggestions.get('suggestions'):
                logger.info(f"OED: No suggestions found for term '{term}'")
                return {'has_data': False}

            suggestion_list = suggestions.get('suggestions', [])
            if not isinstance(suggestion_list, list):
                logger.warning(f"OED: Unexpected suggestions format: {type(suggestion_list)}")
                return {'has_data': False}

            for suggestion in suggestion_list[:1]:  # Use first match
                if not suggestion or not isinstance(suggestion, dict):
                    continue

                entry_id = suggestion.get('entry_id')
                if not entry_id:
                    continue

                logger.info(f"OED: Fetching quotations for entry_id: {entry_id}")
                quotations_result = oed_service.get_quotations(entry_id, limit=100)

                if not quotations_result:
                    logger.info("OED: No quotations result returned")
                    continue

                if not quotations_result.get('success'):
                    logger.info(f"OED: Failed to get quotations - {quotations_result.get('error', 'Unknown error')}")
                    continue

                quotations_data = quotations_result.get('data')
                if not quotations_data or not isinstance(quotations_data, dict):
                    logger.info("OED: No valid quotations data")
                    continue

                # Extract years from quotations
                years = self._extract_years_from_quotations(quotations_data)

                if years:
                    min_year = min(years)
                    max_year = max(years)
                    oed_periods = self.generate_time_periods(min_year, max_year)

                    logger.info(f"OED: Found {len(years)} quotation years, range {min_year}-{max_year}")

                    return {
                        'has_data': True,
                        'periods': oed_periods,
                        'data': {
                            'min_year': min_year,
                            'max_year': max_year,
                            'suggested_periods': oed_periods,
                            'quotation_years': sorted(list(set(years)))
                        }
                    }
                else:
                    logger.info(f"OED: No years extracted from quotations")

        except Exception as oed_error:
            logger.error(f"OED integration error for term '{term}': {str(oed_error)}", exc_info=True)

        return {'has_data': False}

    def _extract_years_from_quotations(self, quotations_data: Dict[str, Any]) -> List[int]:
        """
        Extract years from OED quotations data

        Args:
            quotations_data: OED quotations response data

        Returns:
            List of years
        """
        years = []

        # The OED API returns quotations under the 'data' key
        results = quotations_data.get('data', [])

        if not results or not isinstance(results, list):
            # Try alternative keys if 'data' doesn't work
            for key in ['results', 'quotations', 'items']:
                if key in quotations_data:
                    results = quotations_data[key]
                    if results:
                        logger.info(f"OED: Found quotations under key '{key}'")
                        break

            if not results or not isinstance(results, list):
                logger.info("OED: No valid quotations list found in data")
                return years
        else:
            logger.info(f"OED: Found {len(results)} quotations under 'data' key")

        for quotation in results:
            if not quotation or not isinstance(quotation, dict):
                continue

            # The OED API returns year directly as 'year' field
            year_value = quotation.get('year')
            if year_value:
                try:
                    years.append(int(year_value))
                except (ValueError, TypeError):
                    # If year is not a valid integer, try extracting from string
                    year_match = re.search(r'\b(1[0-9]{3}|20[0-9]{2})\b', str(year_value))
                    if year_match:
                        years.append(int(year_match.group()))

        return years

    def _create_hybrid_temporal_analysis(
        self,
        temporal_service,
        all_documents: List,
        term: str,
        analysis_periods: List[int],
        temporal_data_oed: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create hybrid temporal analysis combining OED and document data

        Args:
            temporal_service: Temporal analysis service instance
            all_documents: List of documents
            term: Term to analyze
            analysis_periods: List of periods
            temporal_data_oed: OED data

        Returns:
            Combined temporal data
        """
        temporal_data = {}
        quotation_years = temporal_data_oed.get('quotation_years', [])

        # Group quotations by period
        period_quotations = {}
        for period in analysis_periods:
            period_quotations[period] = []
            for year in quotation_years:
                # Include quotations within 5 years of the period
                if abs(year - period) <= 5:
                    period_quotations[period].append(year)

        # For each period, create appropriate data
        for period in analysis_periods:
            period_str = str(period)

            # First check if we have OED data for this period
            oed_count = len(period_quotations.get(period, []))

            # Try to get document data if period is recent enough
            doc_based_data = None
            if period >= 1900:  # Only try document analysis for modern periods
                try:
                    # Try to get document-based analysis
                    temp_data = temporal_service.extract_temporal_data(all_documents, term, [period])
                    if temp_data and str(period) in temp_data:
                        doc_based_data = temp_data[str(period)]
                except Exception as e:
                    logger.warning(f"Error extracting temporal data for period {period}: {str(e)}")
                    pass  # If it fails, we'll use OED data

            # Use document data if available and has content
            if doc_based_data and doc_based_data.get('frequency', 0) > 0:
                temporal_data[period_str] = doc_based_data
                # Add OED note if we also have OED data
                if oed_count > 0:
                    temporal_data[period_str]['oed_note'] = f'Also found {oed_count} OED quotation(s)'
            # Otherwise use OED data
            elif oed_count > 0:
                temporal_data[period_str] = {
                    'frequency': oed_count,
                    'contexts': [f'OED: {oed_count} historical quotation(s) from this period'],
                    'co_occurring_terms': [],
                    'evolution': 'historical',
                    'source': 'Oxford English Dictionary',
                    'definition': f'Historical usage documented in OED with {oed_count} quotation(s)',
                    'is_oed_data': True
                }
            else:
                # No data from either source
                temporal_data[period_str] = {
                    'frequency': 0,
                    'contexts': [],
                    'co_occurring_terms': [],
                    'evolution': 'absent',
                    'definition': f'No usage found for "{term}" in {period}',
                    'is_oed_data': True
                }

        return temporal_data

    def _extract_frequency_data(self, temporal_data: Dict[str, Any], analysis_periods: List[int]) -> Dict[int, int]:
        """
        Extract frequency data for visualization

        Args:
            temporal_data: Temporal data by period
            analysis_periods: List of periods

        Returns:
            Dictionary mapping periods to frequencies
        """
        frequency_data = {}
        for period in analysis_periods:
            period_str = str(period)
            if period_str in temporal_data and temporal_data[period_str] is not None:
                # Scale OED frequencies for better visualization
                freq = temporal_data[period_str].get('frequency', 0)
                if temporal_data[period_str].get('is_oed_data'):
                    # Scale OED quotation counts to be comparable with document frequencies
                    freq = freq * 10  # Each OED quotation represents significant usage
                frequency_data[period] = freq
            else:
                frequency_data[period] = 0

        return frequency_data


# Singleton instance
_temporal_service = None


def get_temporal_service() -> TemporalService:
    """Get the singleton TemporalService instance"""
    global _temporal_service
    if _temporal_service is None:
        _temporal_service = TemporalService()
    return _temporal_service
