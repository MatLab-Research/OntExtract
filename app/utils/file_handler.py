import os
from typing import Optional, Set
from flask import current_app
import pypdf
from docx import Document as DocxDocument
import io

class FileHandler:
    """Utility class for handling file operations and text extraction"""
    
    def __init__(self):
        self.allowed_extensions = {'txt', 'pdf', 'docx', 'html', 'md'}

    def save_file(self, file_storage, upload_folder: Optional[str] = None):
        """Save an uploaded file to the uploads folder.

        Returns (saved_path, file_size)
        """
        if upload_folder is None:
            cfg_folder = current_app.config.get('UPLOAD_FOLDER')
            upload_folder = cfg_folder if isinstance(cfg_folder, str) and cfg_folder else 'uploads'
        os.makedirs(upload_folder, exist_ok=True)

        filename = getattr(file_storage, 'filename', '') or ''
        cleaned = self.clean_filename(filename)
        if not cleaned:
            cleaned = 'uploaded-file'
        dest_path = os.path.join(upload_folder, cleaned)

        # If file exists, add a numeric suffix
        base, ext = os.path.splitext(dest_path)
        counter = 1
        while os.path.exists(dest_path):
            dest_path = f"{base}-{counter}{ext}"
            counter += 1

        file_storage.save(dest_path)
        size = os.path.getsize(dest_path)
        return dest_path, size
    
    def allowed_file(self, filename: str) -> bool:
        """Check if file has an allowed extension"""
        if not filename:
            return False
        
        extension = self.get_file_extension(filename)
        return extension.lower() in current_app.config.get('ALLOWED_EXTENSIONS', self.allowed_extensions)
    
    def get_file_extension(self, filename: str) -> str:
        """Get file extension from filename"""
        if not filename:
            return ''
        return os.path.splitext(filename)[1].lower().lstrip('.')
    
    def detect_file_type(self, file_path: str) -> str:
        """Detect file type based on extension"""
        # Extension-based detection
        extension = self.get_file_extension(file_path)
        mime_types = {
            'txt': 'text/plain',
            'pdf': 'application/pdf',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'html': 'text/html',
            'md': 'text/markdown'
        }
        return mime_types.get(extension, 'application/octet-stream')
    
    def extract_text_from_file(self, file_path: str, original_filename: str) -> Optional[str]:
        """Extract text content from various file types

        Returns:
            str: Extracted text content, or None if extraction failed

        Note: Use extract_text_with_method() to also get the extraction tool used
        """
        result = self.extract_text_with_method(file_path, original_filename)
        return result[0] if result else None

    def _clean_extracted_text(self, text: str) -> str:
        """Clean extracted text to remove null bytes and other problematic characters.

        PostgreSQL doesn't allow null bytes in text fields, so they must be removed.
        """
        if not text:
            return text

        # Remove null bytes (0x00) which cause PostgreSQL errors
        text = text.replace('\x00', '')

        # Remove other control characters except newlines, tabs, and carriage returns
        # Keep: \n (10), \r (13), \t (9)
        cleaned = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')

        return cleaned

    def extract_text_with_method(self, file_path: str, original_filename: str) -> Optional[tuple[str, str]]:
        """Extract text content and return the extraction method used

        Returns:
            tuple: (text_content, extraction_method) or None if extraction failed

        Example:
            ("Hello world", "pypdf") or ("Document text", "python-docx")
        """
        try:
            extension = self.get_file_extension(original_filename)

            if extension == 'txt':
                text = self._extract_from_text(file_path)
                text = self._clean_extracted_text(text) if text else None
                return (text, 'python-builtin') if text else None
            elif extension == 'pdf':
                text = self._extract_from_pdf(file_path)
                text = self._clean_extracted_text(text) if text else None
                return (text, 'pypdf') if text else None
            elif extension == 'docx':
                text = self._extract_from_docx(file_path)
                text = self._clean_extracted_text(text) if text else None
                return (text, 'python-docx') if text else None
            elif extension in ['html', 'htm']:
                text = self._extract_from_html(file_path)
                text = self._clean_extracted_text(text) if text else None
                return (text, 'beautifulsoup4') if text else None
            elif extension == 'md':
                text = self._extract_from_markdown(file_path)
                text = self._clean_extracted_text(text) if text else None
                return (text, 'python-builtin') if text else None
            else:
                # Try to read as plain text
                text = self._extract_from_text(file_path)
                text = self._clean_extracted_text(text) if text else None
                return (text, 'python-builtin') if text else None

        except Exception as e:
            current_app.logger.error(f"Error extracting text from {file_path}: {str(e)}")
            return None
    
    def _extract_from_text(self, file_path: str) -> str:
        """Extract text from plain text file"""
        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
        
        # If all encodings fail, read as binary and decode errors
        with open(file_path, 'rb') as f:
            return f.read().decode('utf-8', errors='replace')
    
    def _extract_from_pdf(self, file_path: str) -> Optional[str]:
        """Extract text from PDF file"""
        text_content = []
        
        try:
            with open(file_path, 'rb') as f:
                pdf_reader = pypdf.PdfReader(f)
                
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    text = page.extract_text()
                    if text.strip():
                        text_content.append(text)
            
            return '\n\n'.join(text_content)
            
        except Exception as e:
            current_app.logger.error(f"Error reading PDF {file_path}: {str(e)}")
            return None
    
    def _extract_from_docx(self, file_path: str) -> Optional[str]:
        """Extract text from DOCX file"""
        try:
            doc = DocxDocument(file_path)
            paragraphs = []
            
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    paragraphs.append(paragraph.text)
            
            return '\n\n'.join(paragraphs)
            
        except Exception as e:
            current_app.logger.error(f"Error reading DOCX {file_path}: {str(e)}")
            return None
    
    def _extract_from_html(self, file_path: str) -> Optional[str]:
        """Extract text from HTML file"""
        try:
            from bs4 import BeautifulSoup
            
            with open(file_path, 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f.read(), 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text and clean up whitespace
            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            return text
            
        except Exception as e:
            current_app.logger.error(f"Error reading HTML {file_path}: {str(e)}")
            return None
    
    def _extract_from_markdown(self, file_path: str) -> Optional[str]:
        """Extract text from Markdown file"""
        try:
            # For now, just read as plain text
            # Could be enhanced to parse markdown and extract clean text
            return self._extract_from_text(file_path)
            
        except Exception as e:
            current_app.logger.error(f"Error reading Markdown {file_path}: {str(e)}")
            return None
    
    def validate_file_size(self, file_path: str, max_size_mb: int = 16) -> bool:
        """Validate file size doesn't exceed limit"""
        try:
            file_size = os.path.getsize(file_path)
            max_size_bytes = max_size_mb * 1024 * 1024
            return file_size <= max_size_bytes
        except Exception:
            return False
    
    def clean_filename(self, filename: str) -> str:
        """Clean filename for safe storage"""
        # Remove path components
        filename = os.path.basename(filename)
        
        # Replace problematic characters
        import re
        filename = re.sub(r'[^\w\s.-]', '', filename)
        filename = re.sub(r'[-\s]+', '-', filename)
        
        return filename.strip()
    
    def get_file_info(self, file_path: str) -> dict:
        """Get comprehensive file information"""
        try:
            stat = os.stat(file_path)
            
            return {
                'size': stat.st_size,
                'created': stat.st_ctime,
                'modified': stat.st_mtime,
                'mime_type': self.detect_file_type(file_path),
                'extension': self.get_file_extension(file_path)
            }
            
        except Exception as e:
            current_app.logger.error(f"Error getting file info for {file_path}: {str(e)}")
            return {}
