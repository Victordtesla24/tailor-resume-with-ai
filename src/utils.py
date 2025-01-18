"""Utility functions and classes for the resume tailoring app."""

import logging
import os
import psutil
import tempfile
import time
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, TypeVar, cast

T = TypeVar("T")

logger = logging.getLogger(__name__)

# Constants
MAX_UPLOAD_TIME = 3  # seconds
MAX_AI_TIME = 10  # seconds
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_TEXT_LENGTH = 10000  # characters
MAX_INPUT_SIZE = 50000  # characters for API inputs
CHUNK_SIZE = 4096  # bytes for file reading
MAX_MEMORY_MB = 500  # Maximum memory usage in MB


class RateLimiter:
    """Rate limiter for API calls."""

    def __init__(self, requests_per_minute: int):
        """Initialize rate limiter.

        Args:
            requests_per_minute: Maximum number of requests allowed per minute
        """
        self.requests_per_minute = requests_per_minute
        self.window = 60.0  # 1 minute in seconds
        self.timestamps: list[float] = []

    def can_access(self) -> bool:
        """Check if we can make another request."""
        now = time.time()

        # Remove timestamps older than the window
        self.timestamps = [ts for ts in self.timestamps if now - ts <= self.window]

        if len(self.timestamps) >= self.requests_per_minute:
            return False

        self.timestamps.append(now)
        return True

    def __call__(self, func: Callable) -> Callable:
        """Decorator to rate limit function calls."""

        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not self.can_access():
                logger.warning("Rate limit reached. Waiting for next window.")
                time.sleep(self.window / self.requests_per_minute)
            return func(*args, **kwargs)

        return wrapper


def validate_file_format(filename: str) -> Dict[str, Any]:
    """Validate file format is .docx.

    Returns:
        Dict with validation result and error message if any.
    """
    if not filename:
        return {"valid": False, "error": "No filename provided"}

    if not filename.lower().endswith(".docx"):
        return {"valid": False, "error": "Invalid file format. Only .docx files are supported."}

    return {"valid": True, "error": None}


def validate_input_size(text: str) -> Dict[str, Any]:
    """Validate input text size.

    Returns:
        Dict with validation result and error message if any.
    """
    if not text:
        return {"valid": False, "error": "No text provided"}

    text_length = len(text)
    if text_length > MAX_TEXT_LENGTH:
        return {
            "valid": False,
            "error": f"Text too long ({text_length} chars, max {MAX_TEXT_LENGTH})",
        }

    return {"valid": True, "error": None}


def check_environment_variables() -> Dict[str, str]:
    """Check required environment variables are set and valid."""
    required_vars = {
        "OPENAI_API_KEY": lambda x: x and x.startswith("sk-"),
        "ANTHROPIC_API_KEY": lambda x: x and x.startswith("sk-ant-"),
    }

    status = {}
    for var, validator_func in required_vars.items():
        value = os.getenv(var)
        try:
            if validator_func(value):
                status[var] = "valid"
            else:
                status[var] = "invalid"
        except (TypeError, AttributeError):
            status[var] = "missing"

    return status


def anonymize_data(text: str) -> str:
    """Anonymize sensitive data in text."""
    # TODO: Implement more sophisticated anonymization
    return text[:300] + "..." if len(text) > 300 else text


def get_memory_usage() -> float:
    """Get current memory usage in MB."""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024


def track_performance(operation: str) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator to track function performance."""

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            start_time = time.time()
            start_memory = get_memory_usage()

            try:
                result = func(*args, **kwargs)

                end_time = time.time()
                end_memory = get_memory_usage()

                duration = end_time - start_time
                memory_used = end_memory - start_memory

                logger.info(
                    "%s completed in %.2fs using %.2fMB memory", operation, duration, memory_used
                )

                return result

            except Exception as e:
                logger.error("%s failed: %s", operation, str(e))
                raise

        return cast(Callable[..., T], wrapper)

    return decorator


def get_secure_storage_path() -> Path:
    """Get secure storage path for sensitive data.

    Returns:
        Path to secure storage directory.
    """
    base_dir = Path(tempfile.gettempdir()) / "resume_tailor"
    base_dir.mkdir(mode=0o700, exist_ok=True)
    return base_dir
