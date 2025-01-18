import asyncio
import logging
from threading import Lock
from time import time
from typing import Dict, Optional

logger = logging.getLogger("resume_tailor")


class TokenBucket:
    """Enhanced token bucket rate limiter for API requests with monitoring."""
    def __init__(
        self,
        tokens_per_second: float,
        bucket_size: int,
        burst_limit: Optional[int] = None
    ):
        self.tokens_per_second = tokens_per_second
        self.bucket_size: int = int(bucket_size)
        self.burst_limit: int = int(burst_limit) if burst_limit is not None else self.bucket_size
        self.tokens: int = self.bucket_size
        self.last_update = time()
        self.lock = Lock()
        self.usage_metrics: Dict[str, int] = {
            "total_consumed": 0,
            "burst_limit_hits": 0,
            "rate_limit_hits": 0
        }

    def consume(self, tokens: int, burst: bool = False) -> bool:
        """Try to consume tokens from the bucket with burst handling."""
        with self.lock:
            now = time()
            time_passed = now - self.last_update

            # Calculate new tokens, handling float to int conversion
            tokens_to_add: float = time_passed * self.tokens_per_second
            new_tokens: int = int(tokens_to_add)
            current_tokens: int = self.tokens + new_tokens
            max_tokens: int = self.bucket_size
            self.tokens = min(max_tokens, current_tokens)
            self.last_update = now

            # Check burst limit
            effective_limit = self.burst_limit if burst else self.bucket_size
            if self.tokens >= tokens and tokens <= effective_limit:
                self.tokens -= tokens
                self.usage_metrics["total_consumed"] += tokens
                return True

            # Track rate limiting events
            if self.tokens < tokens:
                self.usage_metrics["rate_limit_hits"] += 1
            elif tokens > effective_limit:
                self.usage_metrics["burst_limit_hits"] += 1

            return False

    async def wait_for_tokens(
        self,
        tokens: int,
        timeout: Optional[float] = None,
        burst: bool = False
    ) -> bool:
        """Wait until tokens are available or timeout occurs."""
        start_time = time()
        while True:
            if self.consume(tokens, burst=burst):
                return True

            if timeout and (time() - start_time) > timeout:
                logger.warning(f"Token bucket wait timeout after {timeout}s")
                return False

            await asyncio.sleep(0.1)

    def get_metrics(self) -> Dict[str, int]:
        """Get usage metrics for monitoring."""
        with self.lock:
            return dict(self.usage_metrics)

    def reset_metrics(self) -> None:
        """Reset usage metrics."""
        with self.lock:
            self.usage_metrics = {
                "total_consumed": 0,
                "burst_limit_hits": 0,
                "rate_limit_hits": 0
            }
