import os
import json
from typing import Any, Dict, cast

from .types import ModelConfig


def load_model_config() -> ModelConfig:
    """Load models configuration dynamically."""
    default_config = {
        "gpt-4": {
            "name": "gpt-4",
            "max_tokens": 3000,
            "temperature": 0.7,
            "description": "High-level synthesis and complex tailoring.",
            "prompt_template": (
                "As an expert resume tailoring system, analyze and enhance the "
                "following {section} considering:\n"
                "1. Industry-specific terminology and best practices\n"
                "2. Quantifiable achievements and metrics\n"
                "3. Technical depth and expertise level\n"
                "4. Format consistency and structure\n\n"
                "Original Content:\n{content}\n\n"
                "Job Description:\n{job_description}\n\n"
                "Maintain the original format while optimizing content."
            ),
            "success_metrics": {
                "format_retention": 0.9,
                "terminology_accuracy": 0.85,
                "skill_match": 0.8
            }
        },
        "o1-mini": {
            "name": "o1-mini",
            "max_tokens": 2000,
            "temperature": 0.5,
            "description": "Efficient for tailored resume validation.",
            "prompt_template": (
                "Validate and enhance this {section} for:\n"
                "1. Keyword optimization\n"
                "2. Clear value propositions\n"
                "3. Consistency check\n\n"
                "Content:\n{content}\n"
                "Job Requirements:\n{job_description}\n\n"
                "Preserve formatting while improving content."
            ),
            "success_metrics": {
                "format_retention": 0.95,
                "terminology_accuracy": 0.8,
                "skill_match": 0.85
            }
        },
        "o1-preview": {
            "name": "o1-preview",
            "max_tokens": 2500,
            "temperature": 0.4,
            "description": "Provides final executive-level refinements.",
            "prompt_template": (
                "Refine this {section} with executive-level polish:\n"
                "1. Strategic impact emphasis\n"
                "2. Leadership qualities\n"
                "3. Industry alignment\n\n"
                "Section:\n{content}\n"
                "Role Context:\n{job_description}\n\n"
                "Maintain professional formatting."
            ),
            "success_metrics": {
                "format_retention": 0.9,
                "terminology_accuracy": 0.9,
                "skill_match": 0.85
            }
        }
    }
    config_str = os.getenv("AVAILABLE_MODELS", json.dumps(default_config))
    return cast(ModelConfig, json.loads(config_str))


AVAILABLE_MODELS = load_model_config()


PERSONAS = {
    "Enterprise Architect": {
        "focus": [
            "technical skills", "certifications", "tools", "cloud architecture",
            "system design"
        ],
        "target_roles": [
            "enterprise architect", "solution designer", "data architect",
            "cloud architect"
        ],
    },
    "Agile Project Manager": {
        "focus": [
            "agile principles", "scrum leadership", "stakeholder management",
            "product roadmaps"
        ],
        "target_roles": ["agile project manager", "scrum master", "project manager"],
    },
    "default": {
        "focus": ["general skills", "adaptability", "collaboration", "communication"],
        "target_roles": []
    },
}


# Cache persona-related data for improved performance
PERSONAS_CACHED: Dict[str, Dict[str, Any]] = {
    persona: {
        "target_roles_set": set(details["target_roles"]),
        "focus_set": set(details["focus"]),
        "precomputed_overlap": 0,  # Initialize with 0 instead of empty dict
    }
    for persona, details in PERSONAS.items()
}
