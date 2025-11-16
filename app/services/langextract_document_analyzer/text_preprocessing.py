"""
Text Preprocessing Module

Handles text cleaning and preparation for LangExtract processing.
"""

import logging
from typing import Tuple

logger = logging.getLogger(__name__)


class TextPreprocessor:
    """Clean and prepare text for LangExtract analysis"""

    @staticmethod
    def clean_text(text: str, max_length: int = 50000) -> Tuple[str, bool]:
        """
        Clean text for LangExtract processing

        Args:
            text: Raw document text
            max_length: Maximum character length (default 50,000)

        Returns:
            Tuple of (cleaned_text, was_truncated)
        """
        if not text:
            return "", False

        # Remove null characters that break processing
        text = text.replace('\x00', '')

        # Track if we need to truncate
        was_truncated = False
        if len(text) > max_length:
            text = text[:max_length]
            was_truncated = True
            logger.warning(f"Text truncated to {max_length:,} characters for processing")

        return text, was_truncated

    @staticmethod
    def validate_text(text: str, min_length: int = 10) -> bool:
        """
        Validate text is suitable for meaningful analysis

        Args:
            text: Text to validate
            min_length: Minimum character length

        Returns:
            True if text is valid for analysis
        """
        if not text:
            return False

        return len(text.strip()) >= min_length
