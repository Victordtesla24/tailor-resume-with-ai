"""Tests for job board integration functionality."""
import pytest
from unittest.mock import Mock, patch
from src.job_board import JobDetails, SeekScraper, JobBoardManager


@pytest.fixture
def sample_seek_html():
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
def mock_response(sample_seek_html):
    """Create mock response with sample HTML."""
    mock = Mock()
    mock.text = sample_seek_html
    mock.raise_for_status = Mock()
    return mock


@pytest.fixture
def seek_scraper():
    """Create SeekScraper instance."""
    return SeekScraper()


def test_job_details_creation():
    """Test JobDetails dataclass creation."""
    details = JobDetails(
        title="Test Job",
        company="Test Company",
        location="Test Location",
        description="Test Description",
        requirements=["Req 1", "Req 2"],
        responsibilities=["Resp 1", "Resp 2"],
        qualifications=["Qual 1", "Qual 2"]
    )
    
    assert details.title == "Test Job"
    assert len(details.requirements) == 2
    assert len(details.responsibilities) == 2
    assert len(details.qualifications) == 2


def test_seek_url_validation(seek_scraper):
    """Test Seek URL validation."""
    valid_url = "https://www.seek.com.au/job/12345"
    invalid_url = "https://example.com/job/12345"
    
    assert seek_scraper.can_handle(valid_url)
    assert not seek_scraper.can_handle(invalid_url)


@patch('requests.get')
def test_seek_job_extraction(mock_get, mock_response, seek_scraper):
    """Test job details extraction from Seek."""
    mock_get.return_value = mock_response
    
    job_details = seek_scraper.fetch(
        "https://www.seek.com.au/job/12345"
    )
    
    assert job_details is not None
    assert job_details.title == "Solution Architect"
    assert job_details.company == "Test Company"
    assert job_details.location == "Melbourne, VIC"
    assert "Solution Architect" in job_details.description
    assert len(job_details.requirements) > 0
    assert len(job_details.responsibilities) > 0
    assert len(job_details.qualifications) > 0


@patch('requests.get')
def test_seek_error_handling(mock_get, seek_scraper):
    """Test error handling in job fetching."""
    # Test connection error
    mock_get.side_effect = Exception("Connection error")
    result = seek_scraper.fetch("https://www.seek.com.au/job/12345")
    assert result is None
    
    # Test invalid HTML
    mock_response = Mock()
    mock_response.text = "<invalid>html"
    mock_get.side_effect = None
    mock_get.return_value = mock_response
    result = seek_scraper.fetch("https://www.seek.com.au/job/12345")
    assert result is None


def test_job_board_manager():
    """Test JobBoardManager functionality."""
    manager = JobBoardManager()
    
    # Test URL support checking
    assert manager.is_supported_url(
        "https://www.seek.com.au/job/12345"
    )
    assert not manager.is_supported_url(
        "https://example.com/job/12345"
    )
    
    # Test scraper selection
    assert isinstance(
        manager.scrapers['seek'],
        SeekScraper
    )


@patch('requests.get')
def test_job_board_manager_fetch(mock_get, mock_response):
    """Test job fetching through manager."""
    mock_get.return_value = mock_response
    manager = JobBoardManager()
    
    # Test successful fetch
    job_details = manager.fetch_job_details(
        "https://www.seek.com.au/job/12345"
    )
    assert job_details is not None
    assert job_details.title == "Solution Architect"
    
    # Test unsupported URL
    result = manager.fetch_job_details(
        "https://example.com/job/12345"
    )
    assert result is None


def test_job_details_extraction_edge_cases(seek_scraper):
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
    
    with patch('requests.get') as mock_get:
        mock_get.return_value = Mock(text=minimal_html)
        result = seek_scraper.fetch(
            "https://www.seek.com.au/job/12345"
        )
        
        assert result is not None
        assert result.title == "Test Job"
        assert result.company == "Unknown Company"
        assert result.location == "Unknown Location"
