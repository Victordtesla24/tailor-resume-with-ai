"""Custom exceptions for the resume tailoring application."""


class RateLimitExceeded(Exception):
    """Raised when API rate limit is exceeded."""
    pass


class InvalidAPIKey(Exception):
    """Raised when API key is invalid or missing."""
    pass


class ModelNotFound(Exception):
    """Raised when requested AI model is not available."""
    pass


class ProcessingError(Exception):
    """Raised when resume processing fails."""
    pass


class FormatError(Exception):
    """Raised when document formatting fails."""
    pass


class JobBoardError(Exception):
    """Raised when job board scraping fails."""
    pass


class DataCollectionError(Exception):
    """Raised when data collection or anonymization fails."""
    pass
