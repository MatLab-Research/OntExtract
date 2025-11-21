"""
Retry Utilities for LLM Orchestration

Provides timeout and retry logic for LLM API calls with exponential backoff.
"""

import asyncio
import logging
from typing import Callable, TypeVar, Any
from functools import wraps

from .config import config

logger = logging.getLogger(__name__)

T = TypeVar('T')


class LLMTimeoutError(Exception):
    """Raised when an LLM call exceeds the configured timeout."""
    pass


class LLMRetryExhaustedError(Exception):
    """Raised when all retry attempts have been exhausted."""
    pass


async def call_llm_with_timeout(
    coro: Callable[..., Any],
    timeout_seconds: int = None,
    operation_name: str = "LLM call"
) -> Any:
    """
    Execute an async LLM call with timeout.

    Args:
        coro: Coroutine to execute
        timeout_seconds: Timeout in seconds (default from config)
        operation_name: Name of operation for logging

    Returns:
        Result of the coroutine

    Raises:
        LLMTimeoutError: If operation exceeds timeout
    """
    if timeout_seconds is None:
        timeout_seconds = config.LLM_TIMEOUT_SECONDS

    try:
        result = await asyncio.wait_for(coro, timeout=timeout_seconds)
        return result
    except asyncio.TimeoutError as e:
        error_msg = f"{operation_name} exceeded timeout of {timeout_seconds} seconds"
        logger.error(error_msg)
        raise LLMTimeoutError(error_msg) from e


async def call_llm_with_retry(
    coro_factory: Callable[[], Any],
    max_retries: int = None,
    timeout_seconds: int = None,
    operation_name: str = "LLM call"
) -> Any:
    """
    Execute an async LLM call with retry logic and timeout.

    Args:
        coro_factory: Factory function that creates the coroutine (called for each retry)
        max_retries: Maximum number of retries (default from config)
        timeout_seconds: Timeout in seconds (default from config)
        operation_name: Name of operation for logging

    Returns:
        Result of the coroutine

    Raises:
        LLMRetryExhaustedError: If all retries are exhausted
        LLMTimeoutError: If operation exceeds timeout
        Exception: If a non-retryable error occurs
    """
    if max_retries is None:
        max_retries = config.LLM_MAX_RETRIES

    if timeout_seconds is None:
        timeout_seconds = config.LLM_TIMEOUT_SECONDS

    last_error = None

    for attempt in range(max_retries + 1):  # +1 for initial attempt
        try:
            logger.info(f"{operation_name}: Attempt {attempt + 1}/{max_retries + 1}")

            # Create fresh coroutine for this attempt
            coro = coro_factory()

            # Execute with timeout
            result = await call_llm_with_timeout(
                coro,
                timeout_seconds=timeout_seconds,
                operation_name=operation_name
            )

            if attempt > 0:
                logger.info(f"{operation_name}: Succeeded on retry attempt {attempt}")

            return result

        except LLMTimeoutError:
            # Timeouts are not retryable - fail immediately
            raise

        except Exception as e:
            last_error = e

            # Check if error is retryable
            if not config.is_retryable_error(e):
                logger.error(f"{operation_name}: Non-retryable error: {e}")
                raise

            # If we've exhausted retries, fail
            if attempt >= max_retries:
                logger.error(f"{operation_name}: Exhausted all {max_retries} retries")
                break

            # Calculate delay before next retry
            delay = config.get_retry_delay(attempt)
            logger.warning(
                f"{operation_name}: Retryable error on attempt {attempt + 1}: {e}. "
                f"Retrying in {delay:.1f} seconds..."
            )

            # Wait before retrying
            await asyncio.sleep(delay)

    # All retries exhausted
    error_msg = f"{operation_name} failed after {max_retries + 1} attempts. Last error: {last_error}"
    raise LLMRetryExhaustedError(error_msg) from last_error


def with_llm_retry(
    operation_name: str = None,
    max_retries: int = None,
    timeout_seconds: int = None
):
    """
    Decorator to add retry logic and timeout to async LLM functions.

    Usage:
        @with_llm_retry(operation_name="Analyze Experiment", max_retries=3, timeout_seconds=300)
        async def analyze_experiment_node(state):
            # ... LLM call ...
            return result

    Args:
        operation_name: Name of operation for logging
        max_retries: Maximum number of retries
        timeout_seconds: Timeout in seconds
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Use function name if operation_name not provided
            op_name = operation_name or func.__name__

            # Create factory that calls the original function
            async def coro_factory():
                return await func(*args, **kwargs)

            return await call_llm_with_retry(
                coro_factory=coro_factory,
                max_retries=max_retries,
                timeout_seconds=timeout_seconds,
                operation_name=op_name
            )

        return wrapper
    return decorator
