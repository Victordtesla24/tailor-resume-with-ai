# Technical Context

## Technologies Used

- Python 3.8+
- Streamlit for UI
- Python-docx for document handling
- OpenAI/Anthropic APIs for AI processing
- BeautifulSoup4 for job description parsing
- Pytest for testing

## Development Setup

- Virtual environment: resume_app_env
- Dependencies managed via requirements.txt
- Local development on MacBook Air M3
- VSCode as primary IDE

## Technical Constraints

- Memory limit: 500MB
- File upload size: < 10MB
- Response time: < 10s for AI operations
- Browser compatibility: Modern browsers only
- Security: Local data storage only
- Performance: Optimized for M3 architecture

## API Integration

- OpenAI GPT models
- Anthropic Claude
- Rate limiting implemented
- Fallback handling for API failures
- Secure key management via environment variables
