"""
Term Service

Business logic for term management in domain comparison experiments.
Handles term configuration, definition fetching, and ontology mapping.
"""

import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from app import db
from app.models import Experiment
from app.models.user import User
from app.services.base_service import (
    BaseService,
    NotFoundError,
    PermissionError,
    ServiceError,
    ValidationError,
)

logger = logging.getLogger(__name__)


class TermService(BaseService):
    """
    Service for term management operations

    Handles all business logic related to terms including:
    - Managing terms and domains for experiments
    - Fetching definitions from references
    - Mapping terms to ontology concepts
    - Configuration management
    """

    def __init__(self):
        """Initialize TermService"""
        super().__init__(model=Experiment)

    def get_term_configuration(
        self,
        experiment_id: int
    ) -> Dict[str, Any]:
        """
        Get term configuration for an experiment

        Args:
            experiment_id: ID of experiment

        Returns:
            Dictionary with terms, domains, and definitions

        Raises:
            NotFoundError: If experiment doesn't exist
            ValidationError: If experiment is not domain_comparison type
            ServiceError: If operation fails
        """
        try:
            experiment = self._get_experiment(experiment_id)

            # Validate experiment type
            if experiment.experiment_type != 'domain_comparison':
                raise ValidationError(
                    'Term management is only available for domain comparison experiments'
                )

            # Parse configuration
            config = self._parse_configuration(experiment)

            terms = config.get('target_terms', [])
            domains = config.get('domains', [])
            definitions = config.get('term_definitions', {})

            # Use default domains if not specified
            if not domains:
                domains = ['Computer Science', 'Philosophy', 'Law']

            return {
                'terms': terms,
                'domains': domains,
                'definitions': definitions
            }

        except (NotFoundError, PermissionError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Failed to get term configuration for experiment {experiment_id}: {e}", exc_info=True)
            raise ServiceError(f"Failed to get term configuration: {str(e)}") from e

    def get_experiment(self, experiment_id: int) -> Experiment:
        """Return an experiment used by the term manager presentation layer."""
        return self._get_experiment(experiment_id)

    def update_term_configuration(
        self,
        experiment_id: int,
        terms: List[str],
        domains: List[str],
        definitions: Optional[Dict[str, Any]] = None,
        actor_id: Optional[int] = None,
    ) -> Experiment:
        """
        Update term configuration for an experiment

        Args:
            experiment_id: ID of experiment
            terms: List of target terms
            domains: List of domains
            definitions: Optional dictionary of term definitions

        Returns:
            Updated experiment instance

        Raises:
            NotFoundError: If experiment doesn't exist
            ValidationError: If validation fails
            ServiceError: If update fails
        """
        try:
            experiment = self._get_experiment(experiment_id)
            self._require_edit_permission(experiment, actor_id)

            # Validate experiment type
            if experiment.experiment_type != 'domain_comparison':
                raise ValidationError(
                    'Term management is only available for domain comparison experiments'
                )

            # Validate inputs
            if not isinstance(terms, list):
                raise ValidationError('Terms must be a list')

            if not isinstance(domains, list):
                raise ValidationError('Domains must be a list')

            terms = self._normalize_strings(terms, 'Terms')
            domains = self._normalize_strings(domains, 'Domains')
            if definitions is not None and not isinstance(definitions, dict):
                raise ValidationError('Definitions must be an object')

            # Parse existing configuration
            config = self._parse_configuration(experiment)

            # Update configuration
            config['target_terms'] = terms
            config['domains'] = domains
            if definitions is not None:
                config['term_definitions'] = definitions

            # Save configuration
            experiment.configuration = json.dumps(config)
            experiment.updated_at = datetime.utcnow()

            self.commit()

            logger.info(
                f"Updated term configuration for experiment {experiment_id}: "
                f"{len(terms)} terms, {len(domains)} domains"
            )

            return experiment

        except (NotFoundError, PermissionError, ValidationError):
            raise
        except Exception as e:
            self.rollback()
            logger.error(f"Failed to update term configuration for experiment {experiment_id}: {e}", exc_info=True)
            raise ServiceError(f"Failed to update term configuration: {str(e)}") from e

    def fetch_definitions(
        self,
        experiment_id: int,
        term: str,
        domains: List[str],
        actor_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Fetch definitions for a term from references and ontologies

        Args:
            experiment_id: ID of experiment
            term: Term to fetch definitions for
            domains: List of domains to search

        Returns:
            Dictionary with definitions and ontology mappings

        Raises:
            NotFoundError: If experiment doesn't exist
            ValidationError: If validation fails
            ServiceError: If operation fails
        """
        try:
            experiment = self._get_experiment(experiment_id)
            self._require_edit_permission(experiment, actor_id)

            term = term.strip() if isinstance(term, str) else ''
            if not term:
                raise ValidationError('Term is required')
            if not isinstance(domains, list):
                raise ValidationError('Domains must be a list')
            domains = self._normalize_strings(domains, 'Domains')
            if not domains:
                raise ValidationError('At least one domain is required')

            definitions = {}
            ontology_mappings = {}

            # For each domain, try to find definitions from references
            for domain in domains:
                domain_definitions = self._search_references_for_term(
                    experiment,
                    term,
                    domain
                )

                if domain_definitions:
                    definitions[domain] = domain_definitions[0]
                else:
                    definitions[domain] = {
                        'text': f'No definition found for "{term}" in {domain} references',
                        'source': None
                    }

                # Map to ontology concepts
                ontology_mappings[domain] = self._map_to_ontology(term)

            logger.info(
                f"Fetched definitions for term '{term}' in {len(domains)} domains "
                f"for experiment {experiment_id}"
            )

            return {
                'definitions': definitions,
                'ontology_mappings': ontology_mappings
            }

        except (NotFoundError, PermissionError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Failed to fetch definitions for experiment {experiment_id}: {e}", exc_info=True)
            raise ServiceError(f"Failed to fetch definitions: {str(e)}") from e

    # Private helper methods

    def _get_experiment(self, experiment_id: int) -> Experiment:
        """
        Get experiment by ID

        Args:
            experiment_id: ID of experiment

        Returns:
            Experiment instance

        Raises:
            NotFoundError: If experiment doesn't exist
        """
        experiment = Experiment.query.filter_by(id=experiment_id).first()

        if not experiment:
            raise NotFoundError(f"Experiment {experiment_id} not found")

        return experiment

    def _parse_configuration(self, experiment: Experiment) -> Dict[str, Any]:
        """
        Parse experiment configuration JSON

        Args:
            experiment: Experiment instance

        Returns:
            Parsed configuration dictionary
        """
        if not experiment.configuration:
            return {}

        if isinstance(experiment.configuration, dict):
            return dict(experiment.configuration)

        try:
            return json.loads(experiment.configuration)
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"Failed to parse configuration for experiment {experiment.id}")
            return {}

    @staticmethod
    def _normalize_strings(values, field_name):
        normalized = []
        seen = set()
        for value in values:
            if not isinstance(value, str):
                raise ValidationError(f'All {field_name.lower()} must be strings')
            value = value.strip()
            if not value:
                raise ValidationError(f'{field_name} cannot contain blank values')
            if value not in seen:
                seen.add(value)
                normalized.append(value)
        return normalized

    @staticmethod
    def _require_edit_permission(experiment, actor_id):
        if actor_id is None:
            return
        actor = db.session.get(User, actor_id)
        if not actor or not actor.can_edit_resource(experiment):
            raise PermissionError('Permission denied')

    def _search_references_for_term(
        self,
        experiment: Experiment,
        term: str,
        domain: str
    ) -> List[Dict[str, str]]:
        """
        Search experiment references for term definitions

        Args:
            experiment: Experiment instance
            term: Term to search for
            domain: Domain context

        Returns:
            List of definition dictionaries
        """
        domain_definitions = []

        for ref in experiment.references:
            # Check if reference matches domain (simple heuristic)
            ref_content = ref.content or ''
            if term.lower() in ref_content.lower():
                # Extract definition context
                lines = ref_content.split('\n')
                for i, line in enumerate(lines):
                    if term.lower() in line.lower():
                        # Get surrounding context
                        start = max(0, i - 2)
                        end = min(len(lines), i + 3)
                        context = '\n'.join(lines[start:end])

                        domain_definitions.append({
                            'text': context[:500],  # Limit length
                            'source': ref.get_display_name()
                        })
                        break

        return domain_definitions

    def _map_to_ontology(self, term: str) -> List[Dict[str, str]]:
        """
        Map term to ontology concepts

        Args:
            term: Term to map

        Returns:
            List of ontology mapping dictionaries
        """
        mappings = []
        term_lower = term.lower()

        # Simple mapping based on common terms (using PROV-O as example)
        if term_lower in ['agent', 'actor', 'person', 'user']:
            mappings.append({
                'label': 'prov:Agent',
                'description': 'An agent is something that bears some form of responsibility for an activity taking place'
            })
        elif term_lower in ['activity', 'process', 'action', 'task']:
            mappings.append({
                'label': 'prov:Activity',
                'description': 'An activity is something that occurs over a period of time and acts upon or with entities'
            })
        elif term_lower in ['entity', 'object', 'data', 'document']:
            mappings.append({
                'label': 'prov:Entity',
                'description': 'An entity is a physical, digital, conceptual, or other kind of thing'
            })

        return mappings


# Singleton instance for easy access
_term_service = None


def get_term_service() -> TermService:
    """
    Get the singleton TermService instance

    Returns:
        TermService instance
    """
    global _term_service
    if _term_service is None:
        _term_service = TermService()
    return _term_service
