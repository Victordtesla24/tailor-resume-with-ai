"""AI Models for Resume Processing"""
import openai
import anthropic
from .config import Config


class ResumeProcessor:
    """Handles resume processing using various AI models."""

    def __init__(self, config: Config):
        """Initialize the resume processor with configuration."""
        self.config = config
        self.openai_client = openai.OpenAI(
            api_key=config.get('OPENAI_API_KEY')
        )
        self.anthropic_client = anthropic.Anthropic(
            api_key=config.get('ANTHROPIC_API_KEY')
        )

    def process_resume(
        self,
        resume_text: str,
        job_description: str,
        model: str = 'gpt-4'
    ) -> str:
        """Process and tailor resume for job description."""
        if model.startswith('gpt'):
            return self._process_with_openai(
                resume_text, job_description, model
            )
        elif model.startswith('claude'):
            return self._process_with_anthropic(resume_text, job_description)
        else:
            raise ValueError(f"Unsupported model: {model}")

    def _process_with_openai(
        self,
        resume_text: str,
        job_description: str,
        model: str
    ) -> str:
        """Process resume using OpenAI models."""
        prompt = self._create_prompt(resume_text, job_description)
        
        response = self.openai_client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional resume writer."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        if response.choices[0].message.content is None:
            raise ValueError("OpenAI API returned empty response")
        return response.choices[0].message.content

    def _process_with_anthropic(
        self,
        resume_text: str,
        job_description: str
    ) -> str:
        """Process resume using Anthropic Claude."""
        prompt = self._create_prompt(resume_text, job_description)
        
        response = self.anthropic_client.messages.create(
            model="claude-2",
            max_tokens=2000,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )
        
        if not response.content or not response.content[0].text:
            raise ValueError("Anthropic API returned empty response")
        return response.content[0].text

    def _create_prompt(self, resume_text: str, job_description: str) -> str:
        """Create the prompt for AI models."""
        return f"""
        Task: Tailor the following resume to match the job description while 
        maintaining truthfulness and professional formatting.

        Job Description:
        {job_description}

        Original Resume:
        {resume_text}

        Please provide a tailored version of the resume that:
        1. Highlights relevant skills and experiences
        2. Uses industry-specific keywords from the job description
        3. Maintains truthful information
        4. Preserves professional formatting
        5. Optimizes for ATS systems
        """
