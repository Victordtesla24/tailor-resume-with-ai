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
            "summary": (
                r"(?i)(professional\s+)?summary|"
                r"profile|objective"
            ),
            "experience": (
                r"(?i)(experience|work|"
                r"employment|history)"
            ),
            "education": (
                r"(?i)(education|academic|"
                r"qualification)"
            ),
            "skills": (
                r"(?i)(skills|expertise|"
                r"competencies)"
            ),
            "projects": (
                r"(?i)(projects|portfolio)"
            ),
            "certifications": (
                r"(?i)(certifications|certificates)"
            ),
            "languages": (
                r"(?i)(languages|linguistic)"
            ),
            "interests": (
                r"(?i)(interests|hobbies)"
            ),
            "references": (
                r"(?i)(references|recommendations)"
            )
        }

    def _is_section_header(self, line: str, pattern: str) -> bool:
        """Check if a line matches a section header pattern."""
        pattern = pattern.replace('(?i)', '')
        line = line.strip()
        flags = re.IGNORECASE
        try:
            match = re.fullmatch(pattern, line, flags)
            return bool(match)
        except re.error:
            return False

    def identify_sections(self, text: str) -> Dict[str, str]:
        """Identify sections in text content."""
        try:
            if not text.strip():
                return {}

            sections = {}
            lines = [line.strip() for line in text.split('\n')]
            if not lines:
                return {}

            current_section = None
            current_content = []

            for line in lines:
                if not line:
                    continue

                print(f"\nChecking line: {line}")
                is_header = False

                for section, pattern in self.section_patterns.items():
                    if self._is_section_header(line, pattern):
                        msg = f"Found section header: {section}"
                        print(msg)
                        if current_section and current_content:
                            content = '\n'.join(current_content)
                            sections[current_section] = content
                        current_section = section
                        current_content = []
                        is_header = True
                        break

                if not is_header and current_section:
                    msg = f"Added content to {current_section}: {line}"
                    current_content.append(line)
                    print(msg)

            if current_section and current_content:
                content = '\n'.join(current_content)
                sections[current_section] = content

            print("\nFinal sections:")
            print(sections)
            return sections

        except Exception as e:
            logger.error("Error identifying sections: %s", str(e))
            raise ProcessingError(
                f"Failed to identify sections: {str(e)}"
            ) from e


class KeywordMatcher:
    """Simple keyword matching using regex."""

    def __init__(self):
        """Initialize keyword matcher."""
        self.skill_patterns = self._load_skill_patterns()

    def _load_skill_patterns(self) -> Dict[str, List[str]]:
        """Load common skill patterns."""
        return {
            "programming": [
                "python", "java", "javascript", "c++", "ruby", "php",
                "typescript", "golang", "rust", "scala", "python3", "py3"
            ],
            "frameworks": [
                "react", "angular", "vue", "django", "flask", "spring",
                "express", "rails", "laravel", "fastapi"
            ],
            "cloud": [
                "aws", "azure", "gcp", "cloud", "docker", "kubernetes",
                "serverless", "microservices", "devops", "ci/cd"
            ],
            "databases": [
                "sql", "mysql", "postgresql", "mongodb", "redis",
                "elasticsearch", "cassandra", "dynamodb", "oracle"
            ],
            "soft_skills": [
                "leadership", "communication", "teamwork", "analytical",
                "agile", "project management", "scrum", "problem solving"
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
            job_lower = job_description.lower()

            # Find all skills mentioned in job description
            for _, skills in self.skill_patterns.items():
                for skill in skills:
                    pattern = rf"\b{re.escape(skill)}\b"
                    if re.search(pattern, job_lower):
                        has_skill = re.search(pattern, resume_lower)
                        scores[skill] = 1.0 if has_skill else 0.0

            # Add architecture as a special case
            arch_pattern = r"\b(architect|architecture)\b"
            if re.search(arch_pattern, job_lower):
                has_arch = re.search(arch_pattern, resume_lower)
                scores["Architecture"] = 1.0 if has_arch else 0.0

            return scores

        except Exception as e:
            logger.error("Error matching skills: %s", str(e))
            raise ProcessingError(
                f"Failed to match skills: {str(e)}"
            ) from e


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
            if not text or not text.strip():
                return {
                    "technical": set(),
                    "soft": set(),
                    "domain": set(),
                    "tools": set()
                }

            text_lower = text.lower()
            results = {
                "technical": set(),
                "soft": set(),
                "domain": set(),
                "tools": set()
            }

            # Extract skills by category
            for category, patterns in self.matcher.skill_patterns.items():
                for pattern in patterns:
                    # Use word boundaries for exact matches
                    pattern_re = rf"\b{re.escape(pattern)}\b"
                    if re.search(pattern_re, text_lower):
                        if category == "soft_skills":
                            results["soft"].add(pattern)
                        elif category in {
                            "programming",
                            "frameworks",
                            "cloud",
                            "databases"
                        }:
                            results["technical"].add(pattern)
                        else:
                            results["tools"].add(pattern)

            # Add Python variations
            python_patterns = [
                r"\bpython\d*\b",
                r"\bpy\d+\b",
                r"\.py\b",
                r"\bdjango\b",
                r"\bflask\b",
                r"\bfastapi\b"
            ]
            if any(re.search(p, text_lower) for p in python_patterns):
                results["technical"].add("python")

            # Domain expertise detection
            domain_patterns = [
                r"\bindustry\b",
                r"\bdomain\b",
                r"\bsector\b",
                r"\bexpertise\b",
                r"\bspecialization\b"
            ]
            if any(re.search(p, text_lower) for p in domain_patterns):
                results["domain"].add("domain expertise")

            # Tool detection
            tool_patterns = [
                r"\btool\b",
                r"\bplatform\b",
                r"\bsoftware\b",
                r"\bsuite\b",
                r"\bsystem\b"
            ]
            if any(re.search(p, text_lower) for p in tool_patterns):
                results["tools"].add("tools")

            return results

        except Exception as e:
            logger.error("Error extracting skills: %s", str(e))
            raise ProcessingError(
                f"Failed to extract skills: {str(e)}"
            ) from e
