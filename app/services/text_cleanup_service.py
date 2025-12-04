"""
Text Cleanup Service for OntExtract

Uses LLM (Claude) to clean and improve document text quality by fixing:
- OCR errors and character recognition mistakes
- Spelling and grammar issues
- Formatting problems (paragraph breaks, whitespace)
- Scanning artifacts (headers, footers, page numbers)
- Punctuation and quote normalization

Supports both sequential and parallel chunk processing modes.
"""

import os
import logging
from typing import Tuple, Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed

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

    def clean_text(self, text: str, max_chunk_size: int = 8000, progress_callback=None) -> Tuple[str, Dict[str, Any]]:
        """
        Clean text using Claude to fix errors and improve quality.

        Args:
            text: The text to clean
            max_chunk_size: Maximum characters per LLM call (for large documents)
            progress_callback: Optional callback function(current_chunk, total_chunks) for progress updates

        Returns:
            Tuple of (cleaned_text, metadata_dict)
        """
        if not text or not text.strip():
            return text, {'error': 'Empty text provided'}

        # Handle large documents by chunking
        if len(text) > max_chunk_size:
            logger.info(f"Text length {len(text)} exceeds chunk size {max_chunk_size}, using chunking")
            return self._clean_large_document(text, max_chunk_size, progress_callback)

        # Clean single chunk
        if progress_callback:
            progress_callback(1, 1)
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

    def _get_processing_settings(self) -> Tuple[bool, int]:
        """
        Get concurrent processing settings from AppSetting.

        Returns:
            Tuple of (concurrent_enabled, max_concurrent_chunks)
        """
        try:
            from app.models.app_settings import AppSetting
            concurrent_enabled = AppSetting.get_setting('concurrent_chunk_processing', default=True)
            max_concurrent = AppSetting.get_setting('max_concurrent_chunks', default=3)
            # Clamp max_concurrent to reasonable bounds
            max_concurrent = max(1, min(10, int(max_concurrent)))
            return concurrent_enabled, max_concurrent
        except Exception as e:
            logger.warning(f"Could not load processing settings, using defaults: {e}")
            return True, 3

    def _clean_large_document(self, text: str, chunk_size: int, progress_callback=None) -> Tuple[str, Dict[str, Any]]:
        """
        Clean large documents by processing in chunks.

        Strategy: Split by paragraphs to maintain context and natural boundaries.
        Supports both sequential and parallel processing based on settings.

        Args:
            text: The full text to clean
            chunk_size: Maximum characters per chunk
            progress_callback: Optional callback function(current_chunk, total_chunks) for progress updates

        Returns:
            Tuple of (cleaned_text, metadata_dict)
        """
        # Split into paragraphs (preserving double newlines)
        paragraphs = text.split('\n\n')

        # Pre-calculate chunks to get total count for progress
        chunks_to_process = []
        current_chunk = []
        current_length = 0

        for para in paragraphs:
            para_len = len(para)

            if current_length + para_len > chunk_size and current_chunk:
                chunks_to_process.append('\n\n'.join(current_chunk))
                current_chunk = [para]
                current_length = para_len
            else:
                current_chunk.append(para)
                current_length += para_len + 2

        if current_chunk:
            chunks_to_process.append('\n\n'.join(current_chunk))

        total_chunks = len(chunks_to_process)

        # Get processing settings
        concurrent_enabled, max_concurrent = self._get_processing_settings()

        if concurrent_enabled and total_chunks > 1:
            logger.info(f"Processing {total_chunks} chunks in parallel (max {max_concurrent} concurrent)")
            return self._clean_chunks_parallel(chunks_to_process, progress_callback, max_concurrent)
        else:
            logger.info(f"Processing {total_chunks} chunks sequentially")
            return self._clean_chunks_sequential(chunks_to_process, progress_callback)

    def _clean_chunks_sequential(self, chunks: List[str], progress_callback=None) -> Tuple[str, Dict[str, Any]]:
        """
        Process chunks sequentially (original behavior).

        Args:
            chunks: List of text chunks to clean
            progress_callback: Optional callback function(current_chunk, total_chunks)

        Returns:
            Tuple of (cleaned_text, metadata_dict)
        """
        total_chunks = len(chunks)
        cleaned_paragraphs = []
        total_input_tokens = 0
        total_output_tokens = 0

        for i, chunk_text in enumerate(chunks):
            # Update progress before processing chunk
            if progress_callback:
                progress_callback(i + 1, total_chunks)

            cleaned_chunk, chunk_meta = self._clean_chunk(chunk_text)
            cleaned_paragraphs.append(cleaned_chunk)

            # Update stats
            total_input_tokens += chunk_meta.get('input_tokens', 0)
            total_output_tokens += chunk_meta.get('output_tokens', 0)

        # Combine all cleaned chunks
        cleaned_text = '\n\n'.join(cleaned_paragraphs)

        original_length = sum(len(c) for c in chunks) + (len(chunks) - 1) * 2  # Account for \n\n separators

        metadata = {
            'model': 'claude-sonnet-4-5-20250929',
            'input_tokens': total_input_tokens,
            'output_tokens': total_output_tokens,
            'original_length': original_length,
            'cleaned_length': len(cleaned_text),
            'chunks_processed': total_chunks,
            'chunking_used': True,
            'processing_mode': 'sequential'
        }

        logger.info(f"Large document cleaned sequentially: {total_chunks} chunks")
        return cleaned_text, metadata

    def _clean_chunks_parallel(self, chunks: List[str], progress_callback=None, max_workers: int = 3) -> Tuple[str, Dict[str, Any]]:
        """
        Process chunks in parallel using ThreadPoolExecutor.

        Maintains order by tracking chunk indices.

        Args:
            chunks: List of text chunks to clean
            progress_callback: Optional callback function(current_chunk, total_chunks)
            max_workers: Maximum concurrent API calls

        Returns:
            Tuple of (cleaned_text, metadata_dict)
        """
        total_chunks = len(chunks)
        results = [None] * total_chunks  # Pre-allocate to maintain order
        total_input_tokens = 0
        total_output_tokens = 0
        completed_count = 0

        def process_chunk(index: int, chunk_text: str) -> Tuple[int, str, Dict[str, Any]]:
            """Process a single chunk and return (index, cleaned_text, metadata)."""
            cleaned_chunk, chunk_meta = self._clean_chunk(chunk_text)
            return index, cleaned_chunk, chunk_meta

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all chunks
            futures = {
                executor.submit(process_chunk, i, chunk): i
                for i, chunk in enumerate(chunks)
            }

            # Process results as they complete
            for future in as_completed(futures):
                try:
                    index, cleaned_chunk, chunk_meta = future.result()
                    results[index] = cleaned_chunk

                    # Update stats
                    total_input_tokens += chunk_meta.get('input_tokens', 0)
                    total_output_tokens += chunk_meta.get('output_tokens', 0)

                    # Update progress (completed count, not index)
                    completed_count += 1
                    if progress_callback:
                        progress_callback(completed_count, total_chunks)

                except Exception as e:
                    # Get the original chunk index for error reporting
                    chunk_index = futures[future]
                    logger.error(f"Error processing chunk {chunk_index}: {e}")
                    raise RuntimeError(f"Failed to process chunk {chunk_index}: {e}")

        # Verify all chunks were processed
        if None in results:
            missing = [i for i, r in enumerate(results) if r is None]
            raise RuntimeError(f"Missing results for chunks: {missing}")

        # Combine all cleaned chunks in order
        cleaned_text = '\n\n'.join(results)

        original_length = sum(len(c) for c in chunks) + (len(chunks) - 1) * 2  # Account for \n\n separators

        metadata = {
            'model': 'claude-sonnet-4-5-20250929',
            'input_tokens': total_input_tokens,
            'output_tokens': total_output_tokens,
            'original_length': original_length,
            'cleaned_length': len(cleaned_text),
            'chunks_processed': total_chunks,
            'chunking_used': True,
            'processing_mode': 'parallel',
            'max_concurrent': max_workers
        }

        logger.info(f"Large document cleaned in parallel: {total_chunks} chunks with {max_workers} workers")
        return cleaned_text, metadata
