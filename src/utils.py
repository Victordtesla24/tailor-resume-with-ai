"""Utility functions for performance monitoring and error handling."""

import hashlib
import logging
import os
import re
import resource
import sys
import time
from functools import lru_cache, wraps
from pathlib import Path
from typing import (Any, Callable, Dict, NamedTuple, Optional, Protocol,
                    TypedDict, TypeVar)

logger = logging.getLogger("resume_tailor")

T = TypeVar("T")

# Constants
MAX_MEMORY_MB = 500
MAX_UPLOAD_TIME = 3
MAX_AI_TIME = 10
MAX_INPUT_SIZE = 50000
CHUNK_SIZE = 1024 * 1024  # 1MB chunks for file reading

# Required environment variables with their validators
REQUIRED_ENV_VARS = {
    "OPENAI_API_KEY": (
        lambda x: bool(x and x.startswith("sk-")),
        'OpenAI API key must start with "sk-". Please check your API key format.',
    ),
    "ANTHROPIC_API_KEY": (
        lambda x: bool(x and x.startswith("sk-ant-")),
        'Anthropic API key must start with "sk-ant-". Please check your API key format.',
    ),
}

# Try to import psutil, fallback to resource module
USE_PSUTIL = False  # Disable psutil since it's causing import issues
logger = logging.getLogger("resume_tailor")


# Custom type definitions
class ValidationResult(TypedDict):
    """Result of validation operation containing validity and error message."""

    valid: bool
    error: Optional[str]


class InputMetrics(TypedDict):
    """Metrics for input validation including length and maximum allowed size."""

    length: int
    max_allowed: int


class InputValidationResult(TypedDict):
    """Result of input validation including validity, error message, and metrics."""

    valid: bool
    error: Optional[str]
    metrics: InputMetrics


class EnvVarStatus(TypedDict):
    """Status of environment variable validation including presence and validity."""

    present: bool
    valid: bool
    error: Optional[str]


class EnvCheckResult(TypedDict):
    """Result of environment variable checks with detailed status and counts."""

    valid: bool
    variables: Dict[str, EnvVarStatus]
    missing_count: int
    invalid_count: int


class EnvValidatorProtocol(Protocol):
    """Protocol defining interface for environment variable validators."""

    def __call__(self, value: Optional[str]) -> bool:
        ...


class ValidatorConfig(NamedTuple):
    """Configuration for validators including validation function and error message."""

    validator: EnvValidatorProtocol
    error_msg: str


class EnvValidator:
    """Environment variable validator with type-safe methods."""

    @staticmethod
    def validate_openai_key(value: Optional[str]) -> bool:
        return bool(value and value.startswith("sk-"))

    @staticmethod
    def validate_anthropic_key(value: Optional[str]) -> bool:
        return bool(value and value.startswith("sk-ant-"))


def get_memory_usage() -> float:
    """Get current memory usage in MB."""
    try:
        # Use resource module directly since psutil is not available
        rusage = resource.getrusage(resource.RUSAGE_SELF)
        if sys.platform == "darwin":
            # macOS reports in bytes
            return float(rusage.ru_maxrss) / (1024 * 1024)
        else:
            # Linux reports in kilobytes
            return float(rusage.ru_maxrss) / 1024
    except (OSError, ValueError) as e:
        logger.error("Error getting memory usage: %s", str(e))
        return 0.0


@lru_cache(maxsize=100)
def get_cached_memory_usage() -> float:
    """Get memory usage with caching to reduce system calls."""
    return get_memory_usage()


def track_performance(operation: str) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator to track operation performance."""

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            start_time = time.time()
            start_memory = get_memory_usage()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                memory_used = get_memory_usage() - start_memory
                # Log performance metrics
                logger.info(
                    f"{operation} completed in {duration:.2f}s " f"using {memory_used:.2f}MB memory"
                )
                # Check against thresholds
                if operation == "file_upload" and duration > MAX_UPLOAD_TIME:
                    logger.warning(f"Slow file upload: {duration:.2f}s > {MAX_UPLOAD_TIME}s")
                elif operation == "ai_response" and duration > MAX_AI_TIME:
                    logger.warning(f"Slow AI response: {duration:.2f}s > {MAX_AI_TIME}s")
                if memory_used > MAX_MEMORY_MB * 0.8:  # Warning at 80%
                    logger.warning(f"High memory usage: {memory_used:.2f}MB")
                return result
            except Exception as e:
                logger.error(f"{operation} failed: {str(e)}")
                raise

        return wrapper

    return decorator


def validate_file_format(file_name: str) -> ValidationResult:
    """Validate file format with detailed checks."""
    if not file_name:
        return {"valid": False, "error": "No file provided"}

    if not file_name.lower().endswith(".docx"):
        return {"valid": False, "error": "Only .docx files are supported"}

    return {"valid": True, "error": None}


def anonymize_data(text: str) -> str:
    """Anonymize sensitive data in text."""
    patterns = [
        (r"\b[\w\.-]+@[\w\.-]+\.\w+\b", "[EMAIL]"),
        (r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", "[PHONE]"),
        (
            r"\b\d+\s+[A-Za-z\s,]+\b(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd)\.?\b",
            "[ADDRESS]",
        ),
        (r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b", "[NAME]"),  # Possible names
        (r"\b(?:http[s]?://)?(?:[\w-]+\.)+[\w-]+(?:/[^\s]*)?", "[URL]"),  # URLs
        (r"\b\d{5}(?:-\d{4})?\b", "[ZIP]"),  # ZIP codes
    ]

    anonymized = text
    for pattern, replacement in patterns:
        anonymized = re.sub(pattern, replacement, anonymized)

    # Truncate long strings to reduce identifiable content
    if len(anonymized) > MAX_INPUT_SIZE:
        anonymized = anonymized[:MAX_INPUT_SIZE] + "..."

    return anonymized


def validate_input_size(text: str, max_size: int = MAX_INPUT_SIZE) -> InputValidationResult:
    """Validate input size with metrics."""
    if not text or text.strip() == "":  # Enhanced empty check
        return {
            "valid": False,
            "error": "Empty input provided. Please enter some text.",
            "metrics": {"length": 0, "max_allowed": max_size},
        }

    # Remove excessive whitespace
    text = " ".join(text.split())
    length = len(text)

    if length < 10:  # Minimum reasonable size
        return {
            "valid": False,
            "error": "Input too short. Please provide more details.",
            "metrics": {"length": length, "max_allowed": max_size},
        }

    if length > max_size:
        error_msg = (
            f"Input too large ({length:,} characters). "
            f"Maximum allowed is {max_size:,} characters."
        )
        return {
            "valid": False,
            "error": error_msg,
            "metrics": {"length": length, "max_allowed": max_size},
        }

    return {"valid": True, "error": None, "metrics": {"length": length, "max_allowed": max_size}}


def check_environment_variables() -> EnvCheckResult:
    """Check required environment variables with detailed validation."""
    results: Dict[str, EnvVarStatus] = {}
    missing_count = 0
    invalid_count = 0

    for var_name, (validator_func, error_msg) in REQUIRED_ENV_VARS.items():
        value = os.getenv(var_name)
        status: EnvVarStatus = {"present": bool(value), "valid": False, "error": None}

        if not value:
            status["error"] = (
                f"Missing {var_name}. Please set this environment variable. "
                "You can find your API key in your account settings."
            )
            missing_count += 1
        elif not validator_func(value):
            status["error"] = (
                f"Invalid {var_name}: {error_msg} "
                "Please check your account settings for the correct key."
            )
            invalid_count += 1
        else:
            status["valid"] = True

        results[var_name] = status

    return {
        "valid": missing_count == 0 and invalid_count == 0,
        "variables": results,
        "missing_count": missing_count,
        "invalid_count": invalid_count,
    }


def get_secure_storage_path() -> Path:
    """Get secure storage path for sensitive data."""
    # Use XDG_DATA_HOME or platform-specific default
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local" / "share"))

    base_dir = base / "resume_tailor" / "data"
    base_dir.mkdir(parents=True, exist_ok=True)

    # Set directory permissions to be private
    try:
        if sys.platform != "win32":  # Skip on Windows
            os.chmod(base_dir, 0o700)  # User read/write/execute only

            # Ensure parent directory is also protected
            parent = base_dir.parent
            if parent.exists():
                os.chmod(parent, 0o755)  # More permissive for parent
    except (OSError, PermissionError) as e:
        logger.warning("Could not set directory permissions: %s", str(e))

    # Create a secure random subdirectory for this session
    session_id = hashlib.sha256((str(time.time()) + os.urandom(16).hex()).encode()).hexdigest()[:16]

    secure_dir = base_dir / session_id
    secure_dir.mkdir(parents=True, exist_ok=True)

    try:
        if sys.platform != "win32":  # Skip on Windows
            os.chmod(secure_dir, 0o700)  # User read/write/execute only
    except (OSError, PermissionError) as e:
        logger.warning("Could not set session directory permissions: %s", str(e))

    return secure_dir


def hash_sensitive_data(data: str) -> str:
    """Hash sensitive data for storage."""
    return hashlib.sha256(data.encode()).hexdigest()


def handle_ai_call(operation: str, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """Handle AI calls with timeout and retry logic."""
    start_time = time.time()
    retries = 2  # Maximum 2 retries
    last_error = None

    for attempt in range(retries + 1):
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time

            if duration > MAX_AI_TIME:
                logger.warning(f"AI call took {duration:.2f}s (limit: {MAX_AI_TIME}s)")

            return result

        except Exception as e:
            last_error = e
            if attempt < retries:
                logger.warning(f"{operation} failed (attempt {attempt + 1}): {str(e)}")
                time.sleep(1)  # Brief pause before retry
            else:
                logger.error(f"{operation} failed after {retries} retries: {str(e)}")

    # If we get here, all retries failed
    raise ValueError(f"AI operation failed: {str(last_error)}")


def validate_job_description(text: str) -> InputValidationResult:
    """Validate job description with specific checks."""
    # First check basic input size
    size_validation = validate_input_size(text)
    if not size_validation["valid"]:
        return size_validation

    # Additional job description specific checks
    text = text.strip()
    word_count = len(text.split())

    if word_count < 20:  # Minimum words for a reasonable job description
        return {
            "valid": False,
            "error": "Job description too short. Please provide more details.",
            "metrics": {"length": len(text), "max_allowed": MAX_INPUT_SIZE},
        }

    return {
        "valid": True,
        "error": None,
        "metrics": {"length": len(text), "max_allowed": MAX_INPUT_SIZE},
    }
