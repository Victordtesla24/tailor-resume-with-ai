"""Job board integration for resume tailoring app."""
import logging
import time
from typing import Dict, List
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from src.exceptions import JobBoardError

# Setup logging
logger = logging.getLogger(__name__)


class JobBoardScraper:
    """Enhanced job board integration with multiple site support and robust
    error handling."""

    def __init__(self) -> None:
        """Initialize with supported job boards."""
        self.scrapers: Dict[str, JobScraper] = {
            'seek': SeekScraper(),
            'indeed': IndeedScraper(),
            'linkedin': LinkedInScraper()
        }
        self.max_retries = 3
        self.retry_delay = 1  # seconds

    def fetch_job_description(self, url: str) -> str:
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


class JobScraper:
    """Base class for job board scrapers."""

    def __init__(self):
        """Initialize with common headers."""
        self.headers = {
            'User-Agent': (
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/91.0.4472.114 Safari/537.36'
            )
        }

    def can_handle(self, url: str) -> bool:
        """Check if scraper can handle this URL."""
        raise NotImplementedError

    def fetch(self, url: str) -> str:
        """Fetch and parse job description."""
        raise NotImplementedError

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


class SeekScraper(JobScraper):
    """Scraper for Seek.com.au job postings."""

    def can_handle(self, url: str) -> bool:
        """Check if URL is from Seek."""
        return 'seek.com.au' in url.lower()

    def fetch(self, url: str) -> str:
        """Fetch and parse Seek job description."""
        html = self._make_request(url)
        soup = BeautifulSoup(html, 'html.parser')

        # Try finding job description in modern Seek layout
        job_desc = None

        # Try to find the job description in the modern Seek layout
        # First look for the main job details container
        main_container = soup.find('div', {'data-automation': 'jobAdDetails'})
        if not main_container:
            main_container = soup.find(
                'div', {'data-automation': 'job-details'}
            )

        if main_container and hasattr(main_container, 'find_all'):
            # Look for specific sections within the container
            sections = main_container.find_all(
                ['div', 'section', 'article'],
                recursive=False
            )

            # Try to find the description section
            for section in sections:
                # Check various attributes for description indicators
                attrs = []
                if hasattr(section, 'get'):
                    attrs.extend(section.get('class', []))
                    attrs.append(section.get('id', ''))
                    attrs.append(section.get('data-automation', ''))

                attrs_text = ' '.join(str(attr) for attr in attrs).lower()
                if any(
                    text in attrs_text
                    for text in [
                        'description', 'details', 'about',
                        'job-ad-details', 'jobaddetails'
                    ]
                ):
                    job_desc = section
                    break

        # Fallback to traditional selectors
        if not job_desc:
            selectors = [
                {'data-automation': 'jobDescription'},
                {'data-automation': 'job-description'},
                {'data-automation': 'job-details'},
                {'class': 'job-description'},
                {'class': 'jobDescription'},
                {'class': 'job-details'},
                {'class': 'description'},
                {'id': 'job-description'},
                {'id': 'jobDescription'},
                {'id': 'job-details'}
            ]

            for selector in selectors:
                job_desc = soup.find(['div', 'section'], selector)
                if job_desc:
                    break

        # Log debug info
        logger.debug("HTML structure:")
        for tag in soup.find_all(['article', 'div', 'section'])[:5]:
            logger.debug(
                "Tag: %s, Class: %s, ID: %s, Data: %s",
                tag.name,
                tag.get('class', ''),
                tag.get('id', ''),
                tag.get('data-automation', '')
            )

        if not job_desc:
            # Try finding any div with "job" and "description" in class/id
            job_desc = soup.find(
                lambda tag: tag.name == 'div' and any(
                    'job' in attr and 'description' in attr
                    for attr in [
                        tag.get('class', ''),
                        tag.get('id', ''),
                        tag.get('data-automation', '')
                    ]
                )
            )

        if not job_desc:
            raise JobBoardError("Could not find job description")

        # Extract and clean text
        description = job_desc.get_text(separator='\n', strip=True)

        # Basic validation
        if len(description) < 50:  # Arbitrary minimum length
            raise JobBoardError("Job description seems too short")
        return description


class IndeedScraper(JobScraper):
    """Scraper for Indeed job postings."""

    def can_handle(self, url: str) -> bool:
        """Check if URL is from Indeed."""
        return 'indeed.com' in url.lower()

    def fetch(self, url: str) -> str:
        """Fetch and parse Indeed job description."""
        html = self._make_request(url)
        soup = BeautifulSoup(html, 'html.parser')

        # Try multiple possible selectors
        selectors = [
            {'id': 'jobDescriptionText'},
            {'class': 'jobsearch-jobDescriptionText'},
            {'id': 'job-description'},
            {'class': 'job-desc'},
            {'class': 'description'}
        ]

        job_desc = None
        for selector in selectors:
            job_desc = soup.find('div', selector)
            if job_desc:
                break

        if not job_desc:
            # Try finding any div with "job" and "description" in class/id
            job_desc = soup.find(
                lambda tag: tag.name == 'div' and any(
                    'job' in attr and 'description' in attr
                    for attr in [
                        tag.get('class', ''),
                        tag.get('id', '')
                    ]
                )
            )

        if not job_desc:
            raise JobBoardError("Could not find job description")

        # Extract and clean text
        description = job_desc.get_text(separator='\n', strip=True)

        # Basic validation
        if len(description) < 50:  # Arbitrary minimum length
            raise JobBoardError("Job description seems too short")
        return description


class LinkedInScraper(JobScraper):
    """Scraper for LinkedIn job postings."""

    def can_handle(self, url: str) -> bool:
        """Check if URL is from LinkedIn."""
        return 'linkedin.com' in url.lower()

    def fetch(self, url: str) -> str:
        """Fetch and parse LinkedIn job description."""
        html = self._make_request(url)
        soup = BeautifulSoup(html, 'html.parser')

        # Try multiple possible selectors
        selectors = [
            {'class': 'description__text'},
            {'class': 'show-more-less-html__markup'},
            {'class': 'job-description'},
            {'class': 'description'},
            {'class': 'job-details'}
        ]

        job_desc = None
        for selector in selectors:
            job_desc = soup.find('div', selector)
            if job_desc:
                break

        if not job_desc:
            # Try finding any div with "job" and "description" in class/id
            job_desc = soup.find(
                lambda tag: tag.name == 'div' and any(
                    'job' in attr and 'description' in attr
                    for attr in [
                        tag.get('class', ''),
                        tag.get('id', '')
                    ]
                )
            )

        if not job_desc:
            raise JobBoardError("Could not find job description")

        # Extract and clean text
        description = job_desc.get_text(separator='\n', strip=True)

        # Basic validation
        if len(description) < 50:  # Arbitrary minimum length
            raise JobBoardError("Job description seems too short")
        return description


def extract_job_requirements(description: str) -> Dict[str, list[str]]:
    """Extract structured requirements from job description."""
    try:
        requirements: Dict[str, list[str]] = {
            'skills': [],
            'experience': [],
            'education': [],
            'responsibilities': []
        }

        # Split into sections
        sections = description.lower().split('\n')
        current_section = None

        for line in sections:
            line = line.strip()
            if not line:
                continue

            # Detect section headers
            if 'requirements' in line or 'skills' in line:
                current_section = 'skills'
            elif 'experience' in line:
                current_section = 'experience'
            elif 'education' in line or 'qualification' in line:
                current_section = 'education'
            elif 'responsibilities' in line or 'duties' in line:
                current_section = 'responsibilities'
            elif line.startswith('•') or line.startswith('-'):
                if current_section:
                    requirements[current_section].append(
                        line.lstrip('•- ').strip()
                    )

        return requirements

    except Exception as e:
        logger.error(f"Error extracting requirements: {str(e)}")
        return requirements
