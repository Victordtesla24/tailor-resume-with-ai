"""AI-powered job recommendation engine."""

import re
from typing import Dict, List, Optional, Set, Tuple, Union

from src.keyword_matcher import KeywordMatcher


class JobRecommender:
    """Recommends jobs based on resume analysis."""

    def __init__(self) -> None:
        """Initialize job recommender."""
        self.keyword_matcher = KeywordMatcher()

        # Role mappings for career progression
        self.role_progressions = {
            "software engineer": [
                "senior software engineer",
                "lead developer",
                "software architect",
                "technical lead",
                "engineering manager"
            ],
            "data scientist": [
                "senior data scientist",
                "lead data scientist",
                "data science manager",
                "head of data",
                "chief data officer"
            ],
            "business analyst": [
                "senior business analyst",
                "lead business analyst",
                "product owner",
                "product manager",
                "program manager"
            ],
            "solution architect": [
                "senior solution architect",
                "enterprise architect",
                "chief architect",
                "technical director",
                "cto"
            ]
        }

        # Skill clusters for role matching
        self.skill_clusters = {
            "frontend": {
                "react", "angular", "vue", "javascript", "typescript",
                "html", "css", "web development", "ui", "ux"
            },
            "backend": {
                "java", "python", "c#", "node.js", "sql",
                "apis", "microservices", "spring", "django", "express"
            },
            "data": {
                "python", "r", "sql", "machine learning", "statistics",
                "tensorflow", "pytorch", "pandas", "numpy", "scikit-learn"
            },
            "devops": {
                "aws", "azure", "gcp", "docker", "kubernetes",
                "ci/cd", "jenkins", "terraform", "ansible", "linux"
            },
            "architecture": {
                "solution design", "enterprise architecture", "system design",
                "cloud architecture", "microservices", "distributed systems"
            }
        }

    def get_recommendations(
        self,
        resume_text: str,
        current_role: str,
        years_experience: int
    ) -> List[Dict[str, Union[str, float]]]:
        """Get job recommendations based on resume analysis.

        Args:
            resume_text: The complete resume text
            current_role: Current job title
            years_experience: Years of experience

        Returns:
            List of recommended job roles with explanations
        """
        recommendations = []

        # Extract skills from resume
        skills = self.keyword_matcher.extract_keywords(
            resume_text
        ).get("technical", set())

        # Find matching skill clusters
        cluster_matches = self._match_skill_clusters(skills)

        # Get career progression recommendations
        progression_matches = self._get_progression_roles(
            current_role,
            years_experience
        )

        # Create recommendations with proper types
        all_recommendations: List[Dict[str, Union[str, float]]] = []

        # Add progression-based recommendations
        for role in progression_matches:
            confidence = self._calculate_progression_confidence(role, years_experience)
            all_recommendations.append({
                "role": str(role),
                "type": "career_progression",
                "confidence": confidence,
                "reason": (
                    f"Natural career progression from {current_role} "
                    f"with {years_experience} years experience"
                )
            })

        # Add skill-based recommendations
        for cluster, score in cluster_matches:
            roles = self._get_roles_for_cluster(cluster, years_experience)
            for role in roles:
                all_recommendations.append({
                    "role": str(role),
                    "type": "skill_match",
                    "confidence": float(score),
                    "reason": (
                        f"Strong match with your {cluster} skills "
                        f"({score:.0%} alignment)"
                    )
                })

        # Sort by confidence and take top 5
        def get_confidence(x: Dict[str, Union[str, float]]) -> float:
            return float(x["confidence"])

        recommendations = sorted(
            all_recommendations,
            key=get_confidence,
            reverse=True
        )[:5]

        return recommendations

    def get_skill_gaps(
        self,
        resume_text: str,
        target_role: str
    ) -> Tuple[List[str], List[str]]:
        """Identify skill gaps for a target role.

        Args:
            resume_text: The complete resume text
            target_role: The desired job role

        Returns:
            Tuple containing:
            - List of critical missing skills
            - List of recommended skills to learn
        """
        # Extract current skills
        current_skills = self.keyword_matcher.extract_keywords(
            resume_text
        ).get("technical", set())

        # Get required skills for target role
        required_skills = self._get_required_skills(target_role)

        # Find gaps
        critical_gaps = []
        recommended_skills = []

        for skill, importance in required_skills.items():
            if skill not in current_skills:
                if importance > 0.8:
                    critical_gaps.append(skill)
                else:
                    recommended_skills.append(skill)

        return critical_gaps, recommended_skills

    def _match_skill_clusters(
        self,
        skills: Set[str]
    ) -> List[Tuple[str, float]]:
        """Match skills against predefined clusters."""
        matches = []
        for cluster, cluster_skills in self.skill_clusters.items():
            overlap = len(skills & cluster_skills)
            if overlap > 0:
                score = overlap / len(cluster_skills)
                matches.append((cluster, score))

        return sorted(matches, key=lambda x: x[1], reverse=True)

    def _get_progression_roles(
        self,
        current_role: str,
        years_experience: int
    ) -> List[str]:
        """Get potential next roles based on career progression."""
        # Find best matching role category
        best_match = None
        best_score = 0

        for base_role, progressions in self.role_progressions.items():
            if self._calculate_role_similarity(current_role, base_role) > best_score:
                best_match = base_role
                best_score = best_score

        if not best_match:
            return []

        # Get progression based on experience
        progression = self.role_progressions[best_match]
        if years_experience < 3:
            return progression[:1]  # Entry level
        elif years_experience < 5:
            return progression[:2]  # Mid level
        elif years_experience < 8:
            return progression[:3]  # Senior level
        else:
            return progression  # All levels

    def _calculate_role_similarity(self, role1: str, role2: str) -> float:
        """Calculate similarity between two role titles."""
        # Normalize roles
        role1 = re.sub(r'[^a-z\s]', '', role1.lower())
        role2 = re.sub(r'[^a-z\s]', '', role2.lower())

        # Split into words
        words1 = set(role1.split())
        words2 = set(role2.split())

        # Calculate Jaccard similarity
        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0.0

    def _calculate_progression_confidence(
        self,
        role: str,
        years_experience: int
    ) -> float:
        """Calculate confidence score for a progression-based recommendation."""
        # Base confidence on role level and experience
        if "senior" in role.lower() and years_experience < 5:
            return 0.6
        elif "lead" in role.lower() and years_experience < 8:
            return 0.5
        elif "manager" in role.lower() and years_experience < 10:
            return 0.4
        elif "director" in role.lower() and years_experience < 12:
            return 0.3
        elif "chief" in role.lower() and years_experience < 15:
            return 0.2
        return 0.8

    def _get_roles_for_cluster(
        self,
        cluster: str,
        years_experience: int
    ) -> List[str]:
        """Get suitable roles for a skill cluster."""
        roles = {
            "frontend": [
                "frontend developer",
                "ui developer",
                "web developer",
                "frontend engineer",
                "ui/ux developer"
            ],
            "backend": [
                "backend developer",
                "software engineer",
                "api developer",
                "backend engineer",
                "systems engineer"
            ],
            "data": [
                "data scientist",
                "data analyst",
                "machine learning engineer",
                "data engineer",
                "analytics engineer"
            ],
            "devops": [
                "devops engineer",
                "site reliability engineer",
                "platform engineer",
                "cloud engineer",
                "infrastructure engineer"
            ],
            "architecture": [
                "solution architect",
                "technical architect",
                "enterprise architect",
                "cloud architect",
                "systems architect"
            ]
        }

        if cluster not in roles:
            return []

        # Filter roles based on experience
        all_roles = roles[cluster]
        if years_experience < 3:
            return all_roles[:2]  # Junior roles
        elif years_experience < 5:
            return all_roles[1:3]  # Mid-level roles
        else:
            return all_roles[2:]  # Senior roles

    def _get_required_skills(self, role: str) -> Dict[str, float]:
        """Get required skills and their importance for a role."""
        # Define skill requirements for common roles
        requirements = {
            "frontend developer": {
                "javascript": 0.9,
                "html": 0.9,
                "css": 0.9,
                "react": 0.8,
                "typescript": 0.7,
                "git": 0.7,
                "responsive design": 0.8,
                "web accessibility": 0.6
            },
            "backend developer": {
                "python": 0.8,
                "java": 0.8,
                "sql": 0.9,
                "apis": 0.9,
                "microservices": 0.7,
                "git": 0.7,
                "docker": 0.6
            },
            "data scientist": {
                "python": 0.9,
                "sql": 0.8,
                "machine learning": 0.9,
                "statistics": 0.9,
                "data visualization": 0.7,
                "deep learning": 0.6
            },
            "devops engineer": {
                "linux": 0.9,
                "docker": 0.9,
                "kubernetes": 0.8,
                "ci/cd": 0.9,
                "cloud platforms": 0.8,
                "monitoring": 0.7
            },
            "solution architect": {
                "system design": 0.9,
                "cloud architecture": 0.9,
                "microservices": 0.8,
                "security": 0.8,
                "scalability": 0.9,
                "integration patterns": 0.8
            }
        }

        # Find best matching role
        best_match: Optional[str] = None
        best_score: float = 0.0
        for template_role in requirements:
            score = self._calculate_role_similarity(role, template_role)
            if score > best_score:
                best_match = template_role
                best_score = score

        return requirements.get(best_match or "", {})
