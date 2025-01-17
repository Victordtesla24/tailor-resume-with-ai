"""Configuration Management for Resume Tailoring App."""

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Union

import keyring  # type: ignore

from .utils import RateLimiter

logger = logging.getLogger("resume_tailor")
logger.setLevel(logging.WARNING)


class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded."""

    pass


@dataclass
class APIConfig:
    """API configuration settings."""

    service_name: str
    key_name: str
    rate_limit: int
    window_seconds: int


class KeyringManager:
    """Secure API key management using system keyring."""

    def __init__(self):
        self.app_name = "resume_tailor"

    def store_key(self, service: str, api_key: str) -> None:
        """Store API key in system keyring."""
        try:
            keyring.set_password(self.app_name, service, api_key)
            logger.debug(f"Stored API key for {service}")
        except Exception as e:
            logger.error(f"Error storing API key: {str(e)}")
            raise

    def get_key(self, service: str) -> Optional[str]:
        """Retrieve API key from system keyring."""
        try:
            key = keyring.get_password(self.app_name, service)
            if not key:
                logger.warning(f"No API key found for {service}")
            return key
        except Exception as e:
            logger.error(f"Error retrieving API key: {str(e)}")
            return None

    def delete_key(self, service: str) -> None:
        """Delete API key from system keyring."""
        try:
            keyring.delete_password(self.app_name, service)
            logger.debug(f"Deleted API key for {service}")
        except Exception as e:
            logger.error(f"Error deleting API key: {str(e)}")
            raise


class Config:
    """Application configuration management."""

    def __init__(self) -> None:
        """Initialize configuration manager."""
        self.keyring: KeyringManager = KeyringManager()
        self.rate_limiters: Dict[str, "RateLimiter"] = {}

        # Default API configurations
        self.api_configs = {
            "openai": APIConfig(
                service_name="OpenAI",
                key_name="OPENAI_API_KEY",
                rate_limit=100,
                window_seconds=3600,
            ),
            "anthropic": APIConfig(
                service_name="Anthropic",
                key_name="ANTHROPIC_API_KEY",
                rate_limit=100,
                window_seconds=3600,
            ),
        }

        # Initialize rate limiters
        for service, config in self.api_configs.items():
            rpm = int(config.rate_limit / (config.window_seconds / 60))
            self.rate_limiters[service] = RateLimiter(requests_per_minute=rpm)

    def load_env_vars(self) -> None:
        """Load environment variables."""
        for config in self.api_configs.values():
            if api_key := os.getenv(config.key_name):
                self.keyring.store_key(config.service_name, api_key)

    def get(self, key: str) -> Optional[str]:
        """Get configuration value with rate limiting."""
        if key.endswith("_API_KEY"):
            service = key.replace("_API_KEY", "").lower()
            if service in self.api_configs:
                config = self.api_configs[service]
                limiter = self.rate_limiters[service]
                if not limiter.can_access():
                    msg = f"Rate limit exceeded: {config.service_name}"
                    raise RateLimitExceeded(msg)
                return self.keyring.get_key(config.service_name)
        return None

    def set(self, key: str, value: str) -> None:
        """Set configuration value."""
        if key.endswith("_API_KEY"):
            service = key.replace("_API_KEY", "").lower()
            if service in self.api_configs:
                config = self.api_configs[service]
                self.keyring.store_key(config.service_name, value)

    def delete(self, key: str) -> None:
        """Delete configuration value."""
        if key.endswith("_API_KEY"):
            service = key.replace("_API_KEY", "").lower()
            if service in self.api_configs:
                config = self.api_configs[service]
                self.keyring.delete_key(config.service_name)


def load_config(config_path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    """Load configuration from file."""
    if not config_path:
        base_dir = os.path.dirname(__file__)
        config_path = os.path.join(base_dir, "..", "config.json")

    path = Path(config_path)
    if not path.exists():
        return {}

    try:
        with open(path) as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading config: {str(e)}")
        return {}


def save_config(config: Dict[str, Any], config_path: Optional[Union[str, Path]] = None) -> None:
    """Save configuration to file."""
    if not config_path:
        config_path = os.path.join(os.path.dirname(__file__), "..", "config.json")

    path = Path(config_path)
    try:
        with open(path, "w") as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving config: {str(e)}")
        raise
