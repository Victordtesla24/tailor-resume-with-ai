"""Configuration management for the Resume Tailoring Application"""
import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv


class Config:
    """Configuration class for managing application settings."""

    def __init__(self):
        """Initialize configuration with environment variables."""
        load_dotenv()
        self.config: Dict[str, Any] = {
            'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY'),
            'ANTHROPIC_API_KEY': os.getenv('ANTHROPIC_API_KEY'),
            'DEBUG': os.getenv('DEBUG', 'False').lower() == 'true',
            'LOG_LEVEL': os.getenv('LOG_LEVEL', 'INFO'),
            'MAX_TOKENS': int(os.getenv('MAX_TOKENS', '2000')),
            'TEMPERATURE': float(os.getenv('TEMPERATURE', '0.7')),
        }

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key."""
        return self.config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set configuration value."""
        self.config[key] = value


def load_config() -> Config:
    """Load and return application configuration."""
    return Config()
