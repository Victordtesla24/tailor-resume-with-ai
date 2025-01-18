import re
from datetime import datetime
from typing import Dict, Set, Tuple, Union

from .types import SkillMetrics


class SkillAnalyzer:
    """Analyzes and tracks skill levels and experience."""
    def __init__(self) -> None:
        self.skill_metrics: SkillMetrics = {}

    def analyze_skill_level(self, skill: str, context: str) -> float:
        """Analyze skill level based on context and experience."""
        # Extract temporal information and experience level
        skill_info = {
            "mentions": context.lower().count(skill.lower()),
            "recent": any(term in context.lower() for term in ["current", "recent", "ongoing"]),
            "years": self._extract_years_experience(context, skill)
        }

        # Calculate weighted score
        base_score = min(skill_info["mentions"] * 0.2, 1.0)
        temporal_bonus = 0.3 if skill_info["recent"] else 0
        experience_score = min(skill_info["years"] * 0.1, 0.5)

        return min(base_score + temporal_bonus + experience_score, 1.0)

    def _extract_years_experience(self, context: str, skill: str) -> float:
        """Extract years of experience for a skill from context."""
        # Simple pattern matching for years/months
        patterns = [
            rf"(\d+)\s*(?:year|yr)s?\s*(?:of)?\s*(?:experience)?"
            rf"\s*(?:with|in)?\s*{skill}",
            rf"{skill}.*?(\d+)\s*(?:year|yr)s?",
        ]
        for pattern in patterns:
            if match := re.search(pattern, context.lower()):
                return float(match.group(1))
        return 0.0

    def verify_industry_terminology(
        self,
        content: str,
        industry_terms: Set[str]
    ) -> Tuple[float, Set[str]]:
        """Verify industry-specific terminology usage."""
        found_terms = {term for term in industry_terms if term.lower() in content.lower()}
        accuracy = len(found_terms) / len(industry_terms) if industry_terms else 0.0
        return accuracy, found_terms

    def update_skill_metrics(self, skill: str, context: str) -> None:
        """Update skill metrics with new analysis."""
        self.skill_metrics[skill] = {
            "level": self.analyze_skill_level(skill, context),
            "last_used": datetime.now()  # Update when skill is mentioned
        }

    def get_skill_metrics(self, skill: str) -> Dict[str, Union[float, datetime]]:
        """Get metrics for a specific skill."""
        return self.skill_metrics.get(skill, {"level": 0.0, "last_used": datetime.min})
