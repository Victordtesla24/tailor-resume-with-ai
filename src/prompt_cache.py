import hashlib
import json
import logging
from typing import Dict, Optional, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass


logger = logging.getLogger("resume_tailor")


@dataclass
class CacheEntry:
    """Represents a cached prompt response with metadata."""
    response: str
    timestamp: datetime
    model: str
    tokens: int
    cost: float


class PromptCache:
    """Manages caching of common prompts for cost optimization."""

    def __init__(self, cache_duration: int = 24, max_entries: int = 1000) -> None:
        """
        Initialize the prompt cache.

        Args:
            cache_duration: Cache duration in hours
            max_entries: Maximum number of entries to store
        """
        self.cache: Dict[str, CacheEntry] = {}
        self.cache_duration = timedelta(hours=cache_duration)
        self.max_entries = max_entries
        self.hits = 0
        self.misses = 0
        self.total_cost_saved = 0.0

    def _generate_key(
        self,
        prompt: str,
        model: str,
        params: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate a unique cache key for a prompt-model combination."""
        content = {
            "prompt": prompt,
            "model": model,
            "params": params or {}
        }
        return hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()

    def _calculate_cost(self, tokens: int, model: str) -> float:
        """Calculate cost for token usage based on model."""
        # Cost per 1K tokens (based on user.log pricing)
        costs = {
            "gpt-4": 0.00250,  # Input tokens
            "gpt-4-output": 0.01000,  # Output tokens
            "o1-mini": 0.0030,  # Input tokens
            "o1-mini-output": 0.0120,  # Output tokens
            "o1-preview": 0.00250,  # Input tokens
            "o1-preview-output": 0.01000  # Output tokens
        }
        base_cost = costs.get(model, 0.00250)  # Default to gpt-4 pricing
        return (tokens / 1000) * base_cost

    def get(
        self,
        prompt: str,
        model: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Optional[CacheEntry]:
        """
        Retrieve cached response if available and not expired.

        Args:
            prompt: The prompt to look up
            model: The model used for generation
            params: Additional parameters that affect the response

        Returns:
            CacheEntry if found and valid, None otherwise
        """
        key = self._generate_key(prompt, model, params)
        if key in self.cache:
            entry = self.cache[key]
            if datetime.now() - entry.timestamp < self.cache_duration:
                self.hits += 1
                # Update cost savings
                self.total_cost_saved += self._calculate_cost(entry.tokens, model)
                return entry
            else:
                del self.cache[key]
        self.misses += 1
        return None

    def set(
        self,
        prompt: str,
        model: str,
        response: str,
        tokens: int,
        params: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Cache a prompt response.

        Args:
            prompt: The original prompt
            model: The model used for generation
            response: The generated response
            tokens: Number of tokens used
            params: Additional parameters that affected the response
        """
        key = self._generate_key(prompt, model, params)

        # Implement LRU-style eviction if cache is full
        if len(self.cache) >= self.max_entries:
            oldest_key = min(self.cache.items(), key=lambda x: x[1].timestamp)[0]
            del self.cache[oldest_key]

        self.cache[key] = CacheEntry(
            response=response,
            timestamp=datetime.now(),
            model=model,
            tokens=tokens,
            cost=self._calculate_cost(tokens, model)
        )

    def get_metrics(self) -> Dict[str, Union[int, float]]:
        """Get cache performance metrics."""
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests) if total_requests > 0 else 0

        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate,
            "total_entries": len(self.cache),
            "total_cost_saved": self.total_cost_saved
        }

    def clear_expired(self) -> int:
        """
        Clear expired entries from cache.

        Returns:
            Number of entries cleared
        """
        now = datetime.now()
        expired_keys = [
            key for key, entry in self.cache.items()
            if now - entry.timestamp >= self.cache_duration
        ]

        for key in expired_keys:
            del self.cache[key]

        return len(expired_keys)
