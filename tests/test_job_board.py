"""Tests for job board integration functionality."""

import time
from unittest.mock import Mock, patch

import pytest
import requests

from src.job_board import (JobBoardError, JobBoardManager, JobDetails,
                           SeekScraper)


@pytest.fixture
def sample_seek_html() -> str:
    """Create sample Seek job listing HTML."""
    return """
    <html>
        <head><title>Test Job</title></head>
        <body>
            <h1>Solution Architect</h1>
            <a data-automation="company-link">Test Company</a>
            <span data-automation="job-location">Melbourne, VIC</span>
            <div data-automation="jobAdDetails">
                <h2>About the Role</h2>
                <p>We are seeking a Solution Architect...</p>
                <h2>Requirements</h2>
                <ul>
                    <li>5+ years experience</li>
                    <li>Cloud expertise</li>
                </ul>
                <h2>Responsibilities</h2>
                <ul>
                    <li>Design solutions</li>
                    <li>Lead technical teams</li>
                </ul>
                <h2>Qualifications</h2>
                <ul>
                    <li>Bachelor's degree</li>
                    <li>Certifications</li>
                </ul>
            </div>
        </body>
    </html>
    """


@pytest.fixture
def mock_response(sample_seek_html: str) -> Mock:
    """Create mock response with sample HTML."""
    mock = Mock()
    mock.text = sample_seek_html
    mock.raise_for_status = Mock()
    mock.iter_content = Mock(return_value=[sample_seek_html.encode()])
    return mock


@pytest.fixture
def seek_scraper() -> SeekScraper:
    """Create SeekScraper instance."""
    return SeekScraper()


def test_job_details_creation() -> None:
    """Test JobDetails dataclass creation."""
    details = JobDetails(
        title="Test Job",
        company="Test Company",
        location="Test Location",
        description="Test Description",
        requirements=["Req 1", "Req 2"],
        responsibilities=["Resp 1", "Resp 2"],
        qualifications=["Qual 1", "Qual 2"],
    )

    assert details.title == "Test Job"
    assert len(details.requirements) == 2
    assert len(details.responsibilities) == 2
    assert len(details.qualifications) == 2


def test_seek_url_validation(seek_scraper: SeekScraper) -> None:
    """Test Seek URL validation."""
    valid_url = "https://www.seek.com.au/job/12345"
    invalid_url = "https://example.com/job/12345"

    assert seek_scraper.can_handle(valid_url)
    assert not seek_scraper.can_handle(invalid_url)


@patch("requests.Session.get")
def test_seek_job_extraction(
    mock_get: Mock, mock_response: Mock, seek_scraper: SeekScraper
) -> None:
    """Test job details extraction from Seek."""
    mock_get.return_value = mock_response

    job_details = seek_scraper.fetch("https://www.seek.com.au/job/12345")

    assert job_details is not None
    assert job_details.title == "Solution Architect"
    assert job_details.company == "Test Company"
    assert job_details.location == "Melbourne, VIC"
    assert "Solution Architect" in job_details.description
    assert len(job_details.requirements) > 0
    assert len(job_details.responsibilities) > 0
    assert len(job_details.qualifications) > 0


@patch("requests.Session.get")
def test_seek_error_handling(mock_get: Mock, seek_scraper: SeekScraper) -> None:
    """Test error handling in job fetching."""
    # Test connection error
    mock_get.side_effect = requests.ConnectionError("Connection error")
    result = seek_scraper.fetch("https://www.seek.com.au/job/12345")
    assert result is None

    # Test timeout error
    mock_get.side_effect = requests.Timeout("Timeout error")
    result = seek_scraper.fetch("https://www.seek.com.au/job/12345")
    assert result is None

    # Test invalid HTML
    mock_response = Mock()
    mock_response.text = "<invalid>html"
    mock_response.iter_content = Mock(return_value=[b"<invalid>html"])
    mock_get.side_effect = None
    mock_get.return_value = mock_response
    result = seek_scraper.fetch("https://www.seek.com.au/job/12345")
    assert result is None


def test_job_board_manager() -> None:
    """Test JobBoardManager functionality."""
    manager = JobBoardManager()

    # Test URL support checking
    assert manager.is_supported_url("https://www.seek.com.au/job/12345")
    assert not manager.is_supported_url("https://example.com/job/12345")

    # Test scraper selection
    assert isinstance(manager.scrapers["seek"], SeekScraper)


@patch("requests.Session.get")
def test_job_board_manager_fetch(mock_get: Mock, mock_response: Mock) -> None:
    """Test job fetching through manager."""
    mock_get.return_value = mock_response
    manager = JobBoardManager()

    # Test successful fetch
    job_details = manager.fetch_job_details("https://www.seek.com.au/job/12345")
    assert job_details is not None
    assert job_details.title == "Solution Architect"

    # Test unsupported URL
    with pytest.raises(JobBoardError):
        manager.fetch_job_details("https://example.com/job/12345")


def test_job_details_extraction_edge_cases(seek_scraper: SeekScraper) -> None:
    """Test edge cases in job details extraction."""
    # Test with minimal HTML
    minimal_html = """
    <html>
        <h1>Test Job</h1>
        <div data-automation="jobAdDetails">
            <p>Description</p>
        </div>
    </html>
    """

    with patch("requests.Session.get") as mock_get:
        mock_response = Mock()
        mock_response.text = minimal_html
        mock_response.iter_content = Mock(return_value=[minimal_html.encode()])
        mock_get.return_value = mock_response
        
        result = seek_scraper.fetch("https://www.seek.com.au/job/12345")

        assert result is not None
        assert result.title == "Test Job"
        assert result.company == "Unknown Company"
        assert result.location == "Unknown Location"


@patch("requests.Session.get")
def test_response_time(mock_get: Mock, mock_response: Mock, seek_scraper: SeekScraper) -> None:
    """Test response time is under 5 seconds."""
    mock_get.return_value = mock_response
    
    start_time = time.time()
    job_details = seek_scraper.fetch("https://www.seek.com.au/job/12345")
    end_time = time.time()
    
    assert job_details is not None
    assert end_time - start_time < 5, "Response time exceeded 5 seconds"


@patch("requests.Session.get")
def test_streaming_functionality(mock_get: Mock, seek_scraper: SeekScraper) -> None:
    """Test streaming functionality for large responses."""
    # Create a large HTML response
    large_html = "x" * (1024 * 1024)  # 1MB of data
    chunks = [large_html[i:i + 8192].encode() for i in range(0, len(large_html), 8192)]
    
    mock_response = Mock()
    mock_response.iter_content = Mock(return_value=chunks)
    mock_get.return_value = mock_response
    
    start_time = time.time()
    seek_scraper.fetch("https://www.seek.com.au/job/12345")
    end_time = time.time()
    
    # Verify streaming was used (chunks were processed)
    assert mock_response.iter_content.called
    assert end_time - start_time < 5, "Large response processing exceeded 5 seconds"


@patch("requests.Session.get")
def test_connection_pooling(mock_get: Mock, mock_response: Mock, seek_scraper: SeekScraper) -> None:
    """Test connection pooling reuse."""
    mock_get.return_value = mock_response
    
    # Make multiple requests
    for _ in range(5):
        seek_scraper.fetch("https://www.seek.com.au/job/12345")
    
    # Verify session was reused
    assert mock_get.call_count == 5
    assert all(call[1].get('timeout') == 5 for call in mock_get.call_args_list)


@patch("requests.Session.get")
def test_error_recovery(mock_get: Mock, mock_response: Mock, seek_scraper: SeekScraper) -> None:
    """Test error recovery and retry mechanism."""
    # Simulate temporary failures followed by success
    mock_get.side_effect = [
        requests.ConnectionError("Temporary error"),
        requests.Timeout("Timeout"),
        mock_response
    ]
    
    job_details = seek_scraper.fetch("https://www.seek.com.au/job/12345")
    
    assert job_details is not None
    assert mock_get.call_count == 3  # Verify retries were attempted


@patch("requests.Session.get")
def test_compression_handling(mock_get: Mock, seek_scraper: SeekScraper) -> None:
    """Test handling of compressed responses."""
    mock_response = Mock()
    mock_response.headers = {"Content-Encoding": "gzip"}
    mock_response.iter_content = Mock(return_value=[b"compressed_content"])
    mock_get.return_value = mock_response
    
    seek_scraper.fetch("https://www.seek.com.au/job/12345")
    
    # Verify compression headers were sent
    assert "gzip" in mock_get.call_args[1]["headers"]["Accept-Encoding"]
