"""Validated dictionary and pasted-reference creation workflow."""

from dataclasses import dataclass
from datetime import datetime

from app import db
from app.models.document import Document
from app.models.experiment import Experiment, experiment_references
from app.models.user import User
from app.services.base_service import (
    NotFoundError,
    PermissionError,
    ServiceError,
    ValidationError,
)


@dataclass(frozen=True)
class DictionaryReferenceResult:
    document: Document
    experiment: Experiment | None


class DictionaryReferenceCreationService:
    """Create normalized reference records and optional experiment links."""

    ALLOWED_SUBTYPES = {
        'dictionary_general',
        'dictionary_oed',
        'dictionary_mw',
        'thesaurus_mw',
        'other',
    }
    OED_FIELDS = (
        'pronunciation',
        'etymology',
        'usage_notes',
        'examples',
        'first_use',
        'edition',
        'url',
        'citation',
        'pdf_link',
    )
    GENERAL_FIELDS = ('journal', 'context', 'synonyms', 'url', 'citation')

    def __init__(
        self,
        provenance_service=None,
        workflow_logger=None,
        clock=None,
    ):
        self.provenance_service = provenance_service
        self.logger = workflow_logger
        self.clock = clock or datetime.utcnow

    def create(self, form, actor_id):
        actor = db.session.get(User, actor_id)
        if not actor:
            raise PermissionError('Permission denied')
        title = self._required(form.get('title'), 'Term is required', 200)
        content = self._required(
            form.get('content'),
            'Definition is required',
            1_000_000,
        )
        subtype = self._text(
            form.get('reference_subtype') or 'dictionary_general',
            30,
        )
        if subtype not in self.ALLOWED_SUBTYPES:
            raise ValidationError('Unsupported reference subtype')
        experiment = self._experiment(form.get('experiment_id'), actor)
        include_in_analysis = self._boolean(form.get('include_in_analysis'))
        metadata = self._metadata(form, subtype)
        formatted_content = self._content(title, content, subtype, metadata)
        document = Document(
            title=title,
            content_type='text',
            document_type='reference',
            reference_subtype=subtype,
            content=formatted_content,
            content_preview=(
                formatted_content[:500]
                + ('...' if len(formatted_content) > 500 else '')
            ),
            source_metadata=metadata or None,
            user_id=actor.id,
            status='completed',
            word_count=len(formatted_content.split()),
            character_count=len(formatted_content),
        )
        self._persist(document, experiment, include_in_analysis)
        self._track_best_effort(document, actor, experiment, metadata)
        return DictionaryReferenceResult(document, experiment)

    def create_quick(self, data, actor_id):
        if not isinstance(data, dict):
            raise ValidationError('Invalid JSON payload')
        actor = db.session.get(User, actor_id)
        if not actor:
            raise PermissionError('Permission denied')
        title = self._text(data.get('title'), 200)
        content = self._text(data.get('content'), 1_000_000)
        if not title or not content:
            raise ValidationError('Title and content are required')
        source = self._text(data.get('source'), 20).upper()
        if source not in {'MW', 'OED'}:
            raise ValidationError('Unsupported reference source')
        experiment = self._experiment(data.get('experiment_id'), actor)
        now = self.clock()
        term = self._text(data.get('term'), 200)
        entry_url = self._text(data.get('entry_url'), 500)
        source_type = self._text(
            data.get('source_type') or 'dictionary',
            30,
        )
        publisher, location, dictionary_name = self._source_details(source)
        citation = (
            f'"{term or title}." {dictionary_name}, {publisher}. '
            f'Accessed {now.strftime("%d %b %Y")}.'
        )
        metadata = {
            'source_type': source_type,
            'term': term,
            'entry_url': entry_url,
            'access_date': now.strftime('%Y-%m-%d'),
            'publisher': publisher,
            'publisher_location': location,
            'dictionary_name': dictionary_name,
            'citation': citation,
        }
        metadata = {key: value for key, value in metadata.items() if value}
        document = Document(
            title=title,
            content=content,
            content_preview=content[:500] + ('...' if len(content) > 500 else ''),
            document_type='reference',
            reference_subtype=(
                'dictionary_mw' if source == 'MW' else 'dictionary_oed'
            ),
            publisher=publisher,
            citation=citation,
            source_metadata=metadata,
            access_date=now.date(),
            user_id=actor.id,
            content_type='text',
            status='completed',
            word_count=len(content.split()),
            character_count=len(content),
            created_at=now,
        )
        self._persist(
            document,
            experiment,
            self._boolean(data.get('include_in_analysis')),
        )
        self._track_best_effort(
            document,
            actor,
            experiment,
            metadata,
            source=source,
        )
        return DictionaryReferenceResult(document, experiment)

    def _track_best_effort(
        self,
        document,
        actor,
        experiment,
        metadata,
        source=None,
    ):
        if not self.provenance_service:
            return
        try:
            self.provenance_service.track_reference_creation(
                document=document,
                user=actor,
                source=(
                    source
                    or self._source(document.reference_subtype, metadata)
                ),
                experiment=experiment,
                source_metadata=metadata,
            )
        except Exception as exc:
            if not db.session.is_active:
                db.session.rollback()
            if self.logger:
                self.logger.warning(
                    'Failed to track dictionary reference provenance: %s',
                    exc,
                )

    @staticmethod
    def _persist(document, experiment, include_in_analysis):
        try:
            with db.session.begin_nested():
                db.session.add(document)
                db.session.flush()
                if experiment:
                    DictionaryReferenceCreationService._link_experiment(
                        document,
                        experiment,
                        include_in_analysis,
                    )
            db.session.commit()
        except Exception as exc:
            if not db.session.is_active:
                db.session.rollback()
            raise ServiceError('Failed to save dictionary reference') from exc

    @staticmethod
    def _link_experiment(document, experiment, include_in_analysis):
        db.session.execute(experiment_references.insert().values(
            experiment_id=experiment.id,
            reference_id=document.id,
            include_in_analysis=include_in_analysis,
        ))

    @classmethod
    def _metadata(cls, form, subtype):
        fields = cls.OED_FIELDS if subtype == 'dictionary_oed' else cls.GENERAL_FIELDS
        metadata = {
            key: cls._text(form.get(key), cls._field_limit(key))
            for key in fields
        }
        if subtype == 'dictionary_oed':
            metadata['journal'] = 'Oxford English Dictionary'
        return {key: value for key, value in metadata.items() if value}

    @staticmethod
    def _content(title, content, subtype, metadata):
        if subtype == 'dictionary_oed':
            return content
        formatted = f'Term: {title}\n\n'
        formatted += f"Source: {metadata.get('journal', 'Unknown')}\n\n"
        if metadata.get('context'):
            formatted += f"Context/Domain: {metadata['context']}\n\n"
        formatted += f'Definition:\n{content}\n'
        if metadata.get('synonyms'):
            formatted += f"\nSynonyms: {metadata['synonyms']}\n"
        return formatted

    @staticmethod
    def _experiment(experiment_id, actor):
        if experiment_id in (None, ''):
            return None
        try:
            experiment_id = int(experiment_id)
        except (TypeError, ValueError) as exc:
            raise NotFoundError('Experiment not found') from exc
        experiment = db.session.get(Experiment, experiment_id)
        if not experiment:
            raise NotFoundError('Experiment not found')
        if not actor.can_edit_resource(experiment):
            raise PermissionError('Permission denied')
        return experiment

    @staticmethod
    def _source(subtype, metadata):
        if subtype == 'dictionary_oed':
            return 'OED'
        if subtype in {'dictionary_mw', 'thesaurus_mw'}:
            return 'MW'
        return metadata.get('journal') or 'manual'

    @staticmethod
    def _source_details(source):
        if source == 'MW':
            return (
                'Merriam-Webster, Incorporated',
                'Springfield, MA',
                'Merriam-Webster Dictionary',
            )
        return (
            'Oxford University Press',
            'Oxford, UK',
            'Oxford English Dictionary',
        )

    @classmethod
    def _required(cls, value, message, limit):
        value = cls._text(value, limit)
        if not value:
            raise ValidationError(message)
        return value

    @staticmethod
    def _text(value, limit):
        if not isinstance(value, str):
            return ''
        return value.replace('\x00', '').strip()[:limit]

    @staticmethod
    def _field_limit(field):
        if field in {'url', 'pdf_link'}:
            return 500
        if field in {'etymology', 'usage_notes', 'examples', 'citation'}:
            return 10_000
        return 500

    @staticmethod
    def _boolean(value):
        return str(value or '').casefold() in {'true', '1', 'yes', 'on'}
