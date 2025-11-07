"""
Shared Upload Service

Provides reusable upload functionality for both generic uploads and
experiment-specific uploads. Handles file processing, metadata extraction,
and document creation.
"""

from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
import os
import tempfile
from pathlib import Path
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage

from app.utils.file_handler import FileHandler
from app.services.crossref_metadata import CrossRefMetadataExtractor
from app.utils.pdf_analyzer import pdf_analyzer


@dataclass
class UploadResult:
    """Result of document upload operation"""
    success: bool
    file_path: Optional[str] = None
    filename: Optional[str] = None
    temp_path: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@dataclass
class MetadataExtractionResult:
    """Result of metadata extraction"""
    success: bool
    metadata: Dict[str, Any]
    source: str  # 'crossref', 'file_analysis', 'user_provided'
    error: Optional[str] = None


class UploadService:
    """
    Shared service for document uploads across the application.

    Provides:
    - File handling and validation
    - Temporary file management
    - CrossRef metadata extraction
    - Bibliographic metadata normalization
    """

    ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt', 'md'}
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

    def __init__(self):
        self.file_handler = FileHandler()
        self.crossref = CrossRefMetadataExtractor()

    def validate_file(self, file: FileStorage) -> Tuple[bool, Optional[str]]:
        """
        Validate uploaded file.

        Returns:
            (is_valid, error_message)
        """
        if not file or file.filename == '':
            return False, "No file selected"

        # Check extension
        ext = Path(file.filename).suffix.lower().lstrip('.')
        if ext not in self.ALLOWED_EXTENSIONS:
            return False, f"File type '.{ext}' not allowed. Allowed types: {', '.join(self.ALLOWED_EXTENSIONS)}"

        # Note: We can't check file size from FileStorage directly
        # It will be checked during save if needed

        return True, None

    def save_to_temp(self, file: FileStorage) -> UploadResult:
        """
        Save uploaded file to temporary location for processing.

        Args:
            file: Uploaded file from request

        Returns:
            UploadResult with temp_path and filename
        """
        # Validate
        is_valid, error = self.validate_file(file)
        if not is_valid:
            return UploadResult(success=False, error=error)

        try:
            # Create temp directory
            temp_dir = tempfile.mkdtemp()

            # Save with secure filename
            secure_name = secure_filename(file.filename)
            temp_path = os.path.join(temp_dir, secure_name)

            file.save(temp_path)

            return UploadResult(
                success=True,
                temp_path=temp_path,
                filename=file.filename
            )

        except Exception as e:
            return UploadResult(
                success=False,
                error=f"Error saving file: {str(e)}"
            )

    def save_permanent(self, temp_path: str, upload_folder: str,
                      filename: Optional[str] = None) -> UploadResult:
        """
        Move file from temporary location to permanent storage.

        Args:
            temp_path: Path to temporary file
            upload_folder: Destination folder
            filename: Optional custom filename (uses original if not provided)

        Returns:
            UploadResult with final file_path
        """
        try:
            if not os.path.exists(temp_path):
                return UploadResult(
                    success=False,
                    error="Temporary file not found"
                )

            # Create upload folder if it doesn't exist
            os.makedirs(upload_folder, exist_ok=True)

            # Determine filename
            if not filename:
                filename = os.path.basename(temp_path)

            secure_name = secure_filename(filename)
            final_path = os.path.join(upload_folder, secure_name)

            # Handle duplicate filenames
            if os.path.exists(final_path):
                base, ext = os.path.splitext(secure_name)
                counter = 1
                while os.path.exists(final_path):
                    secure_name = f"{base}_{counter}{ext}"
                    final_path = os.path.join(upload_folder, secure_name)
                    counter += 1

            # Move file
            import shutil
            shutil.move(temp_path, final_path)

            return UploadResult(
                success=True,
                file_path=final_path,
                filename=secure_name
            )

        except Exception as e:
            return UploadResult(
                success=False,
                error=f"Error saving file permanently: {str(e)}"
            )

    def extract_metadata_from_doi(self, doi: str) -> MetadataExtractionResult:
        """
        Extract bibliographic metadata from DOI using CrossRef.

        Args:
            doi: Digital Object Identifier

        Returns:
            MetadataExtractionResult with bibliographic data
        """
        try:
            metadata = self.crossref.extract_from_doi(doi)

            if not metadata:
                return MetadataExtractionResult(
                    success=False,
                    metadata={},
                    source='crossref',
                    error=f"DOI not found in CrossRef: {doi}"
                )

            return MetadataExtractionResult(
                success=True,
                metadata=self._normalize_metadata(metadata),
                source='crossref'
            )

        except Exception as e:
            return MetadataExtractionResult(
                success=False,
                metadata={},
                source='crossref',
                error=f"Error extracting DOI metadata: {str(e)}"
            )

    def extract_metadata_from_title(self, title: str) -> MetadataExtractionResult:
        """
        Search CrossRef by title and extract metadata from best match.

        Args:
            title: Document title

        Returns:
            MetadataExtractionResult with bibliographic data
        """
        try:
            metadata = self.crossref.extract_from_title(title)

            if not metadata:
                return MetadataExtractionResult(
                    success=False,
                    metadata={},
                    source='crossref',
                    error=f"Title not found in CrossRef: {title}"
                )

            return MetadataExtractionResult(
                success=True,
                metadata=self._normalize_metadata(metadata),
                source='crossref'
            )

        except Exception as e:
            return MetadataExtractionResult(
                success=False,
                metadata={},
                source='crossref',
                error=f"Error searching CrossRef: {str(e)}"
            )

    def extract_metadata_from_pdf(self, pdf_path: str) -> MetadataExtractionResult:
        """
        Extract metadata from PDF file automatically (Zotero-style).

        Tries multiple methods:
        1. Extract DOI from PDF and query CrossRef
        2. Extract title from PDF and query CrossRef
        3. Use embedded PDF metadata

        Args:
            pdf_path: Path to PDF file

        Returns:
            MetadataExtractionResult with extracted metadata
        """
        try:
            # Analyze PDF to extract DOI/title
            pdf_info = pdf_analyzer.analyze(pdf_path)

            # Try DOI first (most reliable)
            if pdf_info.get('doi'):
                result = self.extract_metadata_from_doi(pdf_info['doi'])
                if result.success:
                    # Add PDF analysis info to metadata
                    result.metadata['extracted_doi'] = pdf_info['doi']
                    result.metadata['extraction_method'] = 'doi_from_pdf'
                    return result

            # Try title search
            if pdf_info.get('title'):
                result = self.extract_metadata_from_title(pdf_info['title'])
                if result.success:
                    # Add PDF analysis info
                    result.metadata['extracted_title'] = pdf_info['title']
                    result.metadata['extraction_method'] = 'title_from_pdf'
                    return result

            # Fallback: return what we found from PDF
            return MetadataExtractionResult(
                success=False,
                metadata=pdf_info.get('metadata', {}),
                source='pdf_analysis',
                error="Could not find metadata in CrossRef using extracted DOI/title"
            )

        except Exception as e:
            return MetadataExtractionResult(
                success=False,
                metadata={},
                source='pdf_analysis',
                error=f"Error analyzing PDF: {str(e)}"
            )

    def extract_text_content(self, file_path: str, filename: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Extract text content from file.

        Args:
            file_path: Path to file
            filename: Original filename

        Returns:
            (content, error_message, extraction_method) where extraction_method is the tool used (e.g., 'pypdf', 'python-docx')
        """
        try:
            result = self.file_handler.extract_text_with_method(file_path, filename)
            if not result:
                return None, "Could not extract text from file", None
            content, extraction_method = result
            return content, None, extraction_method
        except Exception as e:
            return None, f"Error extracting text: {str(e)}", None

    def _normalize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize metadata from different sources to consistent format.

        Args:
            metadata: Raw metadata from CrossRef or other source

        Returns:
            Normalized metadata dictionary
        """
        return {
            'title': metadata.get('title'),
            'authors': metadata.get('authors', []),
            'publication_year': metadata.get('publication_year'),
            'journal': metadata.get('journal'),
            'publisher': metadata.get('publisher'),
            'doi': metadata.get('doi'),
            'url': metadata.get('url'),
            'abstract': metadata.get('abstract'),
            'type': metadata.get('type'),  # journal-article, book, etc.
            'raw_date': metadata.get('raw_date'),
            'match_score': metadata.get('match_score')  # For title searches
        }

    def merge_metadata(self, *metadata_dicts: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge multiple metadata dictionaries, preferring non-None values.

        Args:
            *metadata_dicts: Variable number of metadata dictionaries

        Returns:
            Merged metadata dictionary
        """
        result = {}

        for metadata in metadata_dicts:
            if not metadata:
                continue

            for key, value in metadata.items():
                # Only update if current value is None or doesn't exist
                if value is not None and (key not in result or result[key] is None):
                    result[key] = value

        return result

    def cleanup_temp(self, temp_path: str) -> None:
        """
        Clean up temporary file and directory.

        Args:
            temp_path: Path to temporary file
        """
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)

                # Try to remove temp directory if empty
                temp_dir = os.path.dirname(temp_path)
                try:
                    os.rmdir(temp_dir)
                except OSError:
                    pass  # Directory not empty, that's fine

        except Exception:
            pass  # Cleanup is best-effort


# Convenience instance
upload_service = UploadService()
