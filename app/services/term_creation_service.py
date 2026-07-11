"""Atomic term, initial version, and context-anchor creation workflow."""

from datetime import datetime

from sqlalchemy.exc import IntegrityError

from app import db
from app.models.document import Document
from app.models.term import Term, TermVersion
from app.models.user import User
from app.services.base_service import PermissionError, ServiceError, ValidationError


class DuplicateTermError(ValidationError):
    """The creator already owns a term with the supplied text."""


class TermCreationService:
    """Create a term and its first temporal version as one transaction."""

    FIELDS = (
        'term_text',
        'description',
        'etymology',
        'notes',
        'research_domain',
        'selection_rationale',
        'historical_significance',
        'temporal_period',
        'temporal_start_year',
        'temporal_end_year',
        'meaning_description',
        'corpus_source',
        'source_citation',
        'confidence_level',
        'fuzziness_score',
        'context_anchor',
    )

    def __init__(self, provenance_service=None, workflow_logger=None, clock=None):
        self.provenance_service = provenance_service
        self.logger = workflow_logger
        self.clock = clock or datetime.utcnow

    @staticmethod
    def page_context(actor_id):
        actor = db.session.get(User, actor_id)
        if not actor:
            raise PermissionError('Permission denied')
        domains = [
            row[0]
            for row in db.session.query(Term.research_domain).distinct().filter(
                Term.research_domain.isnot(None),
                Term.research_domain != '',
            ).order_by(Term.research_domain).all()
        ]
        documents = Document.query.filter_by(user_id=actor.id).order_by(
            Document.title
        ).all()
        return {'existing_domains': domains, 'documents': documents}

    def create(self, data, actor_id):
        if not isinstance(data, dict):
            raise ValidationError('Invalid term data')
        actor = db.session.get(User, actor_id)
        if not actor:
            raise PermissionError('Permission denied')
        term_text = self._text(data.get('term_text'))
        if not term_text:
            raise ValidationError('Term text is required')
        if Term.query.filter_by(term_text=term_text, created_by=actor.id).first():
            raise DuplicateTermError(f'Term "{term_text}" already exists')
        temporal_period = self._text(data.get('temporal_period'))
        meaning_description = self._text(data.get('meaning_description'))
        if not temporal_period:
            raise ValidationError('Temporal period is required')
        if not meaning_description:
            raise ValidationError('Meaning description is required')
        start_year = data.get('temporal_start_year')
        end_year = data.get('temporal_end_year')
        self._validate_years(start_year, end_year)
        confidence = data.get('confidence_level') or 'medium'
        if confidence not in {'high', 'medium', 'low'}:
            raise ValidationError('Invalid confidence level')
        fuzziness = self._fuzziness(data.get('fuzziness_score'))
        anchors = self._anchors(data.get('context_anchor'))
        term = Term(
            term_text=term_text,
            description=self._optional(data.get('description')),
            etymology=self._optional(data.get('etymology')),
            notes=self._optional(data.get('notes')),
            research_domain=self._optional(data.get('research_domain')),
            selection_rationale=self._optional(data.get('selection_rationale')),
            historical_significance=self._optional(
                data.get('historical_significance')
            ),
            created_by=actor.id,
            status='active',
        )
        version = TermVersion(
            temporal_period=temporal_period,
            temporal_start_year=start_year,
            temporal_end_year=end_year,
            meaning_description=meaning_description,
            corpus_source=self._optional(data.get('corpus_source')),
            source_citation=self._optional(data.get('source_citation')),
            confidence_level=confidence,
            fuzziness_score=fuzziness,
            extraction_method='manual',
            context_anchor=anchors,
            generated_at_time=self.clock(),
            version_number=1,
            is_current=True,
            created_by=actor.id,
        )
        try:
            with db.session.begin_nested():
                db.session.add(term)
                db.session.flush()
                version.term_id = term.id
                db.session.add(version)
                db.session.flush()
                for anchor_term in anchors:
                    version.add_context_anchor(anchor_term, commit=False)
            db.session.commit()
        except IntegrityError as exc:
            if not db.session.is_active:
                db.session.rollback()
            if Term.query.filter_by(
                term_text=term_text,
                created_by=actor.id,
            ).first():
                raise DuplicateTermError(
                    f'Term "{term_text}" already exists'
                ) from exc
            raise ServiceError('Failed to create term') from exc
        except Exception as exc:
            if not db.session.is_active:
                db.session.rollback()
            raise ServiceError('Failed to create term') from exc
        self._track_best_effort(term, actor)
        return term

    def _track_best_effort(self, term, actor):
        if not self.provenance_service:
            return
        try:
            self.provenance_service.track_term_creation(term, actor)
        except Exception as exc:
            if not db.session.is_active:
                db.session.rollback()
            if self.logger:
                self.logger.warning(
                    'Failed to track term creation provenance: %s',
                    exc,
                )

    @classmethod
    def form_data(cls, form):
        return {name: getattr(form, name).data for name in cls.FIELDS}

    @staticmethod
    def _anchors(value):
        if not isinstance(value, str):
            return []
        return list(dict.fromkeys(
            anchor.strip()
            for anchor in value.split(',')
            if anchor.strip()
        ))

    @staticmethod
    def _text(value):
        return value.strip() if isinstance(value, str) else value

    @classmethod
    def _optional(cls, value):
        value = cls._text(value)
        return value or None

    @staticmethod
    def _validate_years(start_year, end_year):
        try:
            normalized = [
                int(year) if year is not None else None
                for year in (start_year, end_year)
            ]
        except (TypeError, ValueError) as exc:
            raise ValidationError('Temporal year must be an integer') from exc
        for year in normalized:
            if year is not None and not 1000 <= year <= 2100:
                raise ValidationError('Temporal year must be between 1000 and 2100')
        if (
            normalized[0] is not None
            and normalized[1] is not None
            and normalized[1] < normalized[0]
        ):
            raise ValidationError('Temporal end year cannot precede start year')

    @staticmethod
    def _fuzziness(value):
        if value is None:
            return None
        try:
            normalized = float(value)
        except (TypeError, ValueError) as exc:
            raise ValidationError('Fuzziness score must be a number') from exc
        if not 0 <= normalized <= 1:
            raise ValidationError('Fuzziness score must be between 0 and 1')
        return normalized
