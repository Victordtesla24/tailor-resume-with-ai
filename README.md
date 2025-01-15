# Smart Resume Tailor

An AI-powered application that helps tailor resumes for specific job descriptions using OpenAI GPT and Anthropic Claude models.

## Features

- Automatic resume tailoring based on job descriptions
- Support for multiple AI models (GPT-4, GPT-3.5, Claude)
- Smart keyword analysis and optimization
- Professional formatting preservation
- Real-time tailoring suggestions

## Prerequisites

- Python 3.8 or higher
- OpenAI API key
- Anthropic API key (optional, for Claude model)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/Victordtesla24/tailor-resume-with-ai.git
cd tailor-resume-with-ai
```

2. Create and activate a virtual environment:
```bash
python -m venv resume_app_env
source resume_app_env/bin/activate  # On Windows: resume_app_env\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r smart_resume_app/requirements.txt
```

4. Set up environment variables:
```bash
cp smart_resume_app/.env.example smart_resume_app/.env
```
Edit `.env` with your API keys.

## Usage

1. Run the application:
```bash
cd smart_resume_app
python app.py
```

2. Follow the prompts to:
   - Input your resume
   - Provide the job description
   - Select the AI model
   - Review and save the tailored resume

## Configuration

Configure the application through the `.env` file:
- `OPENAI_API_KEY`: Your OpenAI API key
- `ANTHROPIC_API_KEY`: Your Anthropic API key (optional)

## Project Structure

```
smart_resume_app/
├── src/
│   ├── components.py    # UI components
│   ├── config.py        # Configuration management
│   ├── models.py        # AI model integrations
│   ├── styles.py        # UI styling
│   └── utils.py         # Utility functions
├── app.py              # Main application
├── requirements.txt    # Dependencies
└── .env.example       # Environment variables template
```

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- OpenAI GPT models
- Anthropic Claude model
- Python community
