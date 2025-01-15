"""Tests for keyword matching and section detection."""
import pytest  # type: ignore
from unittest.mock import Mock, patch
from src.keyword_matcher import (
    KeywordMatcher,
    SectionDetector,
    SkillExtractor
)


@pytest.fixture
def sample_resume_text():
    """Create sample resume text."""
    return """
    Professional Summary

    Experienced Solution Architect with
    expertise in cloud
    transformation
    and enterprise architecture.

    Technical Skills

    - Cloud Platforms: AWS, Azure, GCP
    - Architecture: Solution Design,
      Enterprise Architecture
    - Methodologies: Agile, Scrum, DevOps
    - Languages: Python, Java, SQL

    Work Experience

    Senior Solution Architect at Tech Corp
    - Led cloud transformation initiatives
    - Designed microservices architecture
    """


@pytest.fixture
def sample_job_text():
    """Create sample job description."""
    return """
    Solution Architect Position

    Requirements:
    - 5+ years experience in
      Solution Architecture
    - Strong background in AWS
      and Azure
    - Experience with Kubernetes
      and Docker
    - Knowledge of Enterprise
      Architecture

    Skills:
    - Cloud Architecture
    - System Design
    - Agile/Scrum
    - Leadership
    """


@pytest.fixture
def keyword_matcher():
    """Create KeywordMatcher instance."""
    return KeywordMatcher()


@pytest.fixture
def section_detector():
    """Create SectionDetector instance."""
    return SectionDetector()


@pytest.fixture
def skill_extractor():
    """Create SkillExtractor instance."""
    return SkillExtractor()


@patch('spacy.load')
def test_keyword_extraction(mock_load, keyword_matcher, sample_resume_text):
    """Test keyword extraction functionality."""
    # Mock spaCy behavior
    mock_doc = Mock()
    mock_token = Mock()
    mock_token.text = "Architecture"
    mock_token.pos_ = "NOUN"
    mock_token.is_stop = False
    mock_doc.__iter__.return_value = [mock_token]
    mock_load.return_value.return_value = mock_doc

    keywords = keyword_matcher.extract_keywords(sample_resume_text)
    assert "Architecture" in keywords


def test_section_detection(section_detector, sample_resume_text):
    """Test section detection functionality."""
    sections = section_detector.identify_sections(sample_resume_text)

    assert "summary" in sections
    assert "skills" in sections
    assert "experience" in sections

    # Test content extraction
    summary = sections["summary"]
    assert "Solution Architect" in summary
    assert "cloud transformation" in summary


def test_skill_extraction(
    skill_extractor,
    sample_resume_text,
    sample_job_text
):
    """Test skill extraction and categorization."""
    resume_skills = skill_extractor.extract_skills(sample_resume_text)

    # Test technical skills
    assert "Python" in resume_skills["technical"]
    assert "AWS" in resume_skills["technical"]

    # Test architecture skills
    arch_skills = resume_skills["architecture"]
    has_arch = any(
        "Architecture" in skill
        for skill in arch_skills
    )
    assert has_arch

    # Test methodologies
    assert "Agile" in resume_skills["methodologies"]

    # Test missing skills suggestion
    missing = skill_extractor.suggest_missing_skills(
        sample_resume_text,
        sample_job_text
    )
    assert "Docker" in missing["technical"]


@patch('spacy.load')
def test_skill_matching(mock_load, keyword_matcher, sample_resume_text):
    """Test skill matching functionality."""
    # Mock spaCy similarity behavior
    mock_doc = Mock()
    mock_span = Mock()
    mock_span.similarity.return_value = 0.8
    mock_span.text = "Architecture"
    mock_doc.char_span.return_value = mock_span
    mock_load.return_value.return_value = mock_doc

    desc = "Solution Architect role"
    scores = keyword_matcher.match_skills(sample_resume_text, desc)
    assert scores["Architecture"] >= 0.7


def test_section_detector_edge_cases(section_detector):
    """Test section detection edge cases."""
    # Test empty text
    sections = section_detector.identify_sections("")
    assert not sections

    # Test text without sections
    text = "This is a plain text without any sections."
    sections = section_detector.identify_sections(text)
    assert not sections

    # Test text with only section headers
    text = "Summary\nExperience\nEducation"
    sections = section_detector.identify_sections(text)
    assert all(content == "" for content in sections.values())


def test_skill_extractor_edge_cases(skill_extractor):
    """Test skill extraction edge cases."""
    # Test empty text
    skills = skill_extractor.extract_skills("")
    assert not any(skills.values())

    # Test text without skills
    text = "This text contains no relevant skills."
    skills = skill_extractor.extract_skills(text)
    assert not any(skills.values())

    # Test unusual skill formats
    text = """
    Skills:
    - Python3.9+
    - AWS/Azure
    - Agile/Scrum/Kanban
    """
    skills = skill_extractor.extract_skills(text)
    tech_skills = skills["technical"]
    has_python = any("Python" in skill for skill in tech_skills)
    assert has_python
