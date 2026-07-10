"""Persistence workflow for reviewed document uploads."""

import logging
import os
from datetime import datetime

from app import db
from app.models.document import Document
from app.models.temporal_experiment import DocumentTemporalMetadata
from app.services.base_service import ValidationError
from app.utils.date_parser import parse_flexible_date


logger = logging.getLogger(__name__)


class UploadPersistenceService:
    """Move, extract, normalize, persist, and provenance-track an upload."""

    SOURCE_CONFIDENCE = {
        'crossref': 0.9,
        'semanticscholar': 0.9,
        'zotero': 0.95,
        'pdf_analysis': 0.7,
        'user': 1.0,
        'manual': 1.0,
    }

    SOURCE_ALIASES = {
        'crossref_auto': 'crossref',
        'file': 'pdf_analysis',
    }

    def __init__(self, upload_service, provenance_service, workflow_logger=None):
        self.upload_service = upload_service
        self.provenance_service = provenance_service
        self.logger = workflow_logger or logger

    def persist_reviewed_upload(self, data, user, upload_dir):
        metadata, provenance, temp_path, filename = self._validate(data)
        save_result = self.upload_service.save_permanent(
            temp_path,
            upload_dir,
            filename,
        )
        if not save_result.success:
            raise ValidationError(save_result.error)

        final_path = save_result.file_path
        committed = False
        try:
            content, error, extraction_method = (
                self.upload_service.extract_text_content(final_path, filename)
            )
            if error:
                raise ValidationError(error)

            document = self._build_document(
                metadata,
                provenance,
                filename,
                final_path,
                content,
                user.id,
            )
            db.session.add(document)
            db.session.flush()
            self._add_temporal_metadata(document, metadata)
            db.session.commit()
            committed = True
        except Exception:
            db.session.rollback()
            if not committed:
                self._remove_file(final_path)
            raise

        self._track_provenance_best_effort(
            document,
            user,
            provenance,
            extraction_method,
        )
        return {
            'success': True,
            'message': 'Document saved successfully',
            'document_id': document.id,
            'document_uuid': str(document.uuid),
        }

    @staticmethod
    def _validate(data):
        if not isinstance(data, dict):
            raise ValidationError('No data provided')
        metadata = data.get('metadata') or {}
        provenance = data.get('provenance') or {}
        temp_path = data.get('temp_path')
        filename = data.get('filename')
        if not temp_path:
            raise ValidationError('No document file to save')
        if not metadata.get('title'):
            raise ValidationError('Title is required')
        return metadata, provenance, temp_path, filename

    @classmethod
    def _build_document(
        cls,
        metadata,
        provenance,
        filename,
        final_path,
        content,
        user_id,
    ):
        authors = metadata.get('authors')
        if isinstance(authors, list):
            authors = ', '.join(authors) if authors else None
        return Document(
            title=metadata.get('title', filename),
            content_type='file',
            file_type='pdf',
            original_filename=filename,
            file_path=final_path,
            file_size=os.path.getsize(final_path),
            content=content,
            authors=authors,
            publication_date=parse_flexible_date(metadata.get('publication_year')),
            journal=cls._nullable(metadata.get('journal')),
            publisher=cls._nullable(metadata.get('publisher')),
            doi=cls._nullable(metadata.get('doi')),
            isbn=cls._nullable(metadata.get('isbn')),
            document_subtype=cls._nullable(metadata.get('type')),
            abstract=cls._nullable(metadata.get('abstract')),
            url=cls._nullable(metadata.get('url')),
            citation=cls._nullable(metadata.get('citation')),
            editor=cls._nullable(metadata.get('editor')),
            edition=cls._nullable(metadata.get('edition')),
            volume=cls._nullable(metadata.get('volume')),
            issue=cls._nullable(metadata.get('issue')),
            pages=cls._nullable(metadata.get('pages')),
            issn=cls._nullable(metadata.get('issn')),
            container_title=cls._nullable(metadata.get('container_title')),
            place=cls._nullable(metadata.get('place')),
            series=cls._nullable(metadata.get('series')),
            entry_term=cls._nullable(metadata.get('entry_term')),
            access_date=parse_flexible_date(metadata.get('access_date')),
            notes=cls._nullable(metadata.get('notes')),
            source_metadata={'extraction_source': 'enhanced_upload'},
            metadata_provenance=provenance,
            status='uploaded',
            user_id=user_id,
        )

    @staticmethod
    def _nullable(value):
        return None if value in ('', None) else value

    @staticmethod
    def _add_temporal_metadata(document, metadata):
        publication_year = metadata.get('publication_year')
        if not publication_year:
            return
        parsed_date = parse_flexible_date(publication_year)
        db.session.add(DocumentTemporalMetadata(
            document_id=document.id,
            publication_year=parsed_date.year if parsed_date else publication_year,
            discipline=metadata.get('discipline'),
            key_definition=metadata.get('abstract'),
            created_at=datetime.utcnow(),
        ))

    def _track_provenance_best_effort(
        self,
        document,
        user,
        provenance,
        extraction_method,
    ):
        try:
            service = self.provenance_service
            service.track_document_upload(document, user)
            service.track_text_extraction(
                document,
                user,
                source_format='pdf',
                extraction_method=extraction_method or 'unknown',
            )
            self._track_pdf_identifiers(service, document, user, provenance)
            self._track_metadata_sources(service, document, user, provenance)
            service.track_document_save(document, user)
        except Exception as exc:
            db.session.rollback()
            self.logger.error(
                f'Failed to track document provenance: {exc}',
                exc_info=True,
            )

    @staticmethod
    def _track_pdf_identifiers(service, document, user, provenance):
        extracted_doi = provenance.get('extracted_doi')
        if not isinstance(extracted_doi, dict):
            return
        identifiers = {'doi': extracted_doi.get('raw_value', '')}
        extracted_title = provenance.get('extracted_title')
        if isinstance(extracted_title, dict):
            identifiers['title'] = extracted_title.get('raw_value', '')
        service.track_metadata_extraction_pdf(
            document,
            user,
            extracted_identifiers=identifiers,
        )

    def _track_metadata_sources(self, service, document, user, provenance):
        source_fields = {
            source: {}
            for source in self.SOURCE_CONFIDENCE
        }
        for field_name, provenance_data in provenance.items():
            if not isinstance(provenance_data, dict):
                continue
            source = provenance_data.get('source', '')
            source = self.SOURCE_ALIASES.get(source, source)
            if source in source_fields:
                source_fields[source][field_name] = provenance_data.get('raw_value')

        match_score = provenance.get('match_score', {})
        match_confidence = (
            match_score.get('raw_value', 0.9)
            if isinstance(match_score, dict) else 0.9
        )
        for source, fields in source_fields.items():
            if not fields:
                continue
            confidence = (
                match_confidence
                if source in ('crossref', 'semanticscholar')
                else self.SOURCE_CONFIDENCE[source]
            )
            service.track_metadata_extraction(
                document,
                user,
                source,
                fields,
                confidence,
            )

    def _remove_file(self, file_path):
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
        except OSError as exc:
            self.logger.error(
                f'Failed to remove orphaned upload {file_path}: {exc}'
            )
