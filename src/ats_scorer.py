"""ATS scoring and keyword analysis for resumes."""

import re
from typing import Dict, List, Set, Tuple

from src.keyword_matcher import KeywordMatcher


class ATSScorer:
    """Analyzes and scores resumes based on ATS criteria."""

    def __init__(self) -> None:
        """Initialize ATS scorer."""
        self.keyword_matcher = KeywordMatcher()
        self.hard_skills_weight = 0.4
        self.soft_skills_weight = 0.2
        self.experience_weight = 0.2
        self.education_weight = 0.1
        self.format_weight = 0.1

    def calculate_score(
        self,
        resume_text: str,
        job_description: str
    ) -> Tuple[float, Dict[str, float], List[str]]:
        """Calculate ATS match score and provide improvement suggestions.

        Args:
            resume_text: The complete resume text
            job_description: The target job description

        Returns:
            Tuple containing:
            - Overall score (0-100)
            - Dictionary of component scores
            - List of improvement suggestions
        """
        scores: Dict[str, float] = {}
        suggestions: List[str] = []

        # Calculate keyword match scores
        hard_skills_score = self._calculate_hard_skills_score(
            resume_text, job_description
        )
        scores["hard_skills"] = hard_skills_score

        soft_skills_score = self._calculate_soft_skills_score(
            resume_text, job_description
        )
        scores["soft_skills"] = soft_skills_score

        # Calculate experience match
        experience_score = self._calculate_experience_score(
            resume_text, job_description
        )
        scores["experience"] = experience_score

        # Calculate education match
        education_score = self._calculate_education_score(
            resume_text, job_description
        )
        scores["education"] = education_score

        # Calculate format score
        format_score = self._calculate_format_score(resume_text)
        scores["format"] = format_score

        # Calculate weighted overall score
        overall_score = (
            hard_skills_score * self.hard_skills_weight +
            soft_skills_score * self.soft_skills_weight +
            experience_score * self.experience_weight +
            education_score * self.education_weight +
            format_score * self.format_weight
        ) * 100

        # Generate improvement suggestions
        if hard_skills_score < 0.7:
            missing_skills = self._get_missing_hard_skills(
                resume_text, job_description
            )
            if missing_skills:
                suggestions.append(
                    f"Add these technical skills: {', '.join(missing_skills)}"
                )

        if soft_skills_score < 0.7:
            missing_soft_skills = self._get_missing_soft_skills(
                resume_text, job_description
            )
            if missing_soft_skills:
                suggestions.append(
                    f"Add these soft skills: {', '.join(missing_soft_skills)}"
                )

        if format_score < 0.8:
            suggestions.extend(self._get_format_suggestions(resume_text))

        return overall_score, scores, suggestions

    def _calculate_hard_skills_score(
        self,
        resume_text: str,
        job_description: str
    ) -> float:
        """Calculate technical skills match score."""
        job_skills = self.keyword_matcher.extract_keywords(
            job_description
        ).get("technical", set())
        resume_skills = self.keyword_matcher.extract_keywords(
            resume_text
        ).get("technical", set())

        if not job_skills:
            return 1.0

        matches = len(job_skills & resume_skills)
        return matches / len(job_skills)

    def _calculate_soft_skills_score(
        self,
        resume_text: str,
        job_description: str
    ) -> float:
        """Calculate soft skills match score."""
        job_skills = self.keyword_matcher.extract_keywords(
            job_description
        ).get("soft_skills", set())
        resume_skills = self.keyword_matcher.extract_keywords(
            resume_text
        ).get("soft_skills", set())

        if not job_skills:
            return 1.0

        matches = len(job_skills & resume_skills)
        return matches / len(job_skills)

    def _calculate_experience_score(
        self,
        resume_text: str,
        job_description: str
    ) -> float:
        """Calculate experience match score."""
        # Extract years of experience from job description
        years_required = self._extract_years_required(job_description)
        if not years_required:
            return 1.0

        # Extract years from resume
        years_experience = self._extract_years_experience(resume_text)

        if years_experience >= years_required:
            return 1.0
        elif years_experience >= years_required * 0.8:
            return 0.8
        elif years_experience >= years_required * 0.6:
            return 0.6
        else:
            return 0.4

    def _calculate_education_score(
        self,
        resume_text: str,
        job_description: str
    ) -> float:
        """Calculate education match score."""
        required_degrees = self._extract_required_degrees(job_description)
        if not required_degrees:
            return 1.0

        resume_degrees = self._extract_degrees(resume_text)
        matches = len(required_degrees & resume_degrees)
        return matches / len(required_degrees)

    def _calculate_format_score(self, resume_text: str) -> float:
        """Calculate resume format score."""
        score = 1.0
        deductions: List[float] = []

        # Check for proper section headers
        if not re.search(r'\b(EXPERIENCE|WORK|EMPLOYMENT)\b', resume_text, re.I):
            deductions.append(0.1)
        if not re.search(r'\b(EDUCATION|QUALIFICATIONS)\b', resume_text, re.I):
            deductions.append(0.1)
        if not re.search(r'\b(SKILLS|COMPETENCIES)\b', resume_text, re.I):
            deductions.append(0.1)

        # Check for proper contact information
        if not re.search(r'[\w\.-]+@[\w\.-]+\.\w+', resume_text):  # email
            deductions.append(0.1)
        if not re.search(r'\b\d{10}\b|\(\d{3}\)\s*\d{3}[-\s]?\d{4}', resume_text):  # phone
            deductions.append(0.1)

        return max(0.0, score - sum(deductions))

    def _extract_years_required(self, text: str) -> int:
        """Extract required years of experience from text."""
        patterns = [
            r'(\d+)\+?\s*(?:years|yrs)(?:\s+of)?\s+experience',
            r'minimum\s+of\s+(\d+)\s+(?:years|yrs)',
            r'at\s+least\s+(\d+)\s+(?:years|yrs)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.I)
            if match:
                return int(match.group(1))
        return 0

    def _extract_years_experience(self, text: str) -> int:
        """Extract years of experience from resume text."""
        # Look for date ranges in experience section
        experience_section = re.search(
            r'(?:EXPERIENCE|WORK|EMPLOYMENT).*?(?:EDUCATION|SKILLS|\Z)',
            text,
            re.I | re.S
        )
        if not experience_section:
            return 0

        # Extract all years
        years_str = re.findall(r'\b20\d{2}\b', experience_section.group(0))
        if len(years_str) >= 2:
            years = [int(y) for y in years_str]
            return max(years) - min(years)
        return 0

    def _extract_required_degrees(self, text: str) -> Set[str]:
        """Extract required degrees from job description."""
        degrees: Set[str] = set()
        patterns = [
            r"(?:requires|required|must have|minimum)(?:[^.]*?)"
            r"(?:degree|qualification)(?:[^.]*?)"
            r"(?:in|of)([^.]*)",
            r"(?:bachelor'?s?|master'?s?|phd|doctorate)(?:[^.]*?)"
            r"(?:in|of)([^.]*)",
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, text, re.I)
            for match in matches:
                degree = match.group(1).strip().lower()
                degrees.add(degree)

        return degrees

    def _extract_degrees(self, text: str) -> Set[str]:
        """Extract degrees from resume text."""
        degrees: Set[str] = set()
        education_section = re.search(
            r'(?:EDUCATION|QUALIFICATIONS).*?(?:EXPERIENCE|SKILLS|\Z)',
            text,
            re.I | re.S
        )
        if not education_section:
            return degrees

        # Look for degree names
        patterns = [
            r"(?:bachelor'?s?|master'?s?|phd|doctorate)(?:[^.]*?)"
            r"(?:in|of)([^.]*)",
            r"(?:b\.?s\.?|m\.?s\.?|ph\.?d\.?)(?:[^.]*?)"
            r"(?:in|of)([^.]*)",
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, education_section.group(0), re.I)
            for match in matches:
                degree = match.group(1).strip().lower()
                degrees.add(degree)

        return degrees

    def _get_missing_hard_skills(
        self,
        resume_text: str,
        job_description: str
    ) -> Set[str]:
        """Get missing technical skills."""
        job_skills = self.keyword_matcher.extract_keywords(
            job_description
        ).get("technical", set())
        resume_skills = self.keyword_matcher.extract_keywords(
            resume_text
        ).get("technical", set())
        return job_skills - resume_skills

    def _get_missing_soft_skills(
        self,
        resume_text: str,
        job_description: str
    ) -> Set[str]:
        """Get missing soft skills."""
        job_skills = self.keyword_matcher.extract_keywords(
            job_description
        ).get("soft_skills", set())
        resume_skills = self.keyword_matcher.extract_keywords(
            resume_text
        ).get("soft_skills", set())
        return job_skills - resume_skills

    def _get_format_suggestions(self, resume_text: str) -> List[str]:
        """Get formatting improvement suggestions."""
        suggestions: List[str] = []

        if not re.search(r'\b(EXPERIENCE|WORK|EMPLOYMENT)\b', resume_text, re.I):
            suggestions.append("Add a clear EXPERIENCE section header")
        if not re.search(r'\b(EDUCATION|QUALIFICATIONS)\b', resume_text, re.I):
            suggestions.append("Add a clear EDUCATION section header")
        if not re.search(r'\b(SKILLS|COMPETENCIES)\b', resume_text, re.I):
            suggestions.append("Add a clear SKILLS section header")
        if not re.search(r'[\w\.-]+@[\w\.-]+\.\w+', resume_text):
            suggestions.append("Add your email address")
        if not re.search(r'\b\d{10}\b|\(\d{3}\)\s*\d{3}[-\s]?\d{4}', resume_text):
            suggestions.append("Add your phone number")

        return suggestions
