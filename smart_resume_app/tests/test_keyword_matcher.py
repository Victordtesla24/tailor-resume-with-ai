"""Tests for keyword matching functionality."""
import pytest
from src.keyword_matcher import (
    KeywordMatcher,
    SectionDetector,
    SkillExtractor
)


@pytest.fixture
def sample_resume_text():
    """Sample resume text for testing."""
    text = """
    Professional Summary

    Experienced Solution Architect with
    expertise in cloud
    transformation

    Experience
    Senior Solution Architect at Tech Corp
    - Led cloud transformation initiatives
    - Designed microservices architecture

    Skills
    - Cloud Platforms: AWS Azure GCP
    - Architecture: Solution Design
    Enterprise Architecture
    - Methodologies: Agile Scrum DevOps
    """
    print("\nSample Resume Text:")
    print(text)
    return text


@pytest.fixture
def sample_job_text():
    """Sample job description text for testing."""
    return """
    Solution Architect Position

    Requirements:
    - 5+ years experience in
      Solution Architecture
    - Strong background in Cloud Architecture

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


def test_keyword_extraction(keyword_matcher, sample_resume_text):
    """Test keyword extraction functionality."""
    keywords = keyword_matcher._load_skill_patterns()
    assert isinstance(keywords, dict)
    assert "programming" in keywords
    assert "python" in keywords["programming"]


def test_section_detection(section_detector, sample_resume_text):
    """Test section detection functionality."""
    sections = section_detector.identify_sections(sample_resume_text)
    print("\nExtracted Sections:")
    print(sections)

    assert "summary" in sections
    assert "experience" in sections
    assert "skills" in sections

    # Test content extraction
    assert "Solution Architect" in sections["summary"]
    assert "Tech Corp" in sections["experience"]
    assert "Cloud Platforms" in sections["skills"]


def test_skill_extraction(
    skill_extractor,
    sample_resume_text,
    sample_job_text
):
    """Test skill extraction and categorization."""
    resume_skills = skill_extractor.extract_skills(sample_resume_text)

    # Test technical skills
    assert "cloud" in resume_skills["technical"]
    assert "aws" in resume_skills["technical"]
    assert "azure" in resume_skills["technical"]

    # Test soft skills
    assert "agile" in resume_skills["soft"]

    # Test job description skills
    job_skills = skill_extractor.extract_skills(sample_job_text)
    assert "leadership" in job_skills["soft"]


def test_skill_matching(keyword_matcher, sample_resume_text, sample_job_text):
    """Test skill matching between resume and job description."""
    matches = keyword_matcher.match_skills(sample_resume_text, sample_job_text)
    assert isinstance(matches, dict)
    assert matches.get("cloud", 0) == 1.0  # Should match
    assert matches.get("java", 0) == 0.0   # Should not match


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
    assert "python" in tech_skills
    assert "aws" in tech_skills
    assert "azure" in tech_skills
    assert "agile" in skills["soft"]
