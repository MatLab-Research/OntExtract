"""
Evolution Service

Business logic for semantic evolution analysis of terms.
Handles term evolution visualization, drift analysis, and temporal data.
"""

import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from app import db
from app.models import Experiment
from app.services.base_service import BaseService, ServiceError, NotFoundError, ValidationError

logger = logging.getLogger(__name__)


class EvolutionService(BaseService):
    """
    Service for semantic evolution operations

    Handles all business logic related to term evolution including:
    - Loading term evolution data (versions, OED, legal)
    - Analyzing semantic drift over time
    - Period matching
    - Generating evolution narratives
    """

    def __init__(self):
        """Initialize EvolutionService"""
        super().__init__(model=Experiment)

    def get_evolution_visualization_data(
        self,
        experiment_id: int,
        term: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get data for semantic evolution visualization

        Args:
            experiment_id: ID of experiment
            term: Optional target term (if not provided, gets from config)

        Returns:
            Dictionary with evolution data including:
            - term_record: Term database record
            - academic_anchors: List of temporal versions
            - oed_data: OED etymological data
            - reference_data: Reference data (OED, legal)
            - temporal_span: Span of years covered
            - domains: List of domains

        Raises:
            NotFoundError: If experiment or term not found
            ValidationError: If validation fails
            ServiceError: If operation fails
        """
        try:
            experiment = self._get_experiment(experiment_id)

            # Determine target term
            target_term = self._determine_target_term(experiment, term)

            # Get term record from database
            term_record = self._get_term_record(target_term)

            # Get temporal versions
            term_versions = self._get_term_versions(term_record.id)

            # Build academic anchors
            academic_anchors = self._build_academic_anchors(term_versions)

            # Calculate metrics
            temporal_span, domains = self._calculate_metrics(academic_anchors)

            # Get OED data
            oed_data = self._get_oed_data(term_record, target_term, term_versions)

            # Get reference data
            reference_data = {
                'oed_data': oed_data,
                'legal_data': self._get_legal_data(target_term),
                'temporal_span': temporal_span,
                'domain_count': len(domains),
                'domains': domains
            }

            logger.info(
                f"Retrieved evolution data for term '{target_term}' in experiment {experiment_id}: "
                f"{len(academic_anchors)} anchors, {temporal_span} year span"
            )

            return {
                'term': target_term,
                'term_record': term_record,
                'academic_anchors': academic_anchors,
                'oed_data': oed_data,
                'reference_data': reference_data,
                'temporal_span': temporal_span,
                'domains': domains
            }

        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Failed to get evolution data for experiment {experiment_id}: {e}", exc_info=True)
            raise ServiceError(f"Failed to get evolution data: {str(e)}") from e

    def analyze_evolution(
        self,
        experiment_id: int,
        term: str,
        periods: List[Any]
    ) -> Dict[str, Any]:
        """
        Analyze the evolution of a term over time

        Args:
            experiment_id: ID of experiment
            term: Term to analyze
            periods: List of time periods to analyze

        Returns:
            Dictionary with:
            - analysis: Narrative analysis text
            - drift_metrics: Semantic drift metrics

        Raises:
            NotFoundError: If experiment not found
            ValidationError: If validation fails
            ServiceError: If operation fails
        """
        try:
            experiment = self._get_experiment(experiment_id)

            # Validate inputs
            if not term:
                raise ValidationError('Term is required')

            if not periods:
                raise ValidationError('At least one period is required')

            # Import temporal analysis service
            from shared_services.temporal import TemporalAnalysisService
            from shared_services.ontology.ontology_importer import OntologyImporter

            # Initialize services
            ontology_importer = OntologyImporter()
            temporal_service = TemporalAnalysisService(ontology_importer)

            # Get all documents
            all_documents = list(experiment.documents) + list(experiment.references)

            # Extract temporal data
            temporal_data = temporal_service.extract_temporal_data(all_documents, term, periods)

            # Analyze semantic drift
            drift_analysis = temporal_service.analyze_semantic_drift(all_documents, term, periods)

            # Generate narrative
            narrative = temporal_service.generate_evolution_narrative(temporal_data, term, periods)

            # Build analysis text
            analysis = self._build_analysis_text(narrative, drift_analysis, term, temporal_service)

            # Extract drift metrics
            drift_metrics = {
                'average_drift': drift_analysis.get('average_drift', 0),
                'total_drift': drift_analysis.get('total_drift', 0),
                'stable_term_count': len(drift_analysis.get('stable_terms', []))
            }

            logger.info(
                f"Analyzed evolution for term '{term}' in experiment {experiment_id}: "
                f"avg drift {drift_metrics['average_drift']:.2%}"
            )

            return {
                'analysis': analysis,
                'drift_metrics': drift_metrics
            }

        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Failed to analyze evolution for experiment {experiment_id}: {e}", exc_info=True)
            raise ServiceError(f"Failed to analyze evolution: {str(e)}") from e

    # Private helper methods

    def _get_experiment(self, experiment_id: int) -> Experiment:
        """Get experiment by ID"""
        experiment = Experiment.query.filter_by(id=experiment_id).first()
        if not experiment:
            raise NotFoundError(f"Experiment {experiment_id} not found")
        return experiment

    def _determine_target_term(self, experiment: Experiment, term: Optional[str]) -> str:
        """
        Determine target term from parameter or experiment configuration

        Args:
            experiment: Experiment instance
            term: Optional term parameter

        Returns:
            Target term string

        Raises:
            ValidationError: If no term can be determined
        """
        if term:
            return term

        # Get from experiment configuration
        config = self._parse_configuration(experiment)

        if config.get('target_term'):
            return config.get('target_term')
        elif config.get('target_terms') and len(config['target_terms']) > 0:
            return config['target_terms'][0]
        else:
            raise ValidationError(
                'No target term specified. Provide term parameter or configure in experiment.'
            )

    def _parse_configuration(self, experiment: Experiment) -> Dict[str, Any]:
        """Parse experiment configuration JSON"""
        if not experiment.configuration:
            return {}

        try:
            return json.loads(experiment.configuration)
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"Failed to parse configuration for experiment {experiment.id}")
            return {}

    def _get_term_record(self, term: str):
        """
        Get term record from database

        Args:
            term: Term text

        Returns:
            Term instance

        Raises:
            NotFoundError: If term not found
        """
        from app.models.term import Term

        term_record = Term.query.filter_by(term_text=term).first()

        if not term_record:
            raise NotFoundError(
                f'Term "{term}" not found in database. Create academic anchors first.'
            )

        return term_record

    def _get_term_versions(self, term_id: int) -> List:
        """
        Get all temporal versions for a term

        Args:
            term_id: Term ID

        Returns:
            List of TermVersion instances

        Raises:
            NotFoundError: If no versions found
        """
        from app.models.term import TermVersion

        term_versions = TermVersion.query.filter_by(
            term_id=term_id
        ).order_by(TermVersion.temporal_start_year.asc()).all()

        if not term_versions:
            raise NotFoundError(
                'No temporal versions found. Create academic anchors first.'
            )

        return term_versions

    def _build_academic_anchors(self, term_versions: List) -> List[Dict[str, Any]]:
        """
        Build academic anchors from term versions

        Args:
            term_versions: List of TermVersion instances

        Returns:
            List of anchor dictionaries
        """
        academic_anchors = []

        for version in term_versions:
            academic_anchors.append({
                'year': version.temporal_start_year,
                'period': version.temporal_period,
                'meaning': version.meaning_description,
                'citation': version.source_citation,
                'domain': version.extraction_method.replace('_analysis', '').replace(' analysis', ''),
                'confidence': version.confidence_level,
                'context_anchor': version.context_anchor or []
            })

        return academic_anchors

    def _calculate_metrics(self, academic_anchors: List[Dict]) -> Tuple[int, List[str]]:
        """
        Calculate temporal span and domains

        Args:
            academic_anchors: List of anchor dictionaries

        Returns:
            Tuple of (temporal_span, domains)
        """
        years = [anchor['year'] for anchor in academic_anchors if anchor.get('year')]
        temporal_span = max(years) - min(years) if years else 0

        domains = list(set([anchor['domain'] for anchor in academic_anchors if anchor.get('domain')]))

        return temporal_span, domains

    def _get_oed_data(self, term_record, term: str, term_versions: List) -> Optional[Dict[str, Any]]:
        """
        Get OED data from database or files

        Args:
            term_record: Term database record
            term: Term text
            term_versions: List of term versions

        Returns:
            OED data dictionary or None
        """
        # Try database first
        oed_data = self._get_oed_from_database(term_record)

        if not oed_data:
            # Fallback to file-based loading
            oed_data = self._get_oed_from_files(term)

        # Apply period matching if we have data
        if oed_data and oed_data.get('definitions'):
            oed_data = self._apply_period_matching(oed_data, term_versions, term)

        return oed_data

    def _get_oed_from_database(self, term_record) -> Optional[Dict[str, Any]]:
        """Get OED data from database"""
        from app.models.oed_models import OEDEtymology, OEDDefinition, OEDHistoricalStats, OEDQuotationSummary

        etymology = OEDEtymology.query.filter_by(term_id=term_record.id).first()
        definitions = OEDDefinition.query.filter_by(
            term_id=term_record.id
        ).order_by(OEDDefinition.first_cited_year.asc()).all()
        historical_stats = OEDHistoricalStats.query.filter_by(
            term_id=term_record.id
        ).order_by(OEDHistoricalStats.start_year.asc()).all()
        quotation_summaries = OEDQuotationSummary.query.filter_by(
            term_id=term_record.id
        ).order_by(OEDQuotationSummary.quotation_year.asc()).all()

        if etymology or definitions or historical_stats:
            return {
                'etymology': etymology.to_dict() if etymology else None,
                'definitions': [d.to_dict() for d in definitions],
                'historical_stats': [s.to_dict() for s in historical_stats],
                'quotation_summaries': [q.to_dict() for q in quotation_summaries],
                'date_range': {
                    'earliest': min([d.first_cited_year for d in definitions if d.first_cited_year], default=None),
                    'latest': max([d.last_cited_year for d in definitions if d.last_cited_year], default=None)
                }
            }

        return None

    def _get_oed_from_files(self, term: str) -> Optional[Dict[str, Any]]:
        """Get OED data from JSON files"""
        oed_patterns = [
            f'data/references/oed_{term}_extraction_provenance.json',
            f'data/references/{term}_oed_extraction.json'
        ]

        for pattern in oed_patterns:
            try:
                with open(pattern, 'r') as f:
                    return json.load(f)
            except FileNotFoundError:
                continue

        return None

    def _apply_period_matching(
        self,
        oed_data: Dict[str, Any],
        term_versions: List,
        term: str
    ) -> Dict[str, Any]:
        """Apply period-aware matching to OED definitions"""
        from app.services.period_matching_service import PeriodMatchingService

        # Get target years from term versions
        target_years = [
            version.temporal_start_year
            for version in term_versions
            if version.temporal_start_year
        ]

        if not target_years:
            return oed_data

        try:
            matching_service = PeriodMatchingService()
            enhanced_definitions = matching_service.enhance_definitions_with_period_matching(
                oed_data['definitions'], target_years, term
            )
            oed_data['definitions'] = enhanced_definitions

            logger.info(f"Matched {len(enhanced_definitions)} definitions to periods: {target_years}")

        except Exception as e:
            logger.warning(f"Failed to match definitions with periods: {e}")
            # Continue with original definitions

        return oed_data

    def _get_legal_data(self, term: str) -> Optional[Dict[str, Any]]:
        """Get legal reference data from files"""
        legal_patterns = [
            f'data/references/blacks_law_{term}_extraction.json',
            f'data/references/{term}_legal_extraction.json'
        ]

        for pattern in legal_patterns:
            try:
                with open(pattern, 'r') as f:
                    return json.load(f)
            except FileNotFoundError:
                continue

        return None

    def _build_analysis_text(
        self,
        narrative: str,
        drift_analysis: Dict[str, Any],
        term: str,
        temporal_service
    ) -> str:
        """
        Build comprehensive analysis text

        Args:
            narrative: Evolution narrative
            drift_analysis: Drift analysis results
            term: Term being analyzed
            temporal_service: Temporal analysis service

        Returns:
            Complete analysis text
        """
        parts = [narrative, "\n\n--- Semantic Drift Analysis ---\n"]

        # Add drift metrics
        if drift_analysis.get('average_drift') is not None:
            parts.append(f"Average Semantic Drift: {drift_analysis['average_drift']:.2%}\n")

        if drift_analysis.get('stable_terms'):
            parts.append(f"Stable Associated Terms: {', '.join(drift_analysis['stable_terms'][:5])}\n")

        # Add period-by-period details
        if drift_analysis.get('periods'):
            parts.append("\nPeriod-by-Period Changes:\n")
            for period_range, period_data in drift_analysis['periods'].items():
                parts.append(f"\n{period_range}:")
                parts.append(f"  - Drift Score: {period_data['drift_score']:.2%}")
                if period_data.get('new_terms'):
                    parts.append(f"  - New Terms: {', '.join(period_data['new_terms'][:3])}")
                if period_data.get('lost_terms'):
                    parts.append(f"  - Lost Terms: {', '.join(period_data['lost_terms'][:3])}")

        # Add ontology mapping insights
        parts.append("\n\n--- Ontology Mapping Insights ---\n")
        prov_mapping = self._get_prov_mapping(term)
        parts.append(prov_mapping)

        return '\n'.join(parts)

    def _get_prov_mapping(self, term: str) -> str:
        """Get PROV-O ontology mapping for term"""
        prov_mappings = {
            'agent': 'prov:Agent - An entity that bears responsibility',
            'activity': 'prov:Activity - Something that occurs over time',
            'entity': 'prov:Entity - A physical, digital, or conceptual thing',
            'process': 'prov:Activity - A series of actions or operations',
            'artifact': 'prov:Entity - A thing produced or used',
            'actor': 'prov:Agent - One who performs actions'
        }

        term_lower = term.lower()
        if term_lower in prov_mappings:
            return f"PROV-O Mapping: {prov_mappings[term_lower]}"
        else:
            return f"No direct PROV-O mapping found for '{term}'"


# Singleton instance
_evolution_service = None


def get_evolution_service() -> EvolutionService:
    """
    Get the singleton EvolutionService instance

    Returns:
        EvolutionService instance
    """
    global _evolution_service
    if _evolution_service is None:
        _evolution_service = EvolutionService()
    return _evolution_service
