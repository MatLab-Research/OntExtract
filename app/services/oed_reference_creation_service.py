"""Single and batch OED reference creation workflows."""

from dataclasses import dataclass
from urllib.parse import quote_plus

from flask import current_app

from app import db
from app.models.document import Document
from app.models.experiment import Experiment, experiment_references
from app.models.user import User
from app.services.base_service import NotFoundError, PermissionError, ValidationError


class OEDLookupError(ValidationError):
    """An OED entry could not be loaded from the configured source."""


@dataclass(frozen=True)
class OEDReferenceResult:
    document: Document
    experiment: Experiment | None


@dataclass(frozen=True)
class OEDReferenceBatchResult:
    documents: list[Document]
    errors: list[str]
    experiment: Experiment | None


class OEDReferenceCreationService:
    """Build, persist, link, and provenance-track OED references."""

    DEFAULT_API_BASE = (
        'https://oed-researcher-api.oxfordlanguages.com/oed/api/v0.2'
    )

    def __init__(
        self,
        oed_service,
        provenance_service=None,
        workflow_logger=None,
        api_base=None,
    ):
        self.oed_service = oed_service
        self.provenance_service = provenance_service
        self.logger = workflow_logger
        self.api_base = (
            api_base
            or current_app.config.get('OED_API_BASE_URL')
            or self.DEFAULT_API_BASE
        ).rstrip('/')

    def create_one(
        self,
        entry_id,
        actor,
        selected_sense_ids=None,
        title_override=None,
        experiment_id=None,
        include_in_analysis=False,
    ):
        experiment = self._editable_experiment(experiment_id, actor.id)
        document = self.build_unsaved(
            entry_id,
            actor.id,
            selected_sense_ids,
            title_override,
        )
        self._persist([document], experiment, include_in_analysis)
        self._track_best_effort(document, actor, experiment)
        return OEDReferenceResult(document=document, experiment=experiment)

    def create_batch(
        self,
        entry_ids,
        actor,
        experiment_id=None,
        include_in_analysis=False,
    ):
        normalized_ids = self._entry_ids(entry_ids)
        if not normalized_ids:
            raise ValidationError('No entry IDs selected.')
        experiment = self._editable_experiment(experiment_id, actor.id)
        documents = []
        errors = []
        for entry_id in normalized_ids:
            try:
                documents.append(self.build_unsaved(entry_id, actor.id))
            except OEDLookupError as exc:
                errors.append(f'{entry_id}: {exc}')
        if documents:
            self._persist(documents, experiment, include_in_analysis)
            for document in documents:
                self._track_best_effort(document, actor, experiment)
        return OEDReferenceBatchResult(
            documents=documents,
            errors=errors,
            experiment=experiment,
        )

    def build_unsaved(
        self,
        entry_id,
        user_id,
        selected_sense_ids=None,
        title_override=None,
    ):
        entry_id = self._clean(entry_id)
        if not entry_id:
            raise ValidationError('Entry ID is required (e.g., orchestra_nn01)')
        result = self.oed_service.get_word(entry_id)
        if not result.get('success'):
            raise OEDLookupError(result.get('error', 'unknown error'))
        payload = result.get('data') or {}
        headword = payload.get('headword') or payload.get('word') or entry_id
        part_of_speech = payload.get('pos') or payload.get('part_of_speech')
        senses = self._all_senses(payload)
        selected = self._select_senses(senses, selected_sense_ids)

        content = f'OED entry: {entry_id}\nHeadword: {headword}'
        if part_of_speech:
            content += f'\nPart of speech: {part_of_speech}'
        if selected:
            content += (
                '\nSelected senses: '
                + ', '.join(sense['sense_id'] for sense in selected)
            )
        metadata = {
            'source': 'OED Researcher API',
            'oed_entry_id': entry_id,
            'headword': headword,
            'part_of_speech': part_of_speech,
            'oed_api_word_url': f'{self.api_base}/word/{entry_id}/',
            'oed_web_search_url': (
                'https://www.oed.com/search/dictionary/?q='
                f'{quote_plus(str(headword))}'
            ),
        }
        if selected:
            metadata['selected_senses'] = selected
        title = self._clean(title_override) or f'OED: {headword}'
        return Document(
            title=title,
            content_type='text',
            document_type='reference',
            reference_subtype='dictionary_oed',
            content=content,
            content_preview=content[:500],
            source_metadata=metadata,
            user_id=user_id,
            status='completed',
            word_count=len(content.split()),
            character_count=len(content),
        )

    @classmethod
    def _all_senses(cls, payload):
        merged = {}
        for sense in cls._flatten_senses(payload.get('senses') or []):
            merged[sense['sense_id']] = sense
        for sense in cls._flatten_senses(payload.get('extracted_senses') or []):
            merged.setdefault(sense['sense_id'], sense)
        return list(merged.values())

    @classmethod
    def _flatten_senses(cls, senses):
        flattened = []
        for sense in senses if isinstance(senses, list) else []:
            if not isinstance(sense, dict):
                continue
            sense_id = str(
                sense.get('sense_id')
                or sense.get('id')
                or sense.get('oid')
                or ''
            )
            if sense_id:
                definition = sense.get('definition') or ''
                if isinstance(definition, list):
                    definition = definition[0] if definition else ''
                flattened.append({
                    'sense_id': sense_id,
                    'label': sense.get('label', ''),
                    'definition': cls._excerpt(definition),
                })
            for field in ('subsenses', 'children', 'senses'):
                flattened.extend(cls._flatten_senses(sense.get(field) or []))
        return flattened

    @staticmethod
    def _select_senses(senses, selected_sense_ids):
        selected_ids = {
            str(value) for value in (selected_sense_ids or []) if value
        }
        if not selected_ids:
            return senses
        return [
            sense for sense in senses
            if sense['sense_id'] in selected_ids
        ]

    @staticmethod
    def _excerpt(definition):
        if not isinstance(definition, str) or not definition.strip():
            return ''
        excerpt = ' '.join(definition.split()[:20])
        return excerpt[:200]

    @staticmethod
    def _entry_ids(values):
        return list(dict.fromkeys(
            value.strip()
            for value in (values or [])
            if isinstance(value, str) and value.strip()
        ))

    @staticmethod
    def _editable_experiment(experiment_id, actor_id):
        if experiment_id in (None, ''):
            return None
        try:
            normalized_id = int(experiment_id)
        except (TypeError, ValueError) as exc:
            raise NotFoundError('Experiment not found') from exc
        experiment = db.session.get(Experiment, normalized_id)
        if not experiment:
            raise NotFoundError('Experiment not found')
        actor = db.session.get(User, actor_id)
        if not actor or not actor.can_edit_resource(experiment):
            raise PermissionError('Permission denied')
        return experiment

    @staticmethod
    def _persist(documents, experiment, include_in_analysis):
        try:
            db.session.add_all(documents)
            db.session.flush()
            if experiment:
                for document in documents:
                    db.session.execute(experiment_references.insert().values(
                        experiment_id=experiment.id,
                        reference_id=document.id,
                        include_in_analysis=bool(include_in_analysis),
                    ))
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

    def _track_best_effort(self, document, actor, experiment):
        if not self.provenance_service:
            return
        try:
            self.provenance_service.track_reference_creation(
                document=document,
                user=actor,
                source='OED',
                experiment=experiment,
                source_metadata=document.source_metadata,
            )
        except Exception as exc:
            if not db.session.is_active:
                db.session.rollback()
            if self.logger:
                self.logger.warning(
                    f'Failed to track OED reference provenance: {exc}'
                )

    @staticmethod
    def _clean(value):
        return value.strip() if isinstance(value, str) else ''
