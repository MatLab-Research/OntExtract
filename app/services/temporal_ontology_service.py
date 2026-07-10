"""Read models for semantic-event and temporal-period ontology catalogs."""

from pathlib import Path

from app import db
from app.models.experiment import Experiment
from app.services.base_service import NotFoundError, ValidationError
from app.services.local_ontology_service import get_ontology_service
from app.services.ontserve_client import get_ontserve_client


class TemporalOntologyService:
    """Provide ontology catalogs with stable UI fallbacks."""

    EVENT_SOURCE = 'semantic-change-ontology-v2.ttl'
    EVENT_FALLBACK = [
        {
            'value': 'pejoration',
            'label': 'Pejoration',
            'definition': 'Negative shift in word meaning or connotation',
            'citation': 'Jatowt & Duh 2014',
            'example': None,
            'uri': None,
        },
        {
            'value': 'amelioration',
            'label': 'Amelioration',
            'definition': 'Positive shift in word meaning or connotation',
            'citation': 'Jatowt & Duh 2014',
            'example': None,
            'uri': None,
        },
        {
            'value': 'semantic_drift',
            'label': 'Semantic Drift',
            'definition': (
                'Gradual, incremental meaning change over extended period'
            ),
            'citation': 'Hamilton et al. 2016',
            'example': None,
            'uri': None,
        },
    ]
    PERIOD_FALLBACK = [
        {
            'value': 'HistoricalPeriod',
            'label': 'Historical Period',
            'description': 'Historically-defined temporal span',
            'color': '#6f42c1',
            'icon': 'fas fa-landmark',
            'uri': None,
        },
        {
            'value': 'DisciplinaryEra',
            'label': 'Disciplinary Era',
            'description': 'Era defined by disciplinary conventions',
            'color': '#0d6efd',
            'icon': 'fas fa-graduation-cap',
            'uri': None,
        },
        {
            'value': 'TechnologicalEpoch',
            'label': 'Technological Epoch',
            'description': 'Period marked by technological developments',
            'color': '#198754',
            'icon': 'fas fa-microchip',
            'uri': None,
        },
        {
            'value': 'CulturalMovement',
            'label': 'Cultural Movement',
            'description': 'Period defined by cultural or intellectual movement',
            'color': '#d63384',
            'icon': 'fas fa-palette',
            'uri': None,
        },
    ]

    def __init__(
        self,
        local_ontology=None,
        period_client=None,
        repository_root=None,
    ):
        self.local_ontology = local_ontology or get_ontology_service()
        self.period_client = period_client or get_ontserve_client()
        self.repository_root = (
            Path(repository_root)
            if repository_root else Path(__file__).resolve().parents[2]
        )

    def get_event_catalog(self, experiment_id=None):
        if experiment_id is not None:
            self._temporal_experiment(experiment_id)
        try:
            event_types = self.local_ontology.get_all_for_dropdown()
            return {
                'success': True,
                'event_types': event_types,
                'count': len(event_types),
                'source': self.EVENT_SOURCE,
            }
        except Exception as exc:
            fallback = [dict(item) for item in self.EVENT_FALLBACK]
            return {
                'success': True,
                'event_types': fallback,
                'count': len(fallback),
                'source': 'fallback (ontology load failed)',
                'error': str(exc),
            }

    def get_event_type(self, value):
        catalog = self.get_event_catalog()
        return next(
            (
                item for item in catalog['event_types']
                if item['value'] == value
            ),
            None,
        )

    def get_period_catalog(self):
        try:
            period_types = [
                {
                    'value': item['name'],
                    'label': item['label'],
                    'description': item['description'],
                    'uri': item['uri'],
                    'color': item['color'],
                    'icon': item['icon'],
                }
                for item in self.period_client.get_period_types()
            ]
            return {
                'success': True,
                'period_types': period_types,
                'count': len(period_types),
                'source': 'ontology',
            }
        except Exception as exc:
            fallback = [dict(item) for item in self.PERIOD_FALLBACK]
            return {
                'success': True,
                'period_types': fallback,
                'count': len(fallback),
                'source': 'fallback (ontology load failed)',
                'error': str(exc),
            }

    def get_info_context(self):
        event_types = self.local_ontology.get_semantic_change_event_types()
        ontology_path = Path(self.local_ontology.ontology_path).resolve()
        try:
            display_path = str(ontology_path.relative_to(self.repository_root))
        except ValueError:
            display_path = str(ontology_path)
        validation_path = self.repository_root / 'VALIDATION_GUIDE.md'
        return {
            'event_types': event_types,
            'event_count': len(event_types),
            'ontology_path': display_path,
            'validation_exists': validation_path.exists(),
        }

    @staticmethod
    def _temporal_experiment(experiment_id):
        experiment = db.session.get(Experiment, experiment_id)
        if not experiment:
            raise NotFoundError('Experiment not found')
        if experiment.experiment_type != 'temporal_evolution':
            raise ValidationError(
                'Semantic event types are only available for temporal '
                'evolution experiments'
            )
        return experiment
