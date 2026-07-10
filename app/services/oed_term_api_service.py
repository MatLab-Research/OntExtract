"""API-facing OED enrichment, persistence reads, and search workflows."""

import uuid

from sqlalchemy import func

from app import db
from app.models.experiment import Experiment
from app.models.oed_models import (
    OEDDefinition,
    OEDEtymology,
    OEDHistoricalStats,
    OEDQuotationSummary,
)
from app.models.term import Term
from app.models.user import User
from app.services.base_service import (
    NotFoundError,
    PermissionError,
    ServiceError,
    ValidationError,
)


class OEDTermUpstreamError(ServiceError):
    """OED term enrichment or lookup could not be completed."""


class OEDTermApiService:
    """Resolve terms safely and expose normalized OED API read models."""

    def __init__(self, enrichment_service=None, oed_service=None):
        self.enrichment_service = enrichment_service
        self.oed_service = oed_service

    def enrich(
        self,
        term_text,
        actor_id,
        experiment_id=None,
        entry_id=None,
    ):
        term_text = self._required_text(term_text, 'term_text')
        actor = db.session.get(User, actor_id)
        experiment = self._editable_experiment(experiment_id, actor)
        term = self._resolve_term(term_text, actor, experiment)
        if not actor or not self._can_edit_term(actor, term):
            raise PermissionError('Permission denied')
        if not self.enrichment_service:
            raise OEDTermUpstreamError('OED enrichment service is unavailable')
        try:
            result = self.enrichment_service.enrich_term_with_oed_data(
                str(term.id),
                self._optional_text(entry_id),
            )
        except Exception as exc:
            raise OEDTermUpstreamError('OED term enrichment failed') from exc
        if not isinstance(result, dict) or not result.get('success'):
            raise OEDTermUpstreamError('OED term enrichment failed')
        return result

    @classmethod
    def get_persisted_data(cls, term_id):
        term_uuid = cls._uuid(term_id)
        term = db.session.get(Term, term_uuid)
        if not term:
            raise NotFoundError('Term not found')
        etymology = OEDEtymology.query.filter_by(term_id=term.id).first()
        definitions = OEDDefinition.query.filter_by(
            term_id=term.id
        ).order_by(
            OEDDefinition.first_cited_year.asc().nullslast(),
            OEDDefinition.definition_number,
        ).all()
        historical_stats = OEDHistoricalStats.query.filter_by(
            term_id=term.id
        ).order_by(OEDHistoricalStats.start_year.asc()).all()
        quotations = OEDQuotationSummary.query.filter_by(
            term_id=term.id
        ).order_by(
            OEDQuotationSummary.quotation_year.asc().nullslast(),
            OEDQuotationSummary.chronological_rank,
        ).all()
        first_years = [
            definition.first_cited_year
            for definition in definitions
            if definition.first_cited_year is not None
        ]
        last_years = [
            definition.last_cited_year
            for definition in definitions
            if definition.last_cited_year is not None
        ]
        return {
            'term_text': term.term_text,
            'etymology': etymology.to_dict() if etymology else None,
            'definitions': [item.to_dict() for item in definitions],
            'historical_stats': [item.to_dict() for item in historical_stats],
            'quotation_summaries': [item.to_dict() for item in quotations],
            'date_range': {
                'earliest': min(first_years, default=None),
                'latest': max(last_years, default=None),
            },
        }

    def search(self, term_text, limit=10):
        term_text = self._required_text(term_text, 'term parameter')
        limit = self._bounded_limit(limit)
        if not self.oed_service:
            raise OEDTermUpstreamError('OED search service is unavailable')
        try:
            result = self.oed_service.suggest_ids(term_text, limit=limit)
        except Exception as exc:
            raise OEDTermUpstreamError('OED search failed') from exc
        if not isinstance(result, dict) or not result.get('success', False):
            raise OEDTermUpstreamError('OED search failed')
        return result

    @classmethod
    def _resolve_term(cls, term_text, actor, experiment):
        normalized = term_text.casefold()
        if experiment and experiment.term_id:
            term = db.session.get(Term, experiment.term_id)
            if term and term.term_text.casefold() == normalized:
                return term

        query = Term.query.filter(func.lower(Term.term_text) == normalized)
        if experiment:
            term = query.filter(Term.created_by == experiment.user_id).first()
            if term:
                return term
        if actor:
            term = query.filter(Term.created_by == actor.id).first()
            if term:
                return term
            if actor.is_admin:
                term = query.order_by(Term.created_at.asc()).first()
                if term:
                    return term
            term = query.order_by(Term.created_at.asc()).first()
            if term:
                return term
        raise NotFoundError(f'Term "{term_text}" not found in database')

    @staticmethod
    def _editable_experiment(experiment_id, actor):
        if experiment_id in (None, ''):
            return None
        try:
            normalized_id = int(experiment_id)
        except (TypeError, ValueError) as exc:
            raise NotFoundError('Experiment not found') from exc
        experiment = db.session.get(Experiment, normalized_id)
        if not experiment:
            raise NotFoundError('Experiment not found')
        if not actor or not actor.can_edit_resource(experiment):
            raise PermissionError('Permission denied')
        return experiment

    @staticmethod
    def _can_edit_term(actor, term):
        return bool(actor.is_admin or term.created_by == actor.id)

    @staticmethod
    def _uuid(value):
        try:
            return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
        except (TypeError, ValueError, AttributeError) as exc:
            raise NotFoundError('Term not found') from exc

    @staticmethod
    def _required_text(value, field):
        value = value.strip() if isinstance(value, str) else ''
        if not value:
            raise ValidationError(f'{field} is required')
        return value

    @staticmethod
    def _optional_text(value):
        value = value.strip() if isinstance(value, str) else ''
        return value or None

    @staticmethod
    def _bounded_limit(value):
        try:
            value = int(value)
        except (TypeError, ValueError) as exc:
            raise ValidationError('limit must be an integer') from exc
        return max(1, min(value, 50))
