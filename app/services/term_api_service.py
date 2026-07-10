"""Autocomplete, context discovery, and fuzziness API workflows."""

from decimal import Decimal
from uuid import UUID

from app import db
from app.models.context_anchor import ContextAnchor
from app.models.term import FuzzinessAdjustment, Term, TermVersion
from app.models.user import User
from app.services.base_service import (
    NotFoundError,
    PermissionError,
    ServiceError,
    ValidationError,
)


class AnalysisUnavailableError(ServiceError):
    """The optional shared term-analysis service is unavailable."""


class TermApiService:
    """Serve term utility APIs with bounded queries and validated identities."""

    @classmethod
    def search_context_anchors(cls, query='', limit=20):
        anchors = ContextAnchor.search_anchors(
            cls._clean(query),
            cls._limit(limit, 20),
        )
        return [
            {
                'id': str(anchor.id),
                'term': anchor.anchor_term,
                'frequency': anchor.frequency,
            }
            for anchor in anchors
        ]

    @classmethod
    def search_terms(cls, query='', limit=10):
        terms = Term.search_terms(cls._clean(query)).limit(
            cls._limit(limit, 10)
        ).all()
        return [term.to_dict() for term in terms]

    @classmethod
    def discover_context_anchors(
        cls,
        term_text,
        meaning_description='',
        limit=10,
        analysis_service=None,
    ):
        term_text = cls._clean(term_text)
        if not term_text:
            raise ValidationError('Term text is required')
        limit = cls._limit(limit, 10)
        embedding_service = (
            analysis_service.embedding_service if analysis_service else None
        )
        if not embedding_service or (
            hasattr(embedding_service, 'is_available')
            and not embedding_service.is_available()
        ):
            return cls._existing_anchor_fallback(limit)

        combined_text = term_text
        meaning_description = cls._clean(meaning_description)
        if meaning_description:
            combined_text += f'. {meaning_description}'
        try:
            term_embedding = embedding_service.get_embedding(combined_text)
            anchors = ContextAnchor.query.order_by(
                ContextAnchor.frequency.desc()
            ).limit(100).all()
            similarities = []
            for anchor in anchors:
                try:
                    anchor_embedding = embedding_service.get_embedding(
                        anchor.anchor_term
                    )
                    similarity = embedding_service.similarity(
                        term_embedding,
                        anchor_embedding,
                    )
                    similarities.append({
                        'term': anchor.anchor_term,
                        'frequency': anchor.frequency,
                        'similarity': round(float(similarity), 3),
                        'source': 'embedding_similarity',
                    })
                except Exception:
                    continue
            similarities.sort(
                key=lambda item: item['similarity'],
                reverse=True,
            )
            return similarities[:limit]
        except Exception as exc:
            raise ServiceError('Context anchor discovery failed') from exc

    @classmethod
    def adjust_fuzziness(
        cls,
        term_id,
        version_id,
        score,
        reason,
        actor_id,
    ):
        term, version = cls._term_and_version(term_id, version_id)
        actor = db.session.get(User, actor_id)
        if not actor or (not actor.is_admin and term.created_by != actor.id):
            raise PermissionError('Permission denied')
        try:
            score = Decimal(str(score))
        except Exception as exc:
            raise ValidationError(
                'Fuzziness score must be between 0 and 1.'
            ) from exc
        if not score.is_finite() or score < 0 or score > 1:
            raise ValidationError('Fuzziness score must be between 0 and 1.')
        reason = cls._clean(reason)
        if not reason:
            raise ValidationError('Adjustment reason is required.')
        original = version.fuzziness_score or Decimal('0')
        adjustment = FuzzinessAdjustment(
            term_version_id=version.id,
            original_score=original,
            adjusted_score=score,
            adjustment_reason=reason,
            adjusted_by=actor.id,
        )
        version.fuzziness_score = score
        try:
            db.session.add(adjustment)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
        return adjustment

    @classmethod
    def calculate_fuzziness(cls, term_id, version_id, analysis_service):
        term, version = cls._term_and_version(term_id, version_id)
        if not analysis_service:
            raise AnalysisUnavailableError('Analysis service not available')
        calculator = getattr(
            analysis_service,
            'calculate_fuzziness_score',
            None,
        )
        if not calculator:
            raise AnalysisUnavailableError('Analysis service not available')
        score, confidence = calculator(term, version)
        return {
            'success': True,
            'fuzziness_score': round(float(score), 3),
            'confidence_level': confidence,
            'method': (
                'shared_services'
                if getattr(analysis_service, 'semantic_tracker', None)
                else 'heuristic'
            ),
        }

    @classmethod
    def _term_and_version(cls, term_id, version_id):
        normalized_term = cls._uuid(term_id, 'Term')
        normalized_version = cls._uuid(version_id, 'Term version')
        term = db.session.get(Term, normalized_term)
        if not term:
            raise NotFoundError(f'Term {term_id} not found')
        version = db.session.get(TermVersion, normalized_version)
        if not version:
            raise NotFoundError(f'Term version {version_id} not found')
        if version.term_id != term.id:
            raise ValidationError('Invalid version for this term.')
        return term, version

    @staticmethod
    def _existing_anchor_fallback(limit):
        anchors = ContextAnchor.query.order_by(
            ContextAnchor.frequency.desc()
        ).limit(limit).all()
        return [
            {
                'term': anchor.anchor_term,
                'frequency': anchor.frequency,
                'similarity': 0.0,
                'source': 'existing',
            }
            for anchor in anchors
        ]

    @staticmethod
    def _limit(value, default):
        try:
            value = int(value)
        except (TypeError, ValueError):
            value = default
        return max(1, min(value, 100))

    @staticmethod
    def _uuid(value, label):
        try:
            return UUID(str(value))
        except (TypeError, ValueError, AttributeError) as exc:
            raise NotFoundError(f'{label} {value} not found') from exc

    @staticmethod
    def _clean(value):
        return value.strip() if isinstance(value, str) else ''
