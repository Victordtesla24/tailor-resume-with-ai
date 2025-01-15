"""AI model integration for resume tailoring."""
import logging
from typing import Dict, List, Optional, Any
import openai  # type: ignore
import anthropic  # type: ignore
from src.config import Config
from src.utils import RateLimiter
from src.exceptions import RateLimitExceeded

# Type hints for external packages
OpenAI = Any  # type: ignore
Anthropic = Any  # type: ignore

# Setup logging
logger = logging.getLogger(__name__)


class AIModel:
    """Base class for AI model integration."""

    def process_resume(
        self,
        resume_text: str,
        job_description: str,
        sections: List[str]
    ) -> str:
        """Process resume with AI model."""
        raise NotImplementedError


class OpenAIModel(AIModel):
    """OpenAI model integration."""

    def __init__(self, api_key: str, model: str = "gpt-4"):
        """Initialize with API key and model."""
        self.client = openai.OpenAI(api_key=api_key)
        self.model: str = model

    def _create_prompt(
        self,
        resume_text: str,
        job_description: str,
        sections: List[str]
    ) -> str:
        """Create prompt for OpenAI model."""
        sections_list = ', '.join(sections)
        return (
            "Please tailor these resume sections: {}\n"
            "to better match this job description. Focus on:\n\n"
            "1. Solution Architecture Experience (5+ years):\n"
            "   - Highlight key architectural decisions and impact\n"
            "   - Show solution design leadership and governance\n"
            "   - Demonstrate enterprise architecture expertise\n"
            "   - Quantify outcomes and ROI\n\n"
            "2. Cloud & SaaS Transformation:\n"
            "   - Show hands-on cloud expertise (AWS/Azure/GCP)\n"
            "   - Detail SaaS implementations and adoption\n"
            "   - Lead cloud transformations\n"
            "   - Measure migration success\n\n"
            "3. Domain Expertise:\n"
            "   - App Architecture: Design patterns, scalability\n"
            "   - Integration: APIs, microservices, patterns\n"
            "   - Security: Identity, compliance, frameworks\n"
            "   - Infrastructure: Cloud-native, DevOps\n"
            "   - Process: Methods and best practices\n\n"
            "4. Financial Services Background:\n"
            "   - Financial services domain knowledge and regulations\n"
            "   - Technical certifications and education (CS/IT degree)\n"
            "   - Architecture governance and compliance experience\n"
            "   - Industry-specific transformation projects\n\n"
            "Job Description:\n{}\n\n"
            "Resume:\n{}\n\n"
            "Guidelines:\n"
            "- Quantify architectural achievements\n"
            "- Emphasize technical leadership\n"
            "- Focus on transformation impact\n"
            "- Highlight financial services expertise\n\n"
            "Return only the modified sections."
        ).format(sections_list, job_description, resume_text)

    def process_resume(
        self,
        resume_text: str,
        job_description: str,
        sections: List[str]
    ) -> str:
        """Process resume with OpenAI model."""
        try:
            prompt = self._create_prompt(
                resume_text,
                job_description,
                sections
            )

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=2000
            )

            if not response.choices:
                raise ValueError("No response from OpenAI API")

            return str(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise


class AnthropicModel(AIModel):
    """Anthropic model integration."""

    def __init__(self, api_key: str, model: str = "claude-2"):
        """Initialize with API key and model."""
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model: str = model

    def process_resume(
        self,
        resume_text: str,
        job_description: str,
        sections: List[str]
    ) -> str:
        """Process resume with Anthropic model."""
        try:
            prompt = self._create_prompt(
                resume_text,
                job_description,
                sections
            )

            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )

            if not response.content:
                raise ValueError("Empty response from Anthropic API")
            return str(response.content[0].text)  # type: ignore
        except Exception as e:
            logger.error(f"Anthropic API error: {str(e)}")
            raise

    def _create_prompt(
        self,
        resume_text: str,
        job_description: str,
        sections: List[str]
    ) -> str:
        """Create prompt for Anthropic model."""
        sections_list = ', '.join(sections)
        return (
            "Please tailor these resume sections: {}\n"
            "to better match this job description. Focus on:\n\n"
            "1. Solution Architecture Experience (5+ years):\n"
            "   - Highlight key architectural decisions and impact\n"
            "   - Show solution design leadership and governance\n"
            "   - Demonstrate enterprise architecture expertise\n"
            "   - Quantify outcomes and ROI\n\n"
            "2. Cloud & SaaS Transformation:\n"
            "   - Show hands-on cloud expertise (AWS/Azure/GCP)\n"
            "   - Detail SaaS implementations and adoption\n"
            "   - Lead cloud transformations\n"
            "   - Measure migration success\n\n"
            "3. Domain Expertise:\n"
            "   - App Architecture: Design patterns, scalability\n"
            "   - Integration: APIs, microservices, patterns\n"
            "   - Security: Identity, compliance, frameworks\n"
            "   - Infrastructure: Cloud-native, DevOps\n"
            "   - Process: Methods and best practices\n\n"
            "4. Financial Services Background:\n"
            "   - Financial services domain knowledge and regulations\n"
            "   - Technical certifications and education (CS/IT degree)\n"
            "   - Architecture governance and compliance experience\n"
            "   - Industry-specific transformation projects\n\n"
            "Job Description:\n{}\n\n"
            "Resume:\n{}\n\n"
            "Guidelines:\n"
            "- Quantify architectural achievements\n"
            "- Emphasize technical leadership\n"
            "- Focus on transformation impact\n"
            "- Highlight financial services expertise\n\n"
            "Return only the modified sections."
        ).format(sections_list, job_description, resume_text)


class AIModelManager:
    """Enhanced AI model management with better error handling."""

    def __init__(self, config: Config) -> None:
        """Initialize with configuration."""
        self.config = config
        self.models: Dict[str, AIModel] = {}
        self.current_model: Optional[AIModel] = None
        self.rate_limiter = RateLimiter()

        # Initialize models with validation
        self._init_models()

    def _init_models(self) -> None:
        """Initialize AI models with validation."""
        try:
            openai_key = self.config.get('OPENAI_API_KEY')
            anthropic_key = self.config.get('ANTHROPIC_API_KEY')

            if openai_key:
                if not openai_key.startswith('sk-'):
                    raise ValueError("Invalid OpenAI API key format")
                self.models['gpt-4'] = OpenAIModel(openai_key, "gpt-4")
                self.models['gpt-3.5-turbo'] = OpenAIModel(
                    openai_key,
                    "gpt-3.5-turbo"
                )

            if anthropic_key:
                if not anthropic_key.startswith('sk-ant-'):
                    raise ValueError("Invalid Anthropic API key format")
                self.models['claude-2'] = AnthropicModel(anthropic_key)

        except Exception as e:
            logger.error(f"Error initializing AI models: {str(e)}")
            raise

    def switch_model(self, model_name: str) -> None:
        """Switch between AI models with validation and rate limiting."""
        try:
            if not self.rate_limiter.can_access():
                msg = "Rate limit exceeded for model switching"
                logger.warning(msg)
                raise RateLimitExceeded(msg)

            if model_name not in self.models:
                raise ValueError(f"Unsupported model: {model_name}")
            self.current_model = self.models[model_name]

            logger.info(f"Successfully switched to model: {model_name}")

        except Exception as e:
            logger.error(f"Error switching model: {str(e)}")
            raise

    def process_resume(
        self,
        resume_text: str,
        job_description: str,
        sections: List[str]
    ) -> str:
        """Process resume with current model and enhanced error handling."""
        try:
            if not self.current_model:
                raise RuntimeError("No AI model selected")

            if not self.rate_limiter.can_access():
                msg = "Rate limit exceeded for resume processing"
                logger.warning(msg)
                raise RateLimitExceeded(msg)

            result = self.current_model.process_resume(
                resume_text,
                job_description,
                sections
            )
            logger.info("Successfully processed resume")
            return result

        except Exception as e:
            logger.error(f"Error processing resume: {str(e)}")
            raise

    def list_available_models(self) -> List[str]:
        """List available AI models."""
        return list(self.models.keys())
