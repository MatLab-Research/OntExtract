"""
Text Cleanup Service for OntExtract

Uses LLM (Claude) to clean and improve document text quality by fixing:
- OCR errors and character recognition mistakes
- Spelling and grammar issues
- Formatting problems (paragraph breaks, whitespace)
- Scanning artifacts (headers, footers, page numbers)
- Punctuation and quote normalization
"""

import os
import logging
from typing import Tuple, Dict, Any

logger = logging.getLogger(__name__)


class TextCleanupService:
    """Service for LLM-based text cleaning and improvement."""

    def __init__(self):
        """Initialize the text cleanup service."""
        self.api_key = os.environ.get('ANTHROPIC_API_KEY')
        self._client = None

    @property
    def client(self):
        """Lazy-load the Anthropic client."""
        if self._client is None:
            if not self.api_key:
                raise ValueError("ANTHROPIC_API_KEY environment variable not set")

            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.api_key)
                logger.info("Anthropic client initialized for text cleanup")
            except ImportError:
                raise ImportError("anthropic package not installed. Install with: pip install anthropic")

        return self._client

    def clean_text(self, text: str, max_chunk_size: int = 8000) -> Tuple[str, Dict[str, Any]]:
        """
        Clean text using Claude to fix errors and improve quality.

        Args:
            text: The text to clean
            max_chunk_size: Maximum characters per LLM call (for large documents)

        Returns:
            Tuple of (cleaned_text, metadata_dict)
        """
        if not text or not text.strip():
            return text, {'error': 'Empty text provided'}

        # Handle large documents by chunking
        if len(text) > max_chunk_size:
            logger.info(f"Text length {len(text)} exceeds chunk size {max_chunk_size}, using chunking")
            return self._clean_large_document(text, max_chunk_size)

        # Clean single chunk
        return self._clean_chunk(text)

    def _clean_chunk(self, text: str) -> Tuple[str, Dict[str, Any]]:
        """
        Clean a single chunk of text using Claude.

        Args:
            text: The text chunk to clean

        Returns:
            Tuple of (cleaned_text, metadata_dict)
        """
        prompt = f"""Please clean and improve the following text by fixing:

1. OCR errors (common character recognition mistakes like 'rn' -> 'm', 'l' -> 'I', etc.)
2. Spelling mistakes
3. Grammar issues
4. Paragraph breaks and formatting (ensure proper sentence and paragraph boundaries)
5. Scanning artifacts (stray headers, footers, page numbers in wrong places)
6. Normalize punctuation and quotes (use proper quotation marks, fix double spaces, etc.)

IMPORTANT RULES:
- Preserve the original meaning and structure completely
- Keep all technical terms, proper nouns, and specialized vocabulary unchanged
- Only fix clear and obvious errors
- Do not add new content or interpretations
- Maintain the same overall length and format
- If you're unsure whether something is an error, leave it unchanged

TEXT TO CLEAN:
{text}

Return ONLY the cleaned text with no explanations, commentary, or additional formatting."""

        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=len(text) * 2,  # Allow for some expansion
                temperature=0.0,  # Deterministic for consistency
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            cleaned_text = message.content[0].text.strip()

            metadata = {
                'model': 'claude-sonnet-4-5-20250929',
                'input_tokens': message.usage.input_tokens,
                'output_tokens': message.usage.output_tokens,
                'original_length': len(text),
                'cleaned_length': len(cleaned_text),
                'chunks_processed': 1
            }

            logger.info(f"Text cleaned successfully: {len(text)} -> {len(cleaned_text)} chars")
            return cleaned_text, metadata

        except Exception as e:
            logger.error(f"Error cleaning text with Claude: {e}")
            raise

    def _clean_large_document(self, text: str, chunk_size: int) -> Tuple[str, Dict[str, Any]]:
        """
        Clean large documents by processing in chunks.

        Strategy: Split by paragraphs to maintain context and natural boundaries.

        Args:
            text: The full text to clean
            chunk_size: Maximum characters per chunk

        Returns:
            Tuple of (cleaned_text, metadata_dict)
        """
        # Split into paragraphs (preserving double newlines)
        paragraphs = text.split('\n\n')

        cleaned_paragraphs = []
        total_input_tokens = 0
        total_output_tokens = 0
        chunks_processed = 0

        current_chunk = []
        current_length = 0

        for para in paragraphs:
            para_len = len(para)

            # If adding this paragraph would exceed chunk size and we have content, process current chunk
            if current_length + para_len > chunk_size and current_chunk:
                # Process current chunk
                chunk_text = '\n\n'.join(current_chunk)
                cleaned_chunk, chunk_meta = self._clean_chunk(chunk_text)
                cleaned_paragraphs.append(cleaned_chunk)

                # Update stats
                total_input_tokens += chunk_meta.get('input_tokens', 0)
                total_output_tokens += chunk_meta.get('output_tokens', 0)
                chunks_processed += 1

                # Start new chunk with current paragraph
                current_chunk = [para]
                current_length = para_len
            else:
                # Add to current chunk
                current_chunk.append(para)
                current_length += para_len + 2  # +2 for \n\n

        # Process final chunk
        if current_chunk:
            chunk_text = '\n\n'.join(current_chunk)
            cleaned_chunk, chunk_meta = self._clean_chunk(chunk_text)
            cleaned_paragraphs.append(cleaned_chunk)

            total_input_tokens += chunk_meta.get('input_tokens', 0)
            total_output_tokens += chunk_meta.get('output_tokens', 0)
            chunks_processed += 1

        # Combine all cleaned chunks
        cleaned_text = '\n\n'.join(cleaned_paragraphs)

        metadata = {
            'model': 'claude-sonnet-4-5-20250929',
            'input_tokens': total_input_tokens,
            'output_tokens': total_output_tokens,
            'original_length': len(text),
            'cleaned_length': len(cleaned_text),
            'chunks_processed': chunks_processed,
            'chunking_used': True
        }

        logger.info(f"Large document cleaned: {chunks_processed} chunks, {len(text)} -> {len(cleaned_text)} chars")
        return cleaned_text, metadata
