from setuptools import setup, find_packages

setup(
    name="smart_resume_app",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "streamlit>=1.24.0",
        "python-docx>=0.8.11",
        "requests>=2.31.0",
        "beautifulsoup4>=4.12.2",
        "python-dotenv>=1.0.0",
        "openai>=1.0.0",
        "anthropic>=0.3.0",
        "keyring>=24.2.0",
        "spacy==3.7.2",
        "pytest>=7.0.0",
        "pytest-cov>=4.0.0"
    ],
    python_requires=">=3.11",
)
