"""
Document Processing Module

Handles document and file processing operations.
"""

import logging
from typing import List
from app import db

logger = logging.getLogger(__name__)


class DocumentProcessing:
    """Handles document and file processing"""

    def __init__(self, file_processor=None):
        self.file_processor = file_processor
        self.enhanced_features_enabled = file_processor is not None

    def process_file_content(self, file_path: str, file_type: str) -> str:
        """Process file and extract text content"""
        if not self.enhanced_features_enabled:
            logger.warning("Enhanced features not available, falling back to basic processing")
            return self._basic_file_processing(file_path, file_type)

        try:
            return self.file_processor.process_file(file_path, file_type)
        except Exception as e:
            logger.error(f"Error processing file with shared services: {e}")
            return self._basic_file_processing(file_path, file_type)

    def process_document(self, document):
        """Process a Document: extract content if file, create segments, and update stats"""
        try:
            # Extract content for files
            if document.content_type == 'file' and document.file_path and not document.content:
                ext = document.file_type or 'txt'
                content = self.process_file_content(document.file_path, ext)
                document.content = content
                document.content_preview = content[:500] + ('...' if len(content) > 500 else '') if content else None

            # Update counts
            if document.content:
                document.character_count = len(document.content)
                document.word_count = len(document.content.split())
                document.status = 'completed'

            db.session.commit()

        except Exception as e:
            db.session.rollback()
            raise e

    def _basic_file_processing(self, file_path: str, file_type: str) -> str:
        """Basic file processing fallback"""
        if file_type.lower() in ['txt', 'text']:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                logger.error(f"Error reading text file: {e}")
                return ""
        return ""

    def chunk_text_for_processing(self, text: str, chunk_size: int = 1000,
                                  chunk_overlap: int = 200, segmenter=None) -> List[str]:
        """Chunk text for processing with optional overlap"""
        if not segmenter:
            # Simple chunking by character count
            chunks = []
            start = 0
            while start < len(text):
                end = start + chunk_size
                chunks.append(text[start:end])
                start = end - chunk_overlap if chunk_overlap > 0 else end
            return chunks

        # Intelligent chunking using paragraphs
        paragraphs = segmenter.split_into_paragraphs(text)
        chunks = []
        current_chunk = ""

        for paragraph in paragraphs:
            if len(current_chunk) + len(paragraph) > chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = paragraph
            else:
                current_chunk = current_chunk + "\n\n" + paragraph if current_chunk else paragraph

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks
