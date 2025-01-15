import json
import logging
import re
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime
from src.exceptions import DataCollectionError

# Setup logging
logger = logging.getLogger(__name__)


class DataCollector:
    """Data collection with anonymization for fine-tuning."""

    def __init__(self, storage_path: str = "training_data.jsonl"):
        """Initialize data collector."""
        self.storage_path = Path(storage_path)
        self.anonymizer = DataAnonymizer()

    def save_training_data(
        self,
        resume_text: str,
        job_description: str,
        tailored_output: str,
        extra_metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Store anonymized training data.

        Args:
            resume_text: Original resume text
            job_description: Original job description
            tailored_output: Generated tailored text
            extra_metadata: Additional metadata to store
        """
        try:
            # Anonymize sensitive data
            anon_resume = self.anonymizer.anonymize_text(resume_text)
            anon_job = self.anonymizer.anonymize_text(job_description)
            anon_output = self.anonymizer.anonymize_text(tailored_output)

            # Prepare metadata
            metadata = {
                "resume_length": len(resume_text),
                "job_desc_length": len(job_description),
                "output_length": len(tailored_output)
            }
            if extra_metadata:
                metadata.update(extra_metadata)

            # Prepare training example
            data = {
                "timestamp": datetime.utcnow().isoformat(),
                "prompt": (
                    f"Resume:\n{anon_resume[:300]}...\n\n"
                    f"Job Description:\n{anon_job[:300]}..."
                ),
                "completion": anon_output[:300],
                "metadata": metadata
            }

            # Append to JSONL file
            with self.storage_path.open('a') as f:
                f.write(json.dumps(data) + '\n')

            logger.info("Successfully saved training data")

        except Exception as e:
            logger.error(f"Error saving training data: {str(e)}")
            msg = f"Failed to save training data: {str(e)}"
            raise DataCollectionError(msg)

    def get_training_stats(self) -> Dict[str, Any]:
        """Get statistics about collected training data."""
        try:
            if not self.storage_path.exists():
                return {
                    "total_examples": 0,
                    "avg_resume_length": 0,
                    "avg_job_desc_length": 0,
                    "avg_output_length": 0
                }

            total = 0
            resume_lengths = []
            job_desc_lengths = []
            output_lengths = []

            with self.storage_path.open('r') as f:
                for line in f:
                    data = json.loads(line)
                    total += 1
                    metadata = data.get('metadata', {})
                    resume_lengths.append(metadata.get('resume_length', 0))
                    job_desc_lengths.append(metadata.get('job_desc_length', 0))
                    output_lengths.append(metadata.get('output_length', 0))

            return {
                "total_examples": total,
                "avg_resume_length": (
                    sum(resume_lengths) / total if total > 0 else 0
                ),
                "avg_job_desc_length": (
                    sum(job_desc_lengths) / total if total > 0 else 0
                ),
                "avg_output_length": (
                    sum(output_lengths) / total if total > 0 else 0
                )
            }

        except Exception as e:
            logger.error(f"Error getting training stats: {str(e)}")
            raise DataCollectionError(
                f"Failed to get training statistics: {str(e)}"
            )


class DataAnonymizer:
    """Text anonymization for privacy protection."""

    def __init__(self):
        """Initialize with regex patterns."""
        # Patterns for sensitive data
        self.patterns = {
            'email': r'\b[\w\.-]+@[\w\.-]+\.\w+\b',
            'phone': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            'address': r'\b\d+\s+[A-Za-z\s,]+\b',
            'name': r'(?i)(?:mr\.|mrs\.|ms\.|dr\.)\s+[a-z]+\s+[a-z]+\b',
            'url': r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[^\s]*'
        }

    def anonymize_text(self, text: str) -> str:
        """Anonymize sensitive information in text."""
        try:
            anonymized = text

            # Replace sensitive data with placeholders
            for data_type, pattern in self.patterns.items():
                anonymized = re.sub(
                    pattern,
                    f'[{data_type.upper()}]',
                    anonymized
                )

            return anonymized

        except Exception as e:
            logger.error(f"Error anonymizing text: {str(e)}")
            raise DataCollectionError(f"Failed to anonymize text: {str(e)}")

    def add_pattern(self, name: str, pattern: str) -> None:
        """Add new pattern for anonymization."""
        try:
            # Validate pattern
            re.compile(pattern)
            self.patterns[name] = pattern
            logger.info(f"Added new anonymization pattern: {name}")

        except re.error as e:
            logger.error(f"Invalid regex pattern: {str(e)}")
            raise DataCollectionError(f"Invalid regex pattern: {str(e)}")
