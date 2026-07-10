"""Pre-save metadata extraction and provenance assembly for uploads."""

from datetime import datetime


class UploadMetadataWorkflow:
    """Build metadata-review payloads without persisting a document."""

    USER_FIELDS = (
        'journal', 'publisher', 'doi', 'url', 'abstract', 'type', 'isbn',
        'editor', 'edition', 'volume', 'issue', 'pages', 'series',
        'container_title', 'place', 'issn', 'access_date', 'entry_term', 'notes',
    )

    def __init__(self, upload_service, logger):
        self.upload_service = upload_service
        self.logger = logger

    def run(self, source_type, form, files):
        if source_type == 'doi':
            return self._from_doi(form)
        if source_type == 'file':
            return self._from_file(form, files)
        return {'error': 'Invalid source type'}, 400

    def _from_doi(self, form):
        doi = form.get('doi')
        if not doi:
            return {'error': 'DOI is required'}, 400

        result = self.upload_service.extract_metadata_from_doi(doi)
        if not result.success:
            return {'error': result.error}, 404

        provenance = self._provenance_for_metadata(
            result.metadata,
            source='crossref',
            confidence=0.95,
        )
        return {
            'success': True,
            'metadata': result.metadata,
            'provenance': provenance,
            'needs_file': True,
            'message': (
                'Bibliographic metadata retrieved. '
                'Please upload the document file.'
            ),
        }, 200

    def _from_file(self, form, files):
        if 'document_file' not in files:
            return {'error': 'No file uploaded'}, 400

        file = files['document_file']
        upload_result = self.upload_service.save_to_temp(file)
        if not upload_result.success:
            return {'error': upload_result.error}, 400

        try:
            return self._process_saved_file(form, file, upload_result.temp_path)
        except Exception:
            self.upload_service.cleanup_temp(upload_result.temp_path)
            raise

    def _process_saved_file(self, form, file, temp_path):
        title = form.get('title', '').strip()
        enable_crossref = form.get('enable_crossref', 'true').lower() == 'true'

        crossref_metadata = {}
        crossref_provenance = {}
        extraction_method = None
        pdf_extracted_title = None
        pdf_extracted_metadata = {}
        progress_messages = []

        if enable_crossref:
            pdf_result = self.upload_service.extract_metadata_from_pdf(temp_path)
            progress_messages = getattr(pdf_result, 'progress', None) or []

            if pdf_result.success:
                crossref_metadata = pdf_result.metadata
                extraction_method = (
                    crossref_metadata.get('extraction_method') or 'pdf_analysis'
                )
                source_name = pdf_result.source
                if crossref_metadata.get('extracted_title'):
                    pdf_extracted_title = crossref_metadata['extracted_title']
                    pdf_extracted_metadata = {'title': pdf_extracted_title}
                    if crossref_metadata.get('extracted_authors'):
                        pdf_extracted_metadata['authors'] = (
                            crossref_metadata['extracted_authors']
                        )
                crossref_provenance = self._provenance_for_metadata(
                    crossref_metadata,
                    source=source_name,
                    confidence=self._extraction_confidence(extraction_method),
                    extraction_method=extraction_method,
                )
            else:
                pdf_extracted_metadata = pdf_result.metadata or {}
                pdf_extracted_title = pdf_extracted_metadata.get('title')
                if title:
                    title_result = self.upload_service.extract_metadata_from_title(
                        title
                    )
                    if title_result.success:
                        crossref_metadata = title_result.metadata
                        extraction_method = 'title_from_user'
                        crossref_provenance = self._provenance_for_metadata(
                            crossref_metadata,
                            source='crossref',
                            confidence=title_result.metadata.get(
                                'match_score', 0.85
                            ),
                            extraction_method=extraction_method,
                        )

        user_metadata, user_provenance = self._user_metadata(form, title)
        pdf_provenance = {}
        if pdf_extracted_title and not crossref_metadata:
            pdf_provenance['title'] = self._provenance_entry(
                pdf_extracted_title,
                source='file',
                confidence=0.7,
                extraction_method='pdf_embedded_metadata',
            )

        merged_metadata = self.upload_service.merge_metadata(
            {'title': pdf_extracted_title} if pdf_extracted_title else {},
            crossref_metadata,
            user_metadata,
            {'filename': file.filename},
        )
        merged_provenance = {
            **pdf_provenance,
            **crossref_provenance,
            **user_provenance,
        }
        merged_provenance['filename'] = self._provenance_entry(
            file.filename,
            source='file',
            confidence=1.0,
        )

        if not enable_crossref and not title:
            self.upload_service.cleanup_temp(temp_path)
            return {
                'success': False,
                'error': 'Title is required when CrossRef lookup is disabled.',
            }, 400

        confidence_level = (
            crossref_metadata.get('confidence_level', 'high')
            if crossref_metadata else None
        )
        match_score = (
            crossref_metadata.get('match_score', 0)
            if crossref_metadata else None
        )
        message = self._result_message(
            enable_crossref,
            crossref_metadata,
            pdf_extracted_title,
            title,
            extraction_method,
            confidence_level,
            match_score,
        )

        return {
            'success': True,
            'metadata': merged_metadata,
            'provenance': merged_provenance,
            'temp_path': temp_path,
            'needs_file': False,
            'message': message,
            'crossref_enabled': enable_crossref,
            'crossref_found': bool(crossref_metadata),
            'extraction_method': extraction_method,
            'confidence_level': confidence_level,
            'match_score': match_score,
            'progress': progress_messages,
            'pdf_extracted_title': pdf_extracted_title,
            'pdf_extracted_metadata': pdf_extracted_metadata,
        }, 200

    def build_streaming_payload(
        self,
        result,
        temp_path,
        filename,
        title='',
        enable_crossref=True,
    ):
        """Build the metadata-review payload returned by the SSE workflow."""
        crossref_metadata = {}
        crossref_provenance = {}
        pdf_extracted_title = None
        pdf_extracted_metadata = {}
        progress_messages = []
        extraction_method = None

        if hasattr(result, 'success'):
            progress_messages = getattr(result, 'progress', None) or []
            metadata = result.metadata or {}
            if result.success:
                crossref_metadata = metadata
                extraction_method = (
                    metadata.get('extraction_method') or 'pdf_analysis'
                )
                pdf_extracted_title = metadata.get('extracted_title')
                if pdf_extracted_title:
                    pdf_extracted_metadata = {'title': pdf_extracted_title}
                    if metadata.get('extracted_authors'):
                        pdf_extracted_metadata['authors'] = (
                            metadata['extracted_authors']
                        )
                crossref_provenance = self._provenance_for_metadata(
                    crossref_metadata,
                    source=result.source,
                    confidence=self._extraction_confidence(extraction_method),
                    extraction_method=extraction_method,
                )
            else:
                pdf_extracted_metadata = metadata
                pdf_extracted_title = metadata.get('title')
        elif isinstance(result, dict):
            crossref_metadata = result.get('metadata') or {}
            progress_messages = result.get('progress') or []
            extraction_method = crossref_metadata.get('extraction_method')

        merged_metadata = dict(crossref_metadata)
        merged_metadata['filename'] = filename
        provenance = dict(crossref_provenance)
        provenance['filename'] = self._provenance_entry(
            filename,
            source='file',
            confidence=1.0,
        )
        confidence_level = crossref_metadata.get('confidence_level', 'high')
        match_score = crossref_metadata.get(
            'confidence_value',
            crossref_metadata.get('match_score', 0.0),
        )
        message = self._result_message(
            enable_crossref,
            crossref_metadata,
            pdf_extracted_title,
            title,
            extraction_method,
            confidence_level,
            match_score,
        )
        return {
            'success': True,
            'metadata': merged_metadata,
            'provenance': provenance,
            'temp_path': temp_path,
            'needs_file': False,
            'message': message,
            'crossref_enabled': enable_crossref,
            'crossref_found': bool(crossref_metadata.get('title')),
            'extraction_method': extraction_method,
            'confidence_level': confidence_level,
            'match_score': match_score,
            'progress': progress_messages,
            'pdf_extracted_title': pdf_extracted_title,
            'pdf_extracted_metadata': pdf_extracted_metadata,
        }

    def _user_metadata(self, form, title):
        metadata = {}
        provenance = {}

        if title:
            metadata['title'] = title
            provenance['title'] = self._provenance_entry(
                title, source='user', confidence=1.0
            )

        publication_year = form.get('publication_year', '').strip()
        if publication_year:
            metadata['publication_year'] = publication_year
            provenance['publication_year'] = self._provenance_entry(
                publication_year, source='user', confidence=1.0
            )

        authors_string = form.get('authors', '').strip()
        if authors_string:
            authors = [author.strip() for author in authors_string.split(',')]
            metadata['authors'] = ', '.join(authors)
            provenance['authors'] = {
                **self._provenance_entry(
                    authors, source='user', confidence=1.0
                ),
                'previous_source': 'user',
            }

        for field in self.USER_FIELDS:
            value = form.get(field, '').strip()
            if value:
                metadata[field] = value
                provenance[field] = self._provenance_entry(
                    value, source='user', confidence=1.0
                )

        return metadata, provenance

    @staticmethod
    def _provenance_for_metadata(
        metadata,
        *,
        source,
        confidence,
        extraction_method=None,
    ):
        result = {}
        for key, value in metadata.items():
            if value is not None:
                result[key] = UploadMetadataWorkflow._provenance_entry(
                    value,
                    source=source,
                    confidence=confidence,
                    extraction_method=extraction_method,
                )
        return result

    @staticmethod
    def _provenance_entry(
        value,
        *,
        source,
        confidence,
        extraction_method=None,
    ):
        entry = {
            'source': source,
            'confidence': confidence,
            'timestamp': datetime.utcnow().isoformat(),
            'raw_value': value,
        }
        if extraction_method is not None:
            entry['extraction_method'] = extraction_method
        return entry

    @staticmethod
    def _extraction_confidence(extraction_method):
        if 'arxiv' in extraction_method:
            return 0.95
        if 'doi' in extraction_method:
            return 0.9
        return 0.85

    @staticmethod
    def _result_message(
        enable_crossref,
        crossref_metadata,
        pdf_title,
        user_title,
        extraction_method,
        confidence_level,
        match_score,
    ):
        if enable_crossref and crossref_metadata:
            base_messages = {
                'doi_from_pdf': 'CrossRef match found using DOI from PDF!',
                'title_from_pdf': 'CrossRef match found using title from PDF!',
                'title_from_user': (
                    'CrossRef match found using your provided title!'
                ),
            }
            base = base_messages.get(extraction_method, 'CrossRef match found!')
            if confidence_level == 'low':
                return (
                    f'{base} LOW CONFIDENCE (score: {match_score:.1f}/100). '
                    'Please verify this is the correct document before saving.'
                )
            return f'{base} Please review the auto-filled metadata.'
        if enable_crossref and pdf_title:
            return (
                f'Extracted title from PDF: "{pdf_title}". '
                'No CrossRef match found. You can use this title or enter a '
                'different one below.'
            )
        if enable_crossref and not user_title:
            return (
                'Could not extract metadata from PDF. '
                'Please fill in the required fields below.'
            )
        if enable_crossref:
            return (
                'No CrossRef match found for your title. '
                'Please enter metadata manually.'
            )
        return 'Document uploaded. Please review metadata before saving.'
