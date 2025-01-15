"""Utility classes and functions."""
import time
from typing import Dict


class RateLimiter:
    """Rate limiter for API calls."""

    def __init__(self, requests_per_minute: int = 60):
        """Initialize rate limiter."""
        self.requests_per_minute = requests_per_minute
        self.requests: Dict[int, int] = {}

    def can_access(self) -> bool:
        """Check if request is allowed under rate limit."""
        current_minute = int(time.time() / 60)

        # Clean old entries
        self.requests = {
            minute: count
            for minute, count in self.requests.items()
            if minute >= current_minute - 1
        }

        # Check current minute's requests
        current_requests = self.requests.get(current_minute, 0)
        if current_requests >= self.requests_per_minute:
            return False

        # Update request count
        self.requests[current_minute] = current_requests + 1
        return True
