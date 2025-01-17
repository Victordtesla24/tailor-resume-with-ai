"""Custom exceptions for the resume tailoring application."""


class RateLimitExceeded(Exception):
    """Raised when API rate limit is exceeded."""


class InvalidAPIKey(Exception):
    """Raised when API key is invalid or missing."""


class ModelNotFound(Exception):
    """Raised when requested AI model is not available."""


class ProcessingError(Exception):
    """Raised when resume processing fails."""


class FormatError(Exception):
    """Raised when document formatting fails."""


class JobBoardError(Exception):
    """Raised when job board scraping fails."""


class DataCollectionError(Exception):
    """Raised when data collection or anonymization fails."""
