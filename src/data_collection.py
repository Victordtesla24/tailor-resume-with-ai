"""Data collection with enhanced privacy."""

import json
import logging
import re
from datetime import datetime
from typing import Any, Dict

from src.utils import get_secure_storage_path

logger = logging.getLogger("resume_tailor")


class DataCollector:
    """Handles data collection with privacy focus."""

    def __init__(self, filename: str):
        """Initialize data collector with storage path."""
        self.storage_path = get_secure_storage_path() / filename
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.output_file = str(self.storage_path)

    def anonymize_text(self, text: str) -> str:
        """Anonymize text by removing PII and truncating."""
        # Remove common PII patterns
        patterns = [
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # emails
            r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",  # phone numbers
            r"\b\d{3}[-.]?\d{2}[-.]?\d{4}\b",  # SSN-like
            r"\b[A-Z]{2}\d{6,8}\b",  # passport-like
        ]

        for pattern in patterns:
            text = re.sub(pattern, "[REDACTED]", text)

        # Only keep first 300 chars of each section
        return text[:300] + ("..." if len(text) > 300 else "")

    def save_data(self, data: Dict[str, Any]) -> None:
        """Save anonymized data securely."""
        try:
            # Anonymize sensitive fields
            safe_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "resume_excerpt": self.anonymize_text(data.get("resume_text", "")),
                "job_desc_excerpt": self.anonymize_text(data.get("job_description", "")),
                "sections": data.get("sections", []),
                "model": data.get("model", ""),
                "success": data.get("success", False),
            }

            # Add to storage file
            with open(self.storage_path, "a", encoding="utf-8") as f:
                json.dump(safe_data, f)
                f.write("\n")

        except (OSError, IOError) as e:
            logger.error("Failed to save training data: %s", str(e))
            # Don't raise - data collection should never break main flow

    def save_training_data(
        self, resume_text: str, job_description: str, tailored_text: str, metadata: dict
    ) -> None:
        """Save anonymized training data."""
        from src.utils import anonymize_data

        # Anonymize sensitive data
        anon_resume = anonymize_data(resume_text)
        anon_job = anonymize_data(job_description)
        anon_tailored = anonymize_data(tailored_text)

        # Create training example
        data = {
            "resume": anon_resume[:1000],  # Limit size
            "job_description": anon_job[:1000],
            "tailored_output": anon_tailored[:1000],
            "metadata": metadata,
        }

        # Append to file
        with open(self.output_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(data) + "\n")
