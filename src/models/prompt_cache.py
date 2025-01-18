import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List, cast
from pathlib import Path

logger = logging.getLogger("resume_tailor")


class PromptCache:
    """Caches and manages common prompts and their responses."""
    def __init__(self, cache_dir: str = "cache/model_responses"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.memory_cache: Dict[str, Dict[str, Any]] = {}
        self.max_age = timedelta(hours=24)  # Cache entries expire after 24 hours

    def _get_cache_key(self, model: str, prompt: str) -> str:
        """Generate a unique cache key for the model and prompt combination."""
        import hashlib
        # Create a unique key based on model and prompt
        combined = f"{model}:{prompt}"
        return hashlib.sha256(combined.encode()).hexdigest()

    def _get_cache_path(self, cache_key: str) -> Path:
        """Get the file path for a cache entry."""
        return self.cache_dir / f"{cache_key}.json"

    def get_cached_response(
        self,
        model: str,
        prompt: str,
        max_age: Optional[timedelta] = None
    ) -> Optional[str]:
        """Get a cached response if available and not expired."""
        cache_key = self._get_cache_key(model, prompt)

        # Check memory cache first
        if cache_key in self.memory_cache:
            entry = self.memory_cache[cache_key]
            if datetime.now() - cast(datetime, entry["timestamp"]) <= (max_age or self.max_age):
                return cast(str, entry["response"])
            del self.memory_cache[cache_key]

        # Check file cache
        cache_path = self._get_cache_path(cache_key)
        if cache_path.exists():
            try:
                with cache_path.open("r") as f:
                    entry = json.load(f)
                    timestamp = datetime.fromisoformat(entry["timestamp"])
                    if datetime.now() - timestamp <= (max_age or self.max_age):
                        # Add to memory cache
                        self.memory_cache[cache_key] = {
                            "response": entry["response"],
                            "timestamp": timestamp
                        }
                        return cast(str, entry["response"])
                # Remove expired cache file
                cache_path.unlink()
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                logger.warning(f"Error reading cache file {cache_path}: {e}")
                if cache_path.exists():
                    cache_path.unlink()

        return None

    def cache_response(
        self,
        model: str,
        prompt: str,
        response: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Cache a response with optional metadata."""
        cache_key = self._get_cache_key(model, prompt)
        timestamp = datetime.now()

        # Update memory cache
        self.memory_cache[cache_key] = {
            "response": response,
            "timestamp": timestamp
        }

        # Update file cache
        cache_entry = {
            "model": model,
            "prompt": prompt,
            "response": response,
            "timestamp": timestamp.isoformat(),
            "metadata": metadata or {}
        }

        cache_path = self._get_cache_path(cache_key)
        try:
            with cache_path.open("w") as f:
                json.dump(cache_entry, f, indent=2)
        except Exception as e:
            logger.error(f"Error writing cache file {cache_path}: {e}")

    def clear_expired_cache(self) -> None:
        """Clear expired cache entries from both memory and file cache."""
        now = datetime.now()

        # Clear memory cache
        expired_keys = [
            key for key, entry in self.memory_cache.items()
            if now - cast(datetime, entry["timestamp"]) > self.max_age
        ]
        for key in expired_keys:
            del self.memory_cache[key]

        # Clear file cache
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with cache_file.open("r") as f:
                    entry = json.load(f)
                    timestamp = datetime.fromisoformat(entry["timestamp"])
                    if now - timestamp > self.max_age:
                        cache_file.unlink()
            except (json.JSONDecodeError, KeyError, ValueError, OSError) as e:
                logger.warning(f"Error processing cache file {cache_file}: {e}")
                if cache_file.exists():
                    cache_file.unlink()

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about the cache."""
        stats = {
            "memory_cache_size": len(self.memory_cache),
            "file_cache_size": len(list(self.cache_dir.glob("*.json"))),
            "cache_dir": str(self.cache_dir),
            "max_age_hours": self.max_age.total_seconds() / 3600
        }
        return stats

    def get_common_prompts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most commonly used prompts from the cache."""
        prompts: Dict[str, Dict[str, Any]] = {}

        # Analyze file cache
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with cache_file.open("r") as f:
                    entry = json.load(f)
                    prompt = entry["prompt"]
                    if prompt not in prompts:
                        prompts[prompt] = {
                            "count": 0,
                            "last_used": entry["timestamp"],
                            "models": set()
                        }
                    prompts[prompt]["count"] += 1
                    prompts[prompt]["models"].add(entry["model"])
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Error reading cache file {cache_file}: {e}")

        # Sort by count and get top N
        sorted_prompts = sorted(
            [
                {
                    "prompt": prompt,
                    "count": data["count"],
                    "last_used": data["last_used"],
                    "models": list(data["models"])
                }
                for prompt, data in prompts.items()
            ],
            key=lambda x: x["count"],
            reverse=True
        )

        return sorted_prompts[:limit]
