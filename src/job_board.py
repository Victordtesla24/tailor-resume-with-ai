"""Job board integration for fetching job descriptions."""

import logging
from typing import Dict
import aiohttp
from bs4 import BeautifulSoup

logger = logging.getLogger("resume_tailor")


class JobBoardClient:
    """Client for interacting with job boards."""

    def __init__(self) -> None:
        """Initialize job board client."""
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/91.0.4472.114 Safari/537.36"
            )
        }

    async def fetch_job_description(self, url: str) -> Dict[str, str]:
        """Fetch job description from supported job boards.

        Args:
            url: URL of the job posting

        Returns:
            Dictionary containing job details

        Raises:
            ValueError: If job details cannot be extracted or URL is not supported
        """
        try:
            # Basic URL validation
            if not url.startswith(('http://', 'https://')):
                logger.warning("Invalid URL format: %s", url)
                raise ValueError("Invalid URL format - must start with http:// or https://")

            if "seek.com.au" not in url:
                logger.warning("Unsupported job board URL: %s", url)
                raise ValueError("Unsupported job board - only seek.com.au is supported")

            return await self._fetch_from_seek(url)
        except Exception as e:
            logger.error(f"Error fetching job description: {str(e)}")
            raise

    async def _fetch_from_seek(self, url: str) -> Dict[str, str]:
        """Fetch job description from seek.com.au.

        Args:
            url: Seek job posting URL

        Returns:
            Dictionary containing job details

        Raises:
            ValueError: If job details cannot be extracted
        """
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(url) as response:
                response.raise_for_status()
                html = await response.text()

        soup = BeautifulSoup(html, "html.parser")

        # Extract job details
        title = soup.find("h1", {"data-automation": "job-detail-title"})
        company = soup.find("span", {"data-automation": "advertiser-name"})
        location = soup.find("span", {"data-automation": "job-detail-location"})
        description = soup.find("div", {"data-automation": "jobAdDetails"})

        if not all([title, description]):
            raise ValueError("Could not extract required job details")

        return {
            "title": title.text.strip(),
            "company": company.text.strip() if company else "",
            "location": location.text.strip() if location else "",
            "description": description.get_text(separator="\n").strip()
        }
