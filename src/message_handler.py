import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


logger = logging.getLogger("resume_tailor")


@dataclass
class Message:
    """Represents a chat message with role and content."""
    role: str
    content: str


class SystemMessageHandler:
    """Handles system messages and API format for OpenAI chat completions."""

    def __init__(self) -> None:
        self.default_system_messages: Dict[str, str] = {
            "resume_tailor": (
                "You are an expert resume tailoring system. Focus on optimizing content "
                "while preserving format and structure. Emphasize relevant skills, "
                "quantifiable achievements, and industry-specific terminology."
            ),
            "skill_analyzer": (
                "You are a skilled job market analyst. Evaluate skills and experience "
                "levels based on context, temporal information, and industry standards."
            ),
            "format_validator": (
                "You are a document formatting specialist. Ensure consistent structure, "
                "proper section organization, and professional presentation standards."
            )
        }

    def create_messages(
        self,
        prompt: str,
        role: str = "resume_tailor",
        additional_context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, str]]:
        """
        Create a properly formatted message list for OpenAI API.

        Args:
            prompt: The user prompt
            role: The system role to use
            additional_context: Additional context to include in system message

        Returns:
            List of messages in OpenAI chat format
        """
        system_message = self.default_system_messages.get(
            role,
            self.default_system_messages["resume_tailor"]
        )

        if additional_context:
            context_str = " ".join(
                f"{key}: {value}" for key, value in additional_context.items()
            )
            system_message = f"{system_message}\n\nContext: {context_str}"

        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ]

        return messages

    def create_resume_messages(
        self,
        section: str,
        content: str,
        job_description: str,
        persona: str
    ) -> List[Dict[str, str]]:
        """
        Create specialized messages for resume tailoring.

        Args:
            section: Resume section being processed
            content: Original content
            job_description: Target job description
            persona: Selected persona

        Returns:
            List of messages in OpenAI chat format
        """
        system_message = (
            f"You are an expert resume tailoring system optimizing for the {persona} "
            f"persona. Focus on enhancing the {section} section while maintaining "
            "professional formatting and emphasizing relevant achievements."
        )

        prompt = (
            f"Task: Resume tailoring\n"
            f"Section: {section}\n"
            f"Persona: {persona}\n\n"
            f"Original Content:\n{content}\n\n"
            f"Job Description:\n{job_description}\n\n"
            "Enhance this content while preserving the original format. "
            "Focus on relevant skills, quantifiable achievements, and "
            "industry-specific terminology."
        )

        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ]

        return messages

    def format_api_request(
        self,
        messages: List[Dict[str, str]],
        model: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Format the complete API request with all parameters.

        Args:
            messages: List of chat messages
            model: Model to use
            params: Additional parameters for the API call

        Returns:
            Complete API request dictionary
        """
        request = {
            "model": model,
            "messages": messages,
            "store": True  # Enable response storage as per latest API
        }

        if params:
            request.update(params)

        return request

    def parse_response(
        self,
        response: Dict[str, Any],
        extract_content: bool = True
    ) -> Any:
        """
        Parse API response and extract relevant information.

        Args:
            response: Raw API response
            extract_content: Whether to extract just the content

        Returns:
            Parsed response data
        """
        if extract_content:
            try:
                return response["choices"][0]["message"]["content"]
            except (KeyError, IndexError) as e:
                logger.error(f"Failed to extract content from response: {e}")
                return None
        return response
