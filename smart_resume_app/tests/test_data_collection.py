"""Tests for data collection and anonymization functionality."""
import pytest
import json
from unittest.mock import Mock, patch
from src.data_collection import (
    PIIData,
    PIIDetector,
    Tokenizer,
    DataCollector,
    DataRetentionManager,
    RateLimiter
)


@pytest.fixture
def sample_resume_text():
    """Create sample resume text with PII."""
    return """
    John Smith
    email: john.smith@example.com
    Phone: +1 (555) 123-4567
    Location: Melbourne, Victoria
    
    Experience at Microsoft from Jan 2020 to Dec 2021
    """


@pytest.fixture
def sample_job_text():
    """Create sample job description text."""
    return """
    Position at Google
    Location: Sydney, NSW
    
    Requirements:
    - 5+ years experience
    - Bachelor's degree
    """


@pytest.fixture
def pii_detector():
    """Create PIIDetector instance."""
    return PIIDetector()


@pytest.fixture
def tokenizer():
    """Create Tokenizer instance."""
    return Tokenizer()


@pytest.fixture
def temp_jsonl(tmp_path):
    """Create temporary JSONL file."""
    file_path = tmp_path / "test_data.jsonl"
    return str(file_path)


def test_pii_detection(pii_detector, sample_resume_text):
    """Test PII detection in text."""
    pii = pii_detector.detect(sample_resume_text)
    
    assert isinstance(pii, PIIData)
    assert "John Smith" in pii.names
    assert "john.smith@example.com" in pii.emails
    assert "+1 (555) 123-4567" in pii.phones
    assert "Melbourne" in pii.locations
    assert "Microsoft" in pii.organizations
    assert "Jan 2020" in pii.dates


def test_pii_tokenization(tokenizer, pii_detector, sample_resume_text):
    """Test PII replacement with tokens."""
    pii = pii_detector.detect(sample_resume_text)
    anonymized = tokenizer.replace_pii(sample_resume_text, pii)
    
    assert "John Smith" not in anonymized
    assert "[NAME]" in anonymized
    assert "john.smith@example.com" not in anonymized
    assert "[EMAIL]" in anonymized
    assert "Melbourne" not in anonymized
    assert "[LOCATION]" in anonymized


def test_data_collection(temp_jsonl, sample_resume_text, sample_job_text):
    """Test training data collection and storage."""
    collector = DataCollector(temp_jsonl)
    
    # Test data saving
    collector.save_training_data(
        sample_resume_text,
        sample_job_text,
        "Tailored content",
        {"model": "gpt-4"}
    )
    
    # Verify saved data
    with open(temp_jsonl) as f:
        data = json.loads(f.readline())
        assert "prompt" in data
        assert "completion" in data
        assert "metadata" in data
        assert data["metadata"]["model"] == "gpt-4"
        
        # Verify PII was anonymized
        assert "John Smith" not in data["prompt"]
        assert "[NAME]" in data["prompt"]


def test_data_retention(temp_jsonl):
    """Test data retention management."""
    manager = DataRetentionManager(temp_jsonl)
    
    # Create test data
    with open(temp_jsonl, "w") as f:
        # Old data (40 days ago)
        f.write(json.dumps({
            "timestamp": "2023-01-01T00:00:00",
            "data": "old"
        }) + "\n")
        # Recent data
        f.write(json.dumps({
            "timestamp": "2024-01-01T00:00:00",
            "data": "new"
        }) + "\n")
    
    # Clean up old data
    manager.cleanup_old_data(days=30)
    
    # Verify only recent data remains
    with open(temp_jsonl) as f:
        data = [json.loads(line) for line in f]
        assert len(data) == 1
        assert data[0]["data"] == "new"


def test_rate_limiter():
    """Test rate limiting functionality."""
    limiter = RateLimiter(max_requests=2, window_seconds=1)
    
    # Test within limit
    assert limiter.can_access()
    assert limiter.can_access()
    
    # Test exceeding limit
    assert not limiter.can_access()


def test_pii_detection_edge_cases(pii_detector):
    """Test PII detection edge cases."""
    # Test empty text
    pii = pii_detector.detect("")
    assert not pii.names
    assert not pii.emails
    
    # Test text without PII
    text = "This is a technical document about programming."
    pii = pii_detector.detect(text)
    assert not pii.names
    assert not pii.emails
    assert not pii.phones
    
    # Test unusual formats
    text = """
    Name: J. R. Smith Jr.
    Email: user+test@sub.example.com
    Phone: 1.555.123.4567
    """
    pii = pii_detector.detect(text)
    assert any("Smith" in name for name in pii.names)
    assert "user+test@sub.example.com" in pii.emails
    assert "1.555.123.4567" in pii.phones


def test_data_collector_error_handling(temp_jsonl):
    """Test error handling in data collection."""
    collector = DataCollector(temp_jsonl)
    
    # Test with invalid file path
    with pytest.raises(Exception):
        collector.storage_path = "/invalid/path/data.jsonl"
        collector.save_training_data("", "", "", {})
    
    # Test with invalid metadata
    with pytest.raises(TypeError):
        collector.save_training_data(
            "",
            "",
            "",
            {"invalid": object()}
        )


@patch('spacy.load')
def test_spacy_model_loading(mock_load):
    """Test spaCy model loading behavior."""
    # Test successful model loading
    mock_load.return_value = Mock()
    PIIDetector()  # Create instance to trigger model loading
    mock_load.assert_called_once_with('en_core_web_sm')
    
    # Reset mock for testing model download fallback
    mock_load.reset_mock()
    mock_load.side_effect = [OSError, Mock()]
    PIIDetector()  # Create instance to trigger model loading
    assert mock_load.call_count == 2  # One failed attempt + one successful attempt
