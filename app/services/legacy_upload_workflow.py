"""Compatibility workflow for direct multipart document uploads."""

import logging
import os

from app import db
from app.models.document import Document
from app.models.experiment import (
    Experiment,
    experiment_documents,
    experiment_references,
)
from app.models.experiment_document import ExperimentDocument
from app.models.user import User
from app.services.base_service import NotFoundError, PermissionError, ValidationError
from app.services.reference_metadata_enricher import ReferenceMetadataEnricher
from app.services.text_processing import TextProcessingService
from app.utils.date_parser import parse_flexible_date
from app.utils.file_handler import FileHandler


logger = logging.getLogger(__name__)


class LegacyUploadWorkflow:
    """Persist and process the legacy direct-upload form."""

    BIBLIOGRAPHIC_FIELDS = (
        'journal', 'doi', 'isbn', 'url', 'abstract', 'citation', 'editor',
        'edition', 'volume', 'issue', 'pages', 'issn', 'container_title',
        'place', 'series', 'entry_term', 'notes', 'publisher',
    )

    def __init__(
        self,
        file_handler=None,
        processing_service=None,
        provenance_service=None,
        enricher_factory=ReferenceMetadataEnricher,
        workflow_logger=None,
        language_detector=None,
    ):
        self.file_handler = file_handler or FileHandler()
        self.processing_service = processing_service or TextProcessingService()
        self.provenance_service = (
            provenance_service or self._default_provenance_service()
        )
        self.enricher_factory = enricher_factory
        self.logger = workflow_logger or logger
        self.language_detector = language_detector or self._detect_language

    def upload(
        self,
        file,
        form,
        user,
        upload_folder,
        *,
        force_document_type=None,
        prefill_metadata=None,
        use_zotero=None,
        validate_file_type=False,
    ):
        if not file or not file.filename:
            raise ValidationError('No file selected')
        if validate_file_type and not self.file_handler.allowed_file(file.filename):
            raise ValidationError('File type is not allowed')

        experiment = self._authorized_experiment(
            form.get('experiment_id'),
            user.id,
        )

        saved_path = None
        committed = False
        try:
            saved_path, file_size = self.file_handler.save_file(
                file,
                upload_folder=upload_folder,
            )
            if not saved_path:
                raise ValidationError('Failed to save file')

            original_filename = file.filename or ''
            content = self.file_handler.extract_text_from_file(
                saved_path,
                original_filename,
            )
            document = self._build_document(
                form,
                user.id,
                original_filename,
                saved_path,
                file_size,
                content,
                force_document_type,
            )
            self._enrich_with_zotero(
                document,
                form,
                saved_path,
                prefill_metadata=prefill_metadata,
                use_zotero=use_zotero,
            )
            db.session.add(document)
            db.session.flush()
            self._link_experiment_atomic(document, experiment, form)
            db.session.commit()
            committed = True
        except Exception:
            db.session.rollback()
            if not committed:
                self._remove_file(saved_path)
            raise

        self._track_provenance(document, user, experiment)
        processing_warning = self._process_document(document)
        return {
            'document': document,
            'processing_warning': processing_warning,
            'linked_experiment': experiment,
        }

    def _build_document(
        self,
        form,
        user_id,
        filename,
        saved_path,
        file_size,
        content,
        force_document_type,
    ):
        prov_type = form.get('prov_type', 'prov:Entity')
        if force_document_type == 'reference':
            document_type = 'reference'
            reference_subtype = (
                self._form_value(form, 'reference_subtype') or 'other'
            )
        else:
            document_type, reference_subtype = self._document_classification(
                prov_type
            )
        detected_language = None
        language_confidence = 0.0
        if form.get('auto_detect_language') == 'on' and content:
            detected_language, language_confidence = self.language_detector(content)

        values = {
            field: self._form_value(form, field)
            for field in self.BIBLIOGRAPHIC_FIELDS
        }
        authors = self._form_value(form, 'authors')
        publication_date = parse_flexible_date(
            self._form_value(form, 'publication_date')
        )
        access_date = parse_flexible_date(
            self._form_value(form, 'access_date')
        )
        source_metadata = {'prov_type': prov_type}
        if force_document_type == 'reference':
            source_metadata.update({
                key: value
                for key, value in {
                    'authors': (
                        [item.strip() for item in authors.split(',') if item.strip()]
                        if authors else None
                    ),
                    'publication_date': self._form_value(
                        form, 'publication_date'
                    ),
                    **values,
                }.items()
                if value
            })
        return Document(
            title=self._form_value(form, 'title') or self._secure_name(filename),
            content_type='file',
            document_type=document_type,
            reference_subtype=reference_subtype,
            file_type=self.file_handler.get_file_extension(filename),
            original_filename=filename,
            file_path=saved_path,
            file_size=file_size,
            content=content,
            detected_language=detected_language,
            language_confidence=language_confidence,
            authors=authors,
            publication_date=publication_date,
            access_date=access_date,
            source_metadata=source_metadata,
            user_id=user_id,
            status='uploaded',
            **values,
        )

    @staticmethod
    def _document_classification(prov_type):
        if any(
            marker in prov_type
            for marker in ('Reference', 'Academic', 'Standard')
        ):
            if 'Academic' in prov_type:
                subtype = 'academic'
            elif 'Standard' in prov_type:
                subtype = 'standard'
            else:
                subtype = 'other'
            return 'reference', subtype
        return 'document', None

    def _enrich_with_zotero(
        self,
        document,
        form,
        saved_path,
        *,
        prefill_metadata=None,
        use_zotero=None,
    ):
        enabled = (
            form.get('check_zotero') == 'on'
            if prefill_metadata is None else bool(prefill_metadata)
        )
        if not enabled:
            return
        if self.file_handler.get_file_extension(document.original_filename).lower() != 'pdf':
            return
        try:
            delta = self.enricher_factory(
                use_zotero=True if use_zotero is None else bool(use_zotero)
            ).extract_with_zotero(
                saved_path,
                title=self._form_value(form, 'title'),
                existing=document.source_metadata or {},
                allow_overwrite=False,
            )
            if not delta:
                return
            merged = dict(document.source_metadata or {})
            for key, value in delta.items():
                if not merged.get(key):
                    merged[key] = value
            document.source_metadata = merged
            if delta.get('zotero_key'):
                self.logger.info(
                    'Enriched document with Zotero metadata (key: %s, score: %.2f)',
                    delta['zotero_key'],
                    delta.get('zotero_match_score', 0),
                )
        except Exception as exc:
            self.logger.warning(f'Zotero metadata enrichment failed: {exc}')

    def _track_provenance(self, document, user, experiment):
        try:
            if (
                document.document_type == 'reference'
                and hasattr(self.provenance_service, 'track_reference_creation')
            ):
                self.provenance_service.track_reference_creation(
                    document=document,
                    user=user,
                    source='manual',
                    experiment=experiment,
                    source_metadata=document.source_metadata,
                )
            else:
                self.provenance_service.track_document_upload(
                    document,
                    user,
                    experiment,
                )
        except Exception as exc:
            if not db.session.is_active:
                db.session.rollback()
            self.logger.warning(f'Failed to track document upload provenance: {exc}')

    def _process_document(self, document):
        try:
            self.processing_service.process_document(document)
            return None
        except Exception as exc:
            return str(exc)

    @staticmethod
    def _authorized_experiment(experiment_id, user_id):
        if not experiment_id:
            return None
        try:
            normalized_id = int(experiment_id)
        except (TypeError, ValueError) as exc:
            raise NotFoundError('Experiment not found') from exc
        experiment = db.session.get(Experiment, normalized_id)
        if not experiment:
            raise NotFoundError('Experiment not found')
        actor = db.session.get(User, user_id)
        if not actor or not actor.can_edit_resource(experiment):
            raise PermissionError('Permission denied')
        return experiment

    @staticmethod
    def _link_experiment_atomic(document, experiment, form):
        if not experiment:
            return
        if document.document_type == 'reference':
            db.session.execute(experiment_references.insert().values(
                experiment_id=experiment.id,
                reference_id=document.id,
                include_in_analysis=(
                    form.get('include_in_analysis') == 'true'
                ),
            ))
        else:
            db.session.execute(experiment_documents.insert().values(
                experiment_id=experiment.id,
                document_id=document.id,
            ))
            db.session.add(ExperimentDocument(
                experiment_id=experiment.id,
                document_id=document.id,
                processing_status='pending',
            ))

    @staticmethod
    def _form_value(form, key):
        value = form.get(key, '')
        return value.strip() if isinstance(value, str) and value.strip() else None

    @staticmethod
    def _secure_name(filename):
        from werkzeug.utils import secure_filename

        return secure_filename(filename)

    @staticmethod
    def _detect_language(content):
        try:
            from langdetect import detect

            return detect(content), 0.9
        except Exception:
            return 'en', 0.5

    def _remove_file(self, file_path):
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
        except OSError as exc:
            self.logger.error(
                f'Failed to remove orphaned legacy upload {file_path}: {exc}'
            )

    @staticmethod
    def _default_provenance_service():
        from app.services.provenance_service import provenance_service

        return provenance_service
