"""Compatibility workflow for direct multipart document uploads."""

import logging
import os

from app import db
from app.models.document import Document
from app.models.experiment import Experiment
from app.services.base_service import ValidationError
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

    def upload(self, file, form, user, upload_folder):
        if not file or not file.filename:
            raise ValidationError('No file selected')

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
            )
            self._enrich_with_zotero(document, form, saved_path)
            db.session.add(document)
            db.session.commit()
            committed = True
        except Exception:
            db.session.rollback()
            if not committed:
                self._remove_file(saved_path)
            raise

        experiment = self._authorized_experiment(form.get('experiment_id'), user.id)
        self._track_provenance(document, user, experiment)
        processing_warning = self._process_document(document)
        linked_experiment = self._link_experiment(document, experiment, form)
        return {
            'document': document,
            'processing_warning': processing_warning,
            'linked_experiment': linked_experiment,
        }

    def _build_document(
        self,
        form,
        user_id,
        filename,
        saved_path,
        file_size,
        content,
    ):
        prov_type = form.get('prov_type', 'prov:Entity')
        document_type, reference_subtype = self._document_classification(prov_type)
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
            source_metadata={'prov_type': prov_type},
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

    def _enrich_with_zotero(self, document, form, saved_path):
        if form.get('check_zotero') != 'on':
            return
        if self.file_handler.get_file_extension(document.original_filename).lower() != 'pdf':
            return
        try:
            delta = self.enricher_factory(use_zotero=True).extract_with_zotero(
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
            self.provenance_service.track_document_upload(
                document,
                user,
                experiment,
            )
        except Exception as exc:
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
        except (TypeError, ValueError):
            return None
        experiment = db.session.get(Experiment, normalized_id)
        if not experiment or experiment.user_id != user_id:
            return None
        return experiment

    @staticmethod
    def _link_experiment(document, experiment, form):
        if not experiment:
            return None
        if document.document_type == 'reference':
            experiment.add_reference(
                document,
                include_in_analysis=form.get('include_in_analysis') == 'true',
            )
        else:
            experiment.add_document(document)
            db.session.commit()
        return experiment

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
