"""Tests for data collection functionality."""

import json
import logging
from typing import Any

import pytest

from src.data_collection import (DataCollector, DataRetentionManager, PIIData,
                                 PIIDetector, RateLimiter, TextProcessor,
                                 Tokenizer)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Disable redefined-outer-name warning for pytest fixtures
# pylint: disable=redefined-outer-name


@pytest.fixture
def input_resume() -> str:
    """Create sample resume text for testing."""
    return """
John Doe
123 Main St, San Francisco, CA
john.doe@email.com
(555) 123-4567

Experience:
Software Engineer at Tech Corp
Led development of cloud solutions
"""


@pytest.fixture
def input_job() -> str:
    """Create sample job description text for testing."""
    return """
Senior Software Engineer
Requirements:
- 5+ years experience
- Cloud expertise
- Strong communication skills
"""


@pytest.fixture
def pii_detector_fixture() -> PIIDetector:
    """Create PIIDetector instance for testing."""
    return PIIDetector()


@pytest.fixture
def tokenizer_fixture() -> Tokenizer:
    """Create Tokenizer instance for testing."""
    return Tokenizer()


@pytest.fixture
def test_file(tmp_path: Any) -> str:
    """Create temporary JSONL file for testing."""
    file_path = tmp_path / "test.jsonl"
    return str(file_path)


def test_pii_detection(pii_detector_fixture: PIIDetector, input_resume: str) -> None:
    """Test PII detection functionality."""
    pii = pii_detector_fixture.detect(input_resume)

    assert isinstance(pii, PIIData)
    assert "John Doe" in pii.names
    assert "john.doe@email.com" in pii.emails
    assert "(555) 123-4567" in pii.phones
    assert "San Francisco" in pii.locations
    assert "Tech Corp" in pii.organizations


def test_pii_tokenization(
    tokenizer_fixture: Tokenizer,
    pii_detector_fixture: PIIDetector,
    input_resume: str
) -> None:
    """Test PII tokenization functionality."""
    pii = pii_detector_fixture.detect(input_resume)
    tokenized = tokenizer_fixture.replace_pii(input_resume, pii)

    assert "[NAME]" in tokenized
    assert "[EMAIL]" in tokenized
    assert "[PHONE]" in tokenized
    assert "[LOCATION]" in tokenized
    assert "[ORGANIZATION]" in tokenized


def test_data_collection(
    test_file: str,
    input_resume: str,
    input_job: str
) -> None:
    """Test data collection functionality."""
    collector = DataCollector(test_file)
    metadata = {"source": "test"}

    collector.save_training_data(
        input_resume,
        input_job,
        "Tailored output",
        metadata
    )

    # Verify saved data
    with open(test_file, encoding="utf-8") as f:
        data = json.loads(f.readline())
        assert "timestamp" in data
        assert "prompt" in data
        assert "completion" in data
        assert data["metadata"] == metadata


def test_rate_limiter() -> None:
    """Test rate limiting functionality."""
    limiter = RateLimiter(max_requests=2, window_seconds=1)

    assert limiter.can_access()
    assert limiter.can_access()
    assert not limiter.can_access()


def test_text_processor() -> None:
    """Test text processing functionality."""
    processor = TextProcessor()
    text = "The quick brown fox jumps over the lazy dog"

    sentences = processor.extract_sentences(text)
    assert len(sentences) == 1

    tokens = processor.tokenize_text(text)
    assert len(tokens) > 0

    filtered = processor.remove_stopwords(tokens)
    assert len(filtered) < len(tokens)

    lemmatized = processor.lemmatize_tokens(tokens)
    assert len(lemmatized) == len(tokens)


def test_pii_detection_empty(pii_detector_fixture: PIIDetector) -> None:
    """Test PII detection with empty input."""
    pii = pii_detector_fixture.detect("")
    assert isinstance(pii, PIIData)
    assert len(pii.names) == 0
    assert len(pii.emails) == 0
    assert len(pii.phones) == 0
    assert len(pii.locations) == 0
    assert len(pii.organizations) == 0


def test_data_retention_nonexistent(test_file: str) -> None:
    """Test data retention with nonexistent file."""
    manager = DataRetentionManager(test_file)
    manager.cleanup_old_data(days=1)  # Should not raise any errors
