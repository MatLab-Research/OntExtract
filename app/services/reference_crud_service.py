"""Reference document read, edit, delete, and download workflows."""

import os

from app import db
from app.models.document import Document
from app.models.experiment import Experiment
from app.models.user import User
from app.services.base_service import NotFoundError, PermissionError, ValidationError
from app.utils.date_parser import parse_flexible_date


class ReferenceInUseError(ValidationError):
    """A reference cannot be deleted while linked to experiments."""

    def __init__(self, experiments):
        self.experiments = experiments
        super().__init__('Cannot delete reference: still used in experiments')


class ReferenceCrudService:
    """Manage reference documents with ownership and link protection."""

    STRING_FIELDS = {
        'authors': None,
        'editor': None,
        'edition': 50,
        'journal': 200,
        'container_title': 300,
        'volume': 20,
        'issue': 20,
        'pages': 50,
        'series': 200,
        'publisher': 200,
        'place': 100,
        'doi': 100,
        'isbn': 20,
        'issn': 20,
        'url': 500,
        'entry_term': 200,
        'abstract': None,
        'notes': None,
        'citation': None,
    }

    def __init__(self, provenance_service=None, workflow_logger=None):
        self.provenance_service = provenance_service
        self.logger = workflow_logger

    @staticmethod
    def list_references():
        return Document.query.filter_by(document_type='reference').order_by(
            Document.created_at.desc(),
            Document.id.desc(),
        ).all()

    @classmethod
    def detail_context(cls, reference_id):
        reference = cls._reference(reference_id)
        return {
            'reference': reference,
            'experiments_using': cls._experiments(reference),
        }

    @classmethod
    def edit_context(cls, reference_id, actor_id):
        reference = cls._editable_reference(reference_id, actor_id)
        return {
            'reference': reference,
            'experiments_using': cls._experiments(reference),
        }

    @classmethod
    def update(cls, reference_id, actor_id, form):
        reference = cls._editable_reference(reference_id, actor_id)
        title = cls._clean(form.get('title'))
        if not title:
            raise ValidationError('Title is required')
        subtype = cls._clean(form.get('reference_subtype'))
        if not subtype:
            raise ValidationError('Reference type is required')
        reference.title = title[:200]
        reference.reference_subtype = subtype[:30]
        for field, max_length in cls.STRING_FIELDS.items():
            value = cls._clean(form.get(field))
            if max_length is not None:
                value = value[:max_length]
            setattr(reference, field, value or None)
        reference.publication_date = cls._date(
            form.get('publication_date'),
            'Publication date',
        )
        reference.access_date = cls._date(
            form.get('access_date'),
            'Access date',
        )
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
        return reference

    def delete(self, reference_id, actor_id):
        reference = self._editable_reference(reference_id, actor_id)
        family = [reference, *reference.children.all()]
        experiments = []
        seen_experiments = set()
        for document in family:
            for experiment in self._experiments(document):
                if experiment.id not in seen_experiments:
                    seen_experiments.add(experiment.id)
                    experiments.append(experiment)
        if experiments:
            raise ReferenceInUseError(experiments)
        file_paths = [
            document.file_path for document in family if document.file_path
        ]
        document_ids = [document.id for document in family]
        reference_id_value = reference.id
        try:
            db.session.delete(reference)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
        for file_path in file_paths:
            if not os.path.exists(file_path):
                continue
            try:
                os.remove(file_path)
            except OSError as exc:
                if self.logger:
                    self.logger.warning(
                        f'Failed to remove reference file {file_path}: {exc}'
                    )
        self._delete_provenance_best_effort(document_ids)
        return reference_id_value

    def _delete_provenance_best_effort(self, document_ids):
        if not self.provenance_service:
            return
        for document_id in document_ids:
            try:
                self.provenance_service.delete_or_invalidate_document_provenance(
                    document_id
                )
            except Exception as exc:
                if not db.session.is_active:
                    db.session.rollback()
                if self.logger:
                    self.logger.warning(
                        'Failed to delete reference provenance for '
                        f'{document_id}: {exc}'
                    )

    @classmethod
    def download(cls, reference_id):
        reference = cls._reference(reference_id)
        if not reference.file_path:
            raise ValidationError('No file attached to this reference.')
        if not os.path.isfile(reference.file_path):
            raise ValidationError('Reference file is not available.')
        return {
            'path': reference.file_path,
            'filename': (
                reference.original_filename
                or os.path.basename(reference.file_path)
            ),
        }

    @staticmethod
    def _reference(reference_id):
        reference = db.session.get(Document, reference_id)
        if not reference or reference.document_type != 'reference':
            raise NotFoundError('Reference not found')
        return reference

    @classmethod
    def _editable_reference(cls, reference_id, actor_id):
        reference = cls._reference(reference_id)
        actor = db.session.get(User, actor_id)
        if not actor or not actor.can_edit_resource(reference):
            raise PermissionError('Permission denied')
        return reference

    @staticmethod
    def _experiments(reference):
        return Experiment.query.filter(
            Experiment.references.any(Document.id == reference.id)
        ).order_by(Experiment.created_at.desc()).all()

    @staticmethod
    def _date(value, label):
        value = value.strip() if isinstance(value, str) else ''
        if not value:
            return None
        parsed = parse_flexible_date(value)
        if not parsed:
            raise ValidationError(f'{label} is invalid')
        return parsed

    @staticmethod
    def _clean(value):
        return value.strip() if isinstance(value, str) else ''
