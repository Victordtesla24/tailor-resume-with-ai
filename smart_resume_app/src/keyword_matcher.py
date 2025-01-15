"""Keyword matching and skill extraction functionality."""
import logging
import re
from typing import Dict, List, Set
from src.exceptions import ProcessingError

# Setup logging
logger = logging.getLogger(__name__)


class SectionDetector:
    """Simple section detector using regex patterns."""

    def __init__(self):
        """Initialize section detector."""
        self.section_patterns = {
            "summary": r"(?i)(summary|profile|objective)",
            "experience": r"(?i)(experience|work|employment|history)",
            "education": r"(?i)(education|academic|qualification)",
            "skills": r"(?i)(skills|expertise|competencies)",
            "projects": r"(?i)(projects|portfolio)",
            "certifications": r"(?i)(certifications|certificates)",
            "languages": r"(?i)(languages|linguistic)",
            "interests": r"(?i)(interests|hobbies)",
            "references": r"(?i)(references|recommendations)"
        }

    def identify_sections(self, doc) -> Dict[str, List[int]]:
        """Identify sections in a Word document."""
        try:
            sections = {}
            current_section = None
            section_start = 0

            for idx, para in enumerate(doc.paragraphs):
                text = para.text.strip()
                if not text:
                    continue

                # Check if paragraph is a section header
                for section, pattern in self.section_patterns.items():
                    if re.search(pattern, text):
                        # Save previous section if exists
                        if current_section:
                            sections[current_section] = list(
                                range(section_start, idx)
                            )
                        current_section = section
                        section_start = idx + 1
                        break

            # Save final section
            if current_section:
                sections[current_section] = list(
                    range(section_start, len(doc.paragraphs))
                )

            return sections

        except Exception as e:
            logger.error(f"Error identifying sections: {str(e)}")
            raise ProcessingError(f"Failed to identify sections: {str(e)}")


class KeywordMatcher:
    """Simple keyword matching using regex."""

    def __init__(self):
        """Initialize keyword matcher."""
        self.skill_patterns = self._load_skill_patterns()

    def _load_skill_patterns(self) -> Dict[str, List[str]]:
        """Load common skill patterns."""
        return {
            "programming": [
                "python", "java", "javascript", "c++",
                "ruby", "php", "typescript", "golang",
                "rust", "scala"
            ],
            "frameworks": [
                "react", "angular", "vue", "django",
                "flask", "spring", "express", "rails",
                "laravel", "fastapi"
            ],
            "cloud": [
                "aws", "azure", "gcp", "cloud",
                "docker", "kubernetes", "serverless",
                "microservices", "devops", "ci/cd"
            ],
            "databases": [
                "sql", "mysql", "postgresql",
                "mongodb", "redis", "elasticsearch",
                "cassandra", "dynamodb", "oracle"
            ],
            "soft_skills": [
                "leadership", "communication",
                "teamwork", "analytical", "agile",
                "project management", "scrum",
                "problem solving"
            ]
        }

    def match_skills(
        self,
        resume_text: str,
        job_description: str
    ) -> Dict[str, float]:
        """Match skills between resume and job description."""
        try:
            scores = {}
            resume_lower = resume_text.lower()

            # Find all skills mentioned in job description
            for category, skills in self.skill_patterns.items():
                for skill in skills:
                    if skill in job_description.lower():
                        # Calculate match score
                        # 1.0 if found in resume, 0.0 if not
                        scores[skill] = 1.0 if skill in resume_lower else 0.0

            return scores

        except Exception as e:
            logger.error(f"Error matching skills: {str(e)}")
            raise ProcessingError(f"Failed to match skills: {str(e)}")


class SkillExtractor:
    """Simple skill extraction using regex patterns."""

    def __init__(self):
        """Initialize skill extractor."""
        self.matcher = KeywordMatcher()
        self.categories = {
            "technical": set(),
            "soft": set(),
            "domain": set(),
            "tools": set()
        }

    def extract_skills(self, text: str) -> Dict[str, Set[str]]:
        """Extract and categorize skills from text."""
        try:
            text_lower = text.lower()

            # Extract skills by category
            for category, patterns in self.matcher.skill_patterns.items():
                for pattern in patterns:
                    if pattern in text_lower:
                        if category == "soft_skills":
                            self.categories["soft"].add(pattern)
                        else:
                            self.categories["technical"].add(pattern)

            # Look for domain and tool keywords
            if re.search(r"\b(industry|domain|sector)\b", text_lower):
                self.categories["domain"].add("domain expertise")
            if re.search(r"\b(tool|platform|software)\b", text_lower):
                self.categories["tools"].add("tools")

            return self.categories

        except Exception as e:
            logger.error(f"Error extracting skills: {str(e)}")
            raise ProcessingError(f"Failed to extract skills: {str(e)}")
