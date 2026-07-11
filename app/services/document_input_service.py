"""Simple pasted-text and compatibility file-input persistence workflows."""

import os
import uuid

from werkzeug.utils import secure_filename

from app import db
from app.models.document import Document
from app.services.base_service import ValidationError
from app.utils.file_handler import FileHandler


class DocumentInputService:
    """Create basic document records from pasted text or direct file input."""

    def __init__(self, file_handler=None, language_detector=None, uuid_factory=None):
        self.file_handler = file_handler or FileHandler()
        self.language_detector = language_detector or self._detect_language
        self.uuid_factory = uuid_factory or uuid.uuid4

    def create_text(self, data, user_id):
        if data is None or not hasattr(data, 'get'):
            raise ValidationError('Content is required')
        content = data.get('content', '')
        content = content.strip() if isinstance(content, str) else ''
        if not content:
            raise ValidationError('Content is required')
        title = data.get('title', '')
        title = title.strip() if isinstance(title, str) else ''
        if not title:
            title = self._title_from_content(content)
        language, confidence = self.language_detector(content)
        document = Document(
            title=title,
            content_type='text',
            content=content,
            detected_language=language,
            language_confidence=confidence,
            status='uploaded',
            user_id=user_id,
        )
        try:
            db.session.add(document)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
        return document

    def create_file(
        self,
        file,
        title,
        user_id,
        upload_folder,
        allowed_extensions,
    ):
        if not file or not file.filename:
            raise ValidationError('No file selected')
        original_filename = file.filename
        extension = self.file_handler.get_file_extension(original_filename).lower()
        allowed = {value.lower() for value in allowed_extensions}
        if extension not in allowed:
            raise ValidationError(
                'File type not allowed. Allowed types: '
                + ', '.join(sorted(allowed))
            )

        filename = secure_filename(original_filename)
        if not filename:
            raise ValidationError('No file selected')
        unique_filename = f'{self.uuid_factory().hex}_{filename}'
        os.makedirs(upload_folder, exist_ok=True)
        file_path = os.path.join(upload_folder, unique_filename)
        committed = False
        try:
            file.save(file_path)
            file_size = os.path.getsize(file_path)
            content = self.file_handler.extract_text_from_file(
                file_path,
                original_filename,
            )
            if not content:
                raise ValidationError('Could not extract text from file')
            language, confidence = self.language_detector(content)
            clean_title = title.strip() if isinstance(title, str) else ''
            document = Document(
                title=clean_title or os.path.splitext(original_filename)[0],
                content_type='file',
                file_type=extension,
                original_filename=original_filename,
                file_path=file_path,
                file_size=file_size,
                content=content,
                detected_language=language,
                language_confidence=confidence,
                status='uploaded',
                user_id=user_id,
            )
            db.session.add(document)
            db.session.commit()
            committed = True
            return document
        except Exception:
            db.session.rollback()
            if not committed:
                self._remove_file(file_path)
            raise

    @staticmethod
    def _title_from_content(content):
        first_line = content.split('\n', 1)[0].strip()
        if not first_line:
            return 'Untitled Text'
        return first_line[:50] + ('...' if len(first_line) > 50 else '')

    @staticmethod
    def _detect_language(content):
        try:
            from langdetect import detect

            return detect(content), 0.9
        except Exception:
            return 'en', 0.5

    @staticmethod
    def _remove_file(file_path):
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
        except OSError:
            pass
