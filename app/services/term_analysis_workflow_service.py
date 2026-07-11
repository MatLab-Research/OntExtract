"""Authorized persistence workflows around semantic term-analysis algorithms."""

from uuid import UUID

from app import db
from app.models.term import Term, TermVersion
from app.models.user import User
from app.services.base_service import (
    NotFoundError,
    PermissionError,
    ServiceError,
    ValidationError,
)


class AnalysisUnavailableError(ServiceError):
    """The optional term analysis algorithms are unavailable."""


class TermAnalysisWorkflowService:
    """Authorize term analysis and persist normalized results atomically."""

    def __init__(self, analysis_service):
        self.analysis_service = analysis_service

    def analyze(self, term_id, corpus_texts, actor_id):
        term, actor = self._editable_term(term_id, actor_id)
        if not self.analysis_service:
            raise AnalysisUnavailableError('Analysis service not available')
        corpus_texts = self._corpus(corpus_texts)
        current_version = term.get_current_version()
        if not current_version:
            raise ValidationError('Term has no current version')
        try:
            result = self.analysis_service.analyze_term(term, corpus_texts)
        except Exception as exc:
            raise ServiceError('Term analysis failed') from exc
        anchors = self._anchors(getattr(result, 'context_anchors', []))
        try:
            with db.session.begin_nested():
                score = float(getattr(result, 'fuzziness_score', 0) or 0)
                confidence = getattr(result, 'confidence_level', None) or 'medium'
                if score > 0 and current_version.fuzziness_score is None:
                    current_version.fuzziness_score = score
                    current_version.confidence_level = confidence
                existing = list(dict.fromkeys(current_version.context_anchor or []))
                new_anchors = [item for item in anchors if item not in existing][:5]
                if new_anchors:
                    current_version.context_anchor = existing + new_anchors
                    for anchor in new_anchors:
                        current_version.add_context_anchor(anchor, commit=False)
            db.session.commit()
        except Exception as exc:
            raise ServiceError('Failed to persist term analysis') from exc
        return {
            'success': True,
            'analysis': {
                'fuzziness_score': float(getattr(result, 'fuzziness_score', 0) or 0),
                'confidence_level': getattr(result, 'confidence_level', 'medium'),
                'context_anchors': anchors,
                'has_embeddings': getattr(result, 'embeddings', None) is not None,
                'temporal_contexts_count': len(
                    getattr(result, 'temporal_contexts', None) or []
                ),
            },
            'term': term,
            'actor': actor,
        }

    def detect_drift(
        self,
        term_id,
        baseline_version_id,
        comparison_version_id,
        actor_id,
    ):
        term, actor = self._editable_term(term_id, actor_id)
        if not self.analysis_service:
            raise AnalysisUnavailableError('Analysis service not available')
        baseline = self._version(baseline_version_id)
        comparison = self._version(comparison_version_id)
        if baseline.term_id != term.id or comparison.term_id != term.id:
            raise ValidationError('Invalid version for this term')
        if baseline.id == comparison.id:
            raise ValidationError('Versions must be different')
        if (
            baseline.temporal_start_year is not None
            and comparison.temporal_start_year is not None
            and baseline.temporal_start_year >= comparison.temporal_start_year
        ):
            raise ValidationError(
                'Baseline version must precede comparison version'
            )
        try:
            drift = self.analysis_service.detect_semantic_drift(
                term,
                baseline,
                comparison,
            )
        except Exception as exc:
            raise ServiceError('Semantic drift detection failed') from exc
        if not drift:
            raise ServiceError('Semantic drift detection failed')
        try:
            with db.session.begin_nested():
                activity = self.analysis_service.create_semantic_drift_activity(
                    term,
                    baseline,
                    comparison,
                    drift,
                )
                activity.created_by = actor.id
                db.session.add(activity)
            db.session.commit()
        except Exception as exc:
            raise ServiceError('Failed to persist semantic drift') from exc
        return {
            'success': True,
            'drift': drift.to_dict(),
            'activity_id': str(activity.id),
        }

    @staticmethod
    def _editable_term(term_id, actor_id):
        term = db.session.get(Term, term_id)
        if not term:
            raise NotFoundError('Term not found')
        actor = db.session.get(User, actor_id)
        if not actor:
            raise PermissionError('Permission denied')
        if term.created_by is None:
            raise PermissionError('Shared catalog terms are read-only')
        if not actor.is_admin and term.created_by != actor.id:
            raise PermissionError('Permission denied')
        return term, actor

    @staticmethod
    def _version(version_id):
        try:
            normalized = (
                version_id
                if isinstance(version_id, UUID)
                else UUID(str(version_id))
            )
        except (TypeError, ValueError, AttributeError) as exc:
            raise NotFoundError('Term version not found') from exc
        version = db.session.get(TermVersion, normalized)
        if not version:
            raise NotFoundError('Term version not found')
        return version

    @staticmethod
    def _corpus(values):
        if values is None:
            return []
        if not isinstance(values, list):
            raise ValidationError('corpus_texts must be a list')
        cleaned = []
        for value in values[:5]:
            if not isinstance(value, str):
                raise ValidationError('corpus_texts must contain strings')
            value = value.strip()
            if value:
                cleaned.append(value[:100000])
        return cleaned

    @staticmethod
    def _anchors(values):
        anchors = []
        for value in values or []:
            if not isinstance(value, str):
                continue
            value = value.strip()
            if value and value not in anchors:
                anchors.append(value[:255])
        return anchors[:10]
