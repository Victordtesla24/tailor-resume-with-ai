"""Setup configuration for smart_resume_app package."""

try:
    from setuptools import find_packages, setup
except ImportError:
    from distutils.core import setup

setup(
    name="smart_resume_app",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "pytest>=8.0.0",
        "pylint>=3.0.0",
        "setuptools>=69.0.0",
    ],
    author="Vic D",
    author_email="melbvicduque@gmail.com",
    description="A smart resume analysis and tailoring tool",
    keywords="resume, ai, nlp, job search",
    python_requires=">=3.8",
)
