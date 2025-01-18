# Smart Resume Tailoring App

A Python application that uses AI to intelligently tailor resumes for specific job descriptions while preserving formatting and ensuring data privacy.

## Features

- Multi-AI model support (OpenAI GPT-4, GPT-3.5, Anthropic Claude)
- Automatic job description extraction from Seek.com.au
- Format preservation for Word documents
- Side-by-side comparison view
- Data anonymization and privacy protection
- Secure API key management
- Rate limiting and error handling

## Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/smart-resume-app.git
cd smart-resume-app
```

2. Create and activate a virtual environment:

```bash
python -m venv resume_app_env
source resume_app_env/bin/activate  # On Windows: resume_app_env\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Download spaCy model:

```bash
python -m spacy download en_core_web_sm
```

## Configuration

1. Create a `.env` file in the project root:

```env
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
```

2. (Optional) Adjust configuration in `config.json`:

```json
{
  "rate_limits": {
    "openai": {
      "max_requests": 100,
      "window_seconds": 3600
    },
    "anthropic": {
      "max_requests": 100,
      "window_seconds": 3600
    }
  }
}
```

## Usage

1. Start the application:

```bash
streamlit run app.py
```

2. Upload your resume (Word format)

3. Either:

   - Paste a job description directly, or
   - Enter a Seek.com.au job URL

4. Select sections to tailor

5. Choose AI model and click "Tailor Resume"

## Development

### Running Tests

```bash
pytest
```

### Type Checking

```bash
mypy src tests
```

### Code Quality

```bash
flake8 src tests
```

### Test Coverage

```bash
pytest --cov=src --cov-report=term-missing
```

## Project Structure

```
smart_resume_app/
├── src/
│   ├── __init__.py
│   ├── models.py          # AI model integration
│   ├── formatting.py      # Document formatting
│   ├── job_board.py      # Job board integration
│   ├── components.py      # UI components
│   ├── data_collection.py # Data handling
│   └── config.py         # Configuration
├── tests/
│   ├── __init__.py
│   ├── test_models.py
│   ├── test_formatting.py
│   ├── test_job_board.py
│   └── test_data_collection.py
├── app.py                 # Main application
├── requirements.txt
├── setup.cfg
└── README.md
```

## Security

- API keys are stored securely using system keyring
- Personal data is anonymized before storage
- Rate limiting prevents API abuse
- Error handling prevents data leaks

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and type checking
5. Submit a pull request

## License

MIT License - see LICENSE file for details
