"""Utility functions for the Resume Tailoring Application"""
import logging
from typing import Dict, Any
import os


def setup_logging() -> logging.Logger:
    """Set up and configure logging."""
    logger = logging.getLogger('resume_tailor')
    
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        log_level = os.getenv('LOG_LEVEL', 'INFO')
        logger.setLevel(getattr(logging, log_level))
        
        # Add file handler for error logging
        error_handler = logging.FileHandler('api_errors.log')
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        logger.addHandler(error_handler)
    
    return logger


def validate_input(data: Dict[str, Any]) -> bool:
    """Validate input data for resume processing."""
    required_fields = ['resume', 'job_description']
    
    if not all(field in data for field in required_fields):
        return False
    
    if not isinstance(data['resume'], str) or not data['resume'].strip():
        return False
    
    if not isinstance(data['job_description'], str) or \
            not data['job_description'].strip():
        return False
    
    if 'model' in data and not isinstance(data['model'], str):
        return False
    
    return True


def sanitize_input(text: str) -> str:
    """Sanitize input text."""
    # Remove potentially harmful characters
    text = ''.join(char for char in text if ord(char) < 128)
    
    # Basic XSS prevention
    text = text.replace('<', '&lt;').replace('>', '&gt;')
    
    return text.strip()
