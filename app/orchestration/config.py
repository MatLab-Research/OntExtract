"""
Orchestration Configuration

Manages configuration for LLM orchestration including timeout and retry settings.
"""

import os
from typing import Optional


class OrchestrationConfig:
    """Configuration for LLM orchestration error handling."""

    # LLM Timeout Settings
    LLM_TIMEOUT_SECONDS: int = int(os.getenv('LLM_TIMEOUT_SECONDS', '300'))  # 5 minutes default

    # Retry Settings
    LLM_MAX_RETRIES: int = int(os.getenv('LLM_MAX_RETRIES', '3'))
    LLM_RETRY_INITIAL_DELAY: float = float(os.getenv('LLM_RETRY_INITIAL_DELAY', '1.0'))
    LLM_RETRY_MAX_DELAY: float = float(os.getenv('LLM_RETRY_MAX_DELAY', '60.0'))
    LLM_RETRY_EXPONENTIAL_BASE: float = float(os.getenv('LLM_RETRY_EXPONENTIAL_BASE', '2.0'))

    # Retryable error codes/types
    RETRYABLE_HTTP_CODES = {429, 500, 502, 503, 504}  # Rate limit, server errors
    RETRYABLE_ERROR_TYPES = {
        'timeout',
        'connection_error',
        'rate_limit_error',
        'server_error',
        'service_unavailable'
    }

    @classmethod
    def get_retry_delay(cls, attempt: int) -> float:
        """
        Calculate retry delay using exponential backoff.

        Args:
            attempt: Retry attempt number (0-indexed)

        Returns:
            Delay in seconds before next retry
        """
        delay = cls.LLM_RETRY_INITIAL_DELAY * (cls.LLM_RETRY_EXPONENTIAL_BASE ** attempt)
        return min(delay, cls.LLM_RETRY_MAX_DELAY)

    @classmethod
    def is_retryable_error(cls, error: Exception) -> bool:
        """
        Determine if an error is retryable.

        Args:
            error: The exception that occurred

        Returns:
            True if error should be retried
        """
        error_str = str(error).lower()
        error_type = type(error).__name__.lower()

        # Check for retryable error types
        if any(retryable_type in error_type for retryable_type in cls.RETRYABLE_ERROR_TYPES):
            return True

        # Check error message for retryable indicators
        retryable_messages = [
            'timeout',
            'timed out',
            'connection',
            'rate limit',
            '429',
            '500',
            '502',
            '503',
            '504',
            'temporary',
            'transient'
        ]

        if any(msg in error_str for msg in retryable_messages):
            return True

        # Check HTTP status codes if available
        if hasattr(error, 'status_code'):
            return error.status_code in cls.RETRYABLE_HTTP_CODES

        return False


# Global instance
config = OrchestrationConfig()
