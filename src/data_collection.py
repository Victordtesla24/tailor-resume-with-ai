"""Data collection with enhanced privacy and quality tracking."""

import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from src.utils import get_secure_storage_path

logger = logging.getLogger("resume_tailor")


class DataValidator:
    """Validates collected data for quality and completeness."""

    @staticmethod
    def validate_section_format(section: str, content: str) -> Tuple[bool, Dict[str, bool]]:
        """Validate section formatting."""
        checks = {
            "has_header": bool(re.search(rf"^#\s+{section}", content, re.M | re.I)),
            "has_bullets": bool(re.search(r"^\s*-\s+\w+", content, re.M)),
            "has_metrics": bool(re.search(r"\d+%|\d+x|\$\d+|\d+\s*[KMB]?", content)),
            "proper_spacing": not bool(re.search(r"\n{3,}", content)),
            "markdown_format": bool(re.search(r"^#|\*\*|\-\s", content, re.M)),
        }
        return all(checks.values()), checks

    @staticmethod
    def validate_content_quality(
        content: str, job_keywords: Set[str]
    ) -> Tuple[float, Dict[str, Any]]:
        """Validate content quality and keyword usage."""
        metrics = {
            "length": len(content),
            "keyword_count": sum(1 for kw in job_keywords if kw.lower() in content.lower()),
            "bullet_points": len(re.findall(r"^\s*-\s+", content, re.M)),
            "metrics_used": len(re.findall(r"\d+%|\d+x|\$\d+|\d+\s*[KMB]?", content)),
        }

        # Calculate quality score (0-1)
        score = (
            min(1.0, metrics["length"] / 2000) * 0.3  # Length score
            + min(1.0, metrics["keyword_count"] / len(job_keywords)) * 0.3  # Keyword score
            + min(1.0, metrics["bullet_points"] / 5) * 0.2  # Format score
            + min(1.0, metrics["metrics_used"] / 3) * 0.2  # Metrics score
        )

        return score, metrics


class DataCollector:
    """Handles data collection with privacy focus and quality tracking."""

    def __init__(self, filename: str):
        """Initialize data collector with storage path."""
        self.storage_path = get_secure_storage_path() / filename
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.output_file = str(self.storage_path)
        self.validator = DataValidator()

        # Track template effectiveness
        self.template_stats_file = self.storage_path.parent / "template_stats.json"
        self._load_template_stats()

    def _load_template_stats(self) -> None:
        """Load template effectiveness statistics."""
        try:
            if self.template_stats_file.exists():
                with open(self.template_stats_file) as f:
                    self.template_stats = json.load(f)
            else:
                self.template_stats = {
                    "templates": {},
                    "section_patterns": {},
                    "prompt_patterns": {},
                }
        except Exception as e:
            logger.error("Failed to load template stats: %s", str(e))
            self.template_stats = {"templates": {}, "section_patterns": {}, "prompt_patterns": {}}

    def _update_template_stats(self, template_id: str, success: bool, quality_score: float) -> None:
        """Update template effectiveness statistics."""
        stats = self.template_stats["templates"].get(
            template_id, {"uses": 0, "successes": 0, "total_quality": 0.0}
        )

        stats["uses"] += 1
        if success:
            stats["successes"] += 1
        stats["total_quality"] += quality_score

        self.template_stats["templates"][template_id] = stats

        try:
            with open(self.template_stats_file, "w") as f:
                json.dump(self.template_stats, f, indent=2)
        except Exception as e:
            logger.error("Failed to save template stats: %s", str(e))

    def extract_job_keywords(self, job_description: str) -> Set[str]:
        """Extract relevant keywords from job description."""
        # Remove common words and get unique keywords
        common_words = {
            "the",
            "and",
            "or",
            "a",
            "an",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "from",
            "up",
            "about",
            "into",
            "over",
            "after",
        }

        words = set()
        for word in re.findall(r"\b\w+\b", job_description.lower()):
            if len(word) > 2 and word not in common_words and not word.isdigit():
                words.add(word)

        return words

    def anonymize_text(self, text: str) -> str:
        """Anonymize text by removing PII."""
        patterns = [
            (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL]"),
            (r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", "[PHONE]"),
            (r"\b\d{3}[-.]?\d{2}[-.]?\d{4}\b", "[ID]"),
            (r"\b[A-Z]{2}\d{6,8}\b", "[ID]"),
            (
                r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*"
                r"\s+\d{1,2},\s+\d{4}\b",
                "[DATE]",
            ),
            (r"\b\d{1,2}/\d{1,2}/\d{2,4}\b", "[DATE]"),
            (r"\b(?:street|st|avenue|ave|road|rd|boulevard|blvd|lane|ln|drive|dr)\b", "[ADDRESS]"),
            (r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2}\b", "[NAME]"),  # Proper names
        ]

        anonymized = text
        for pattern, replacement in patterns:
            anonymized = re.sub(pattern, replacement, anonymized, flags=re.I)

        return anonymized

    def extract_sections(self, text: str) -> Dict[str, str]:
        """Extract and validate resume sections."""
        sections: Dict[str, str] = {}
        current_section = None
        current_content: List[str] = []

        for line in text.split("\n"):
            # Detect section headers (all caps or markdown headers)
            if re.match(r"^#\s+[A-Z\s]+$", line) or line.strip().isupper():
                if current_section:
                    sections[current_section] = "\n".join(current_content).strip()
                current_section = re.sub(r"^#\s+", "", line).strip()
                current_content = []
            elif current_section:
                current_content.append(line)

        # Add last section
        if current_section:
            sections[current_section] = "\n".join(current_content).strip()

        return sections

    def save_training_data(
        self,
        resume_text: str,
        job_description: str,
        tailored_text: str,
        metadata: Dict[str, Any],
        sections: List[str],
        ats_score: float,
        *,
        section_scores: Optional[Dict[str, float]] = None,
        format_validation: Optional[Dict[str, bool]] = None,
        keyword_matches: Optional[Dict[str, int]] = None,
        template_id: Optional[str] = None,
    ) -> None:
        """Save comprehensive training data with quality metrics."""
        try:
            # Extract and validate sections
            original_sections = self.extract_sections(resume_text)
            tailored_sections = self.extract_sections(tailored_text)

            # Extract keywords for quality validation
            job_keywords = self.extract_job_keywords(job_description)

            # Validate each section
            section_validations = {}
            section_quality = {}

            for section in sections:
                if section in tailored_sections:
                    # Validate format
                    format_valid, format_checks = self.validator.validate_section_format(
                        section, tailored_sections[section]
                    )

                    # Validate content quality
                    quality_score, quality_metrics = self.validator.validate_content_quality(
                        tailored_sections[section], job_keywords
                    )

                    section_validations[section] = {
                        "format_valid": format_valid,
                        "format_checks": format_checks,
                    }

                    section_quality[section] = {
                        "quality_score": quality_score,
                        "metrics": quality_metrics,
                    }

            # Calculate overall quality score
            quality_scores = [
                (
                    float(sq["quality_score"])
                    if isinstance(sq["quality_score"], (int, float, str))
                    else 0.0
                )
                for sq in section_quality.values()
            ]
            overall_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0

            # Update template statistics if template_id provided
            if template_id:
                self._update_template_stats(
                    template_id,
                    overall_quality >= 0.7,  # Consider success if quality score >= 0.7
                    overall_quality,
                )

            # Prepare training data
            training_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "input": {
                    "resume": {
                        "full_text": self.anonymize_text(resume_text),
                        "sections": {
                            k: self.anonymize_text(v) for k, v in original_sections.items()
                        },
                    },
                    "job_description": self.anonymize_text(job_description),
                    "sections_requested": sections,
                },
                "output": {
                    "full_text": self.anonymize_text(tailored_text),
                    "sections": {k: self.anonymize_text(v) for k, v in tailored_sections.items()},
                },
                "validation": {
                    "section_validations": section_validations,
                    "section_quality": section_quality,
                    "overall_quality": overall_quality,
                    "ats_score": ats_score,
                    "section_scores": section_scores or {},
                    "keyword_matches": keyword_matches or {},
                },
                "metadata": {
                    **metadata,
                    "template_id": template_id,
                    "processing_time": metadata.get("processing_time", 0),
                    "model_confidence": metadata.get("model_confidence", 0),
                },
            }

            # Save to file
            with open(self.output_file, "a", encoding="utf-8") as f:
                json.dump(training_data, f, ensure_ascii=False)
                f.write("\n")

        except Exception as e:
            logger.error("Failed to save training data: %s", str(e))
            # Don't raise - data collection should never break main flow
