"""Job board integration for resume tailoring app."""
import logging
import time
from typing import Dict, List, Optional
from dataclasses import dataclass
import requests
from bs4 import BeautifulSoup
from bs4.element import Tag
from urllib.parse import urlparse
from src.exceptions import JobBoardError

# Setup logging
logger = logging.getLogger(__name__)


@dataclass
class JobDetails:
    """Container for job posting details."""
    title: str
    company: str
    location: str
    description: str
    requirements: List[str]
    responsibilities: List[str]
    qualifications: List[str]


class JobBoardManager:
    """Manager for job board integrations."""

    def __init__(self):
        """Initialize with supported scrapers."""
        self.scrapers: Dict[str, 'SeekScraper'] = {
            'seek': SeekScraper()
        }
        self.max_retries = 3
        self.retry_delay = 1  # seconds

    def is_supported_url(self, url: str) -> bool:
        """Check if URL is supported."""
        return any(
            scraper.can_handle(url) for scraper in self.scrapers.values()
        )

    def fetch_job_details(self, url: str) -> Optional[JobDetails]:
        """Fetch job description with automatic site detection and retry
        logic."""
        try:
            # Validate URL format
            if not url.startswith(('http://', 'https://')):
                raise JobBoardError(
                    "Invalid URL format. Must start with http:// or https://"
                )

            domain = urlparse(url).netloc.lower()
            if not domain:
                raise JobBoardError("Invalid URL: missing domain")

            # Find matching scraper
            matching_scrapers = [
                (site, scraper)
                for site, scraper in self.scrapers.items()
                if site in domain and scraper.can_handle(url)
            ]

            if not matching_scrapers:
                supported_sites = ", ".join(self.scrapers.keys())
                raise JobBoardError(
                    f"Unsupported job board: {domain}.\n"
                    f"Supported sites: {supported_sites}"
                )

            # Try each matching scraper with retries
            errors = []
            for site, scraper in matching_scrapers:
                for attempt in range(self.max_retries):
                    try:
                        return scraper.fetch(url)
                    except Exception as e:
                        msg = f"Attempt {attempt + 1} failed for {site}"
                        logger.warning(f"{msg}: {str(e)}")
                        if attempt < self.max_retries - 1:
                            time.sleep(self.retry_delay)
                        errors.append(f"{site}: {str(e)}")

            # If all retries failed
            error_details = "\n".join(errors)
            msg = (
                f"Failed to fetch job description after "
                f"{self.max_retries} attempts:\n{error_details}"
            )
            raise JobBoardError(msg)

        except JobBoardError:
            raise
        except Exception as e:
            msg = f"Failed to fetch job description: {str(e)}"
            logger.error(f"Unexpected error: {str(e)}")
            raise JobBoardError(msg)

    def get_supported_sites(self) -> List[str]:
        """Get list of supported job board sites."""
        return list(self.scrapers.keys())


class SeekScraper:
    """Scraper for Seek job postings."""

    def __init__(self):
        """Initialize scraper."""
        self.headers = {
            'User-Agent': (
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/91.0.4472.114 Safari/537.36'
            )
        }

    def can_handle(self, url: str) -> bool:
        """Check if URL is from Seek."""
        return 'seek.com.au' in url.lower()

    def fetch(self, url: str) -> Optional[JobDetails]:
        """Fetch and parse Seek job posting."""
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract job details
            h1 = soup.find('h1')
            title = h1.text.strip() if h1 else "Unknown Title"

            company_link = soup.find(
                'a', {'data-automation': 'company-link'}
            )
            company = (
                company_link.text.strip()
                if company_link
                else "Unknown Company"
            )

            location_span = soup.find(
                'span', {'data-automation': 'job-location'}
            )
            location = (
                location_span.text.strip()
                if location_span
                else "Unknown Location"
            )

            # Get job description
            description_div = soup.find(
                'div', {'data-automation': 'jobAdDetails'}
            )
            if not description_div:
                return None

            description = description_div.get_text('\n', strip=True)

            # Extract lists
            requirements = []
            responsibilities = []
            qualifications = []

            # Find all lists in the description
            lists: List[Tag] = []
            if hasattr(description_div, 'find_all'):
                find = description_div.find_all
                lists.extend(find('ul'))
                for ul in lists:
                    if hasattr(ul, 'find_all'):
                        items = [
                            li.text.strip()
                            for li in ul.find_all('li')
                        ]
                        # Categorize based on preceding header
                        prev = ul.find_previous(['h2', 'h3', 'strong'])
                        if prev and hasattr(prev, 'text'):
                            header = prev.text.lower()
                            if 'requirement' in header:
                                requirements.extend(items)
                            elif 'responsibilit' in header:
                                responsibilities.extend(items)
                            elif 'qualification' in header:
                                qualifications.extend(items)

            return JobDetails(
                title=title,
                company=company,
                location=location,
                description=description,
                requirements=requirements,
                responsibilities=responsibilities,
                qualifications=qualifications
            )

        except Exception as e:
            logger.error(f"Error fetching job details: {str(e)}")
            return None

    def _log_html_preview(self, html: str) -> None:
        """Log a preview of HTML content in chunks."""
        logger.debug("HTML preview:")
        text = html[:1000]
        chunk_size = 200
        for i in range(0, len(text), chunk_size):
            logger.debug(text[i:i + chunk_size])

    def _make_request(self, url: str) -> str:
        """Make HTTP request with error handling."""
        try:
            # Add more browser-like headers
            # Use latest Chrome on macOS
            headers = {
                'User-Agent': (
                    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/121.0.0.0 Safari/537.36'
                ),
                # Parse URL for dynamic host header
                'Host': urlparse(url).netloc,
                # Standard browser headers
                'Accept': (
                    'text/html,application/xhtml+xml,application/xml;'
                    'q=0.9,*/*;q=0.8'
                ),
                'Accept-Language': 'en-AU,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Cache-Control': 'no-cache',
                'Cookie': '',  # Empty cookie to avoid tracking
                # Security headers
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1'
            }

            # Increase timeout and allow redirects
            response = requests.get(
                url,
                headers=headers,
                timeout=30,
                allow_redirects=True
            )
            response.raise_for_status()

            # Log response info for debugging
            logger.debug(f"Response status: {response.status_code}")
            logger.debug(f"Response headers: {response.headers}")

            # Check if we got a valid response
            if not response.text:
                raise JobBoardError("Empty response from server")

            # Parse response
            soup = BeautifulSoup(response.text, 'html.parser')

            # Log HTML preview for debugging
            if logger.isEnabledFor(logging.DEBUG):
                self._log_html_preview(response.text)

            # Look for job content markers
            has_details = soup.find(
                attrs={'data-automation': 'jobAdDetails'}
            )
            has_desc = soup.find(
                attrs={'data-automation': 'jobDescription'}
            )
            has_class = soup.find(attrs={'class': 'job-description'})

            # Check if any marker was found
            job_content_found = bool(has_details or has_desc or has_class)

            if not job_content_found:
                raise JobBoardError("Could not find job content")

            return response.text

        except requests.RequestException as e:
            logger.error(f"Request failed: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(
                    f"Response status: {e.response.status_code}"
                )
                logger.error(f"Response headers: {e.response.headers}")
            raise JobBoardError(f"Failed to fetch job posting: {str(e)}")
