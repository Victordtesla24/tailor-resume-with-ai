"""Keyword matching and ATS optimization."""

__all__ = ["KeywordMatcher", "SectionDetector", "SkillExtractor"]

import re
from collections import Counter
from typing import Dict, List, Optional, Set, Union, TypedDict

import spacy
from sklearn.feature_extraction.text import TfidfVectorizer

# Load spaCy model for NLP processing
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    import subprocess

    subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"])
    nlp = spacy.load("en_core_web_sm")


class IndustryTerms:
    """Industry-specific terminology."""

    TECH_TERMS = {
        "languages": {
            "python",
            "java",
            "javascript",
            "typescript",
            "c++",
            "c#",
            "ruby",
            "go",
            "rust",
            "swift",
            "kotlin",
            "scala",
            "php",
            "perl",
            "r",
            "matlab",
        },
        "frameworks": {
            "react",
            "angular",
            "vue",
            "django",
            "flask",
            "spring",
            "express",
            "tensorflow",
            "pytorch",
            "keras",
            "scikit-learn",
            "pandas",
            "numpy",
        },
        "cloud": {
            "aws",
            "azure",
            "gcp",
            "kubernetes",
            "docker",
            "terraform",
            "jenkins",
            "ci/cd",
            "devops",
            "microservices",
            "serverless",
            "iaas",
            "paas",
            "saas",
        },
        "databases": {
            "sql",
            "mysql",
            "postgresql",
            "mongodb",
            "redis",
            "elasticsearch",
            "cassandra",
            "dynamodb",
            "oracle",
            "sqlite",
            "nosql",
        },
    }

    SOFT_SKILLS = {
        "leadership": {
            "team leadership",
            "strategic planning",
            "decision making",
            "mentoring",
            "coaching",
            "conflict resolution",
        },
        "communication": {
            "presentation skills",
            "public speaking",
            "technical writing",
            "stakeholder management",
            "client communication",
        },
        "management": {
            "project management",
            "agile",
            "scrum",
            "kanban",
            "lean",
            "risk management",
            "resource planning",
            "budgeting",
        },
    }

    METHODOLOGIES = {
        "agile": {
            "scrum",
            "kanban",
            "xp",
            "lean",
            "safe",
            "crystal",
            "dsdm",
            "feature driven development",
            "adaptive software development",
        },
        "development": {
            "tdd",
            "bdd",
            "ddd",
            "ci/cd",
            "devops",
            "waterfall",
            "spiral",
            "rapid application development",
            "extreme programming",
        },
        "design": {
            "solid",
            "dry",
            "kiss",
            "mvc",
            "mvvm",
            "clean architecture",
            "microservices",
            "service oriented architecture",
        },
    }


class ValidationResult(TypedDict):
    """Type definition for section validation result."""

    valid: bool
    has_content: bool
    has_structure: bool
    has_metrics: bool
    message: str


class SkillMatch(TypedDict):
    """Type definition for skill match result."""

    name: str
    confidence: float


class MatchResult(TypedDict):
    """Type definition for match result."""

    score: float
    matched_terms: float


class CategoryMatches(TypedDict):
    """Type definition for category matches."""

    score: float
    matches: float


class SectionScore(TypedDict):
    """Type definition for section score."""

    score: float
    keyword_density: Dict[str, float]


class MatchSkillsResult(TypedDict):
    """Type definition for match_skills result."""

    overall_match: Dict[str, Union[float, int]]
    category_matches: Dict[str, CategoryMatches]
    section_scores: Optional[Dict[str, SectionScore]]


class KeywordMatcher:
    """Handles keyword matching and ATS optimization."""

    def __init__(self) -> None:
        """Initialize keyword matcher."""
        self.vectorizer = TfidfVectorizer(
            stop_words="english", ngram_range=(1, 3), max_features=1000
        )
        self.industry_terms = IndustryTerms()

    def extract_keywords(
        self, text: str, *, include_phrases: bool = True, context: Optional[str] = None
    ) -> Dict[str, Set[str]]:
        """Extract important keywords from text using NLP."""
        doc = nlp(text.lower())
        keywords: Dict[str, Set[str]] = {
            "technical": set(),
            "soft_skills": set(),
            "methodologies": set(),
            "domain": set(),
            "phrases": set() if include_phrases else set(),
        }

        # Extract named entities and noun phrases
        for ent in doc.ents:
            if ent.label_ in ["ORG", "PRODUCT", "GPE", "TECH"]:
                if len(ent.text.split()) > 1:
                    keywords["phrases"].add(ent.text)
                else:
                    keywords["technical"].add(ent.text)

        # Extract noun phrases if enabled
        if include_phrases:
            for chunk in doc.noun_chunks:
                if 2 <= len(chunk.text.split()) <= 3:  # 2-3 word phrases
                    keywords["phrases"].add(chunk.text)

        # Extract technical terms and skills
        for token in doc:
            if token.pos_ in ["NOUN", "PROPN"] and len(token.text) > 2:
                # Check against industry terms
                term = token.text.lower()
                if any(term in terms for terms in self.industry_terms.TECH_TERMS.values()):
                    keywords["technical"].add(term)
                elif any(term in terms for terms in self.industry_terms.SOFT_SKILLS.values()):
                    keywords["soft_skills"].add(term)
                elif any(term in terms for terms in self.industry_terms.METHODOLOGIES.values()):
                    keywords["methodologies"].add(term)

        # Context-aware extraction
        if context:
            context_doc = nlp(context.lower())
            for token in context_doc:
                if token.pos_ in ["NOUN", "PROPN"]:
                    keywords["domain"].add(token.text)

        return keywords

    def calculate_keyword_density(
        self, text: str, section: Optional[str] = None
    ) -> Dict[str, float]:
        """Calculate keyword density scores with section context."""
        # Get section-specific weights
        weights = {"summary": 1.2, "experience": 1.0, "skills": 1.5, "education": 0.8}
        section_weight = weights.get(section.lower(), 1.0) if section else 1.0

        # Calculate density
        words = re.findall(r"\b\w+\b", text.lower())
        word_count = len(words)
        density = Counter(words)

        return {
            word: float(count / word_count) * float(section_weight)
            for word, count in density.items()
        }

    def match_skills(self, resume_text: str, job_description: str) -> Dict[str, float]:
        """Match skills between resume and job description."""
        # Extract keywords from both texts
        resume_keywords = self.extract_keywords(resume_text)
        job_keywords = self.extract_keywords(job_description)

        # Calculate matches for each category
        matches: Dict[str, float] = {}

        for category in ["technical", "soft_skills", "methodologies", "domain", "phrases"]:
            resume_terms = resume_keywords[category]
            job_terms = job_keywords[category]

            if job_terms:  # Only calculate if job requires skills in this category
                matched = resume_terms.intersection(job_terms)
                score = len(matched) / len(job_terms) if job_terms else 0.0
                matches[category] = score

        return matches


class SectionDetector:
    """Detects and identifies sections in resume text."""

    def __init__(self) -> None:
        """Initialize section detector."""
        self.common_sections = {
            "summary": ["summary", "professional summary", "profile", "objective"],
            "experience": ["experience", "work experience", "employment history", "work history"],
            "education": ["education", "academic background", "qualifications"],
            "skills": ["skills", "technical skills", "core competencies", "expertise"],
        }

    def identify_sections(self, text: str) -> List[str]:
        """Identify sections in the resume text."""
        sections = []
        lines = text.lower().split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            for section_type, keywords in self.common_sections.items():
                if any(keyword in line for keyword in keywords):
                    if section_type not in sections:
                        sections.append(section_type)

        return sections


class SkillExtractor:
    """Extracts skills from text using NLP."""

    def __init__(self) -> None:
        """Initialize skill extractor."""
        self.nlp = nlp
        self.skill_patterns = [
            "programming languages?",
            "frameworks?",
            "tools?",
            "methodologies",
            "technologies",
            "platforms?",
            "databases?",
            "software",
        ]

    def extract_skills(self, text: str) -> Set[str]:
        """Extract skills from text."""
        doc = self.nlp(text.lower())
        skills = set()

        # Extract noun phrases following skill indicators
        for sent in doc.sents:
            sent_text = sent.text.lower()
            if any(re.search(pattern, sent_text) for pattern in self.skill_patterns):
                for token in sent:
                    if token.pos_ in ["NOUN", "PROPN"]:
                        skills.add(token.text)

        return skills
