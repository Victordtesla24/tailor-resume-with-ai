import json
import logging
import re
from typing import Dict, Any, Optional, Set
from pathlib import Path
from datetime import datetime
from src.exceptions import DataCollectionError
import spacy  # type: ignore
from time import time

# Setup logging
logger = logging.getLogger(__name__)


class PIIData:
    """Container for PII data found in text."""
    def __init__(self) -> None:
        self.names: Set[str] = set()
        self.emails: Set[str] = set()
        self.phones: Set[str] = set()
        self.locations: Set[str] = set()
        self.organizations: Set[str] = set()
        self.dates: Set[str] = set()


class PIIDetector:
    """Detects PII in text using spaCy."""
    def __init__(self):
        try:
            self.nlp = spacy.load('en_core_web_sm')
        except OSError:
            import subprocess
            subprocess.run([
                "python", "-m", "spacy", "download", "en_core_web_sm"
            ], check=True)
            self.nlp = spacy.load('en_core_web_sm')

    def _extract_dates(self, text: str) -> Set[str]:
        """Extract dates from text using spaCy and regex."""
        dates = set()
        doc = self.nlp(text)
        
        # Extract dates from spaCy entities
        for ent in doc.ents:
            if ent.label_ == 'DATE':
                # Split compound dates into individual parts
                date_parts = ent.text.split(" to ")
                for part in date_parts:
                    dates.add(part.strip())
                dates.add(ent.text)  # Also keep the full date range
                
        # Additional regex patterns for dates
        date_patterns = [
            r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{4}\b',
            r'\b\d{4}\b',  # Year
            r'\b\d{1,2}/\d{1,2}/\d{2,4}\b',  # MM/DD/YYYY
            r'\b\d{1,2}-\d{1,2}-\d{2,4}\b'  # MM-DD-YYYY
        ]

        for pattern in date_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                dates.add(match.group())

        return dates

    def detect(self, text: str) -> PIIData:
        """Detect PII in text."""
        pii = PIIData()
        if not text.strip():
            return pii

        doc = self.nlp(text)
        for ent in doc.ents:
            if ent.label_ == 'PERSON':
                pii.names.add(ent.text)
            elif ent.label_ == 'ORG':
                pii.organizations.add(ent.text)
            elif ent.label_ == 'GPE':
                pii.locations.add(ent.text)

        # Add dates using the dedicated method
        pii.dates.update(self._extract_dates(text))

        # Add regex patterns for emails
        pii.emails.update(re.findall(r'\b[\w\+\.-]+@[\w\.-]+\.\w+\b', text))

        # Extract phone numbers with original format preserved
        phone_patterns = [
            r'\+?\d[\d\s\(\)-\.]{8,}',  # General format
            r'\d{3}[-.]?\d{3}[-.]?\d{4}',  # US format
            r'\+\d{1,3}[\s-]?\(?\d{1,4}\)?[\s-]?\d{1,4}[\s-]?\d{1,9}'
        ]

        for pattern in phone_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                phone = match.group().strip()
                # Store original format
                pii.phones.add(phone)
                # Also store cleaned version for matching
                cleaned = re.sub(r'[\s\(\)-\.]', '', phone)
                if len(cleaned) >= 10:  # Ensure it's a valid phone number
                    pii.phones.add(cleaned)

        return pii


class Tokenizer:
    """Replaces PII with tokens."""
    def replace_pii(self, text: str, pii: PIIData) -> str:
        result = text
        # Sort by length in reverse order to handle longer matches first
        for name in sorted(pii.names, key=len, reverse=True):
            result = result.replace(name, '[NAME]')
        for email in sorted(pii.emails, key=len, reverse=True):
            result = result.replace(email, '[EMAIL]')
        for phone in sorted(pii.phones, key=len, reverse=True):
            result = result.replace(phone, '[PHONE]')
        for location in sorted(pii.locations, key=len, reverse=True):
            result = result.replace(location, '[LOCATION]')
        for org in sorted(pii.organizations, key=len, reverse=True):
            result = result.replace(org, '[ORGANIZATION]')
        for date in sorted(pii.dates, key=len, reverse=True):
            result = result.replace(date, '[DATE]')
        return result


class RateLimiter:
    """Simple rate limiting implementation."""
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: list[float] = []

    def can_access(self) -> bool:
        now = time()
        self.requests = [
            req for req in self.requests
            if now - req < self.window_seconds
        ]
        if len(self.requests) >= self.max_requests:
            return False
        self.requests.append(now)
        return True


class DataRetentionManager:
    """Manages data retention policies."""
    def __init__(self, storage_path: str):
        self.storage_path = Path(storage_path)

    def cleanup_old_data(self, days: int) -> None:
        """Remove data older than specified days."""
        if not self.storage_path.exists():
            return

        cutoff = datetime.now().timestamp() - (days * 86400)
        temp_path = self.storage_path.with_suffix('.tmp')

        try:
            with open(self.storage_path, 'r') as inf:
                # Read all valid lines first
                valid_lines = []
                for line in inf:
                    try:
                        data = json.loads(line)
                        ts = datetime.fromisoformat(
                            data.get('timestamp', '')
                        ).timestamp()
                        if ts > cutoff:
                            valid_lines.append(line)
                    except (json.JSONDecodeError, ValueError):
                        continue

            # Write valid lines to temp file
            with open(temp_path, 'w') as outf:
                outf.writelines(valid_lines)

            # Replace original with temp file
            temp_path.replace(self.storage_path)

        except Exception as e:
            if temp_path.exists():
                temp_path.unlink()
            logger.error(f"Error during data cleanup: {str(e)}")
            raise DataCollectionError(f"Failed to cleanup data: {str(e)}")


class DataCollector:
    """Data collection with anonymization for fine-tuning."""

    def __init__(self, storage_path: str = "training_data.jsonl"):
        """Initialize data collector."""
        self.storage_path = Path(storage_path)
        self.pii_detector = PIIDetector()
        self.tokenizer = Tokenizer()
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

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
            # Detect and anonymize PII
            resume_pii = self.pii_detector.detect(resume_text)
            job_pii = self.pii_detector.detect(job_description)
            output_pii = self.pii_detector.detect(tailored_output)

            anon_resume = self.tokenizer.replace_pii(resume_text, resume_pii)
            anon_job = self.tokenizer.replace_pii(job_description, job_pii)
            anon_output = self.tokenizer.replace_pii(tailored_output, output_pii)

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
                    f"Resume:\n{anon_resume}\n\n"
                    f"Job Description:\n{anon_job}"
                ),
                "resume": anon_resume,
                "job_description": anon_job,
                "completion": anon_output[:300],
                "metadata": metadata
            }

            # Append to JSONL file
            with open(self.storage_path, 'a') as f:
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

            with open(self.storage_path, 'r') as f:
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
