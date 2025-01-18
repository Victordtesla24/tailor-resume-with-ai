import openai
import asyncio
from typing import Any, Dict, List, Tuple, Union, TypedDict
from datetime import datetime


# Type aliases for better readability
ModelConfig = Dict[str, Dict[str, Any]]
PerformanceMetrics = Dict[Tuple[str, str], float]
OpenAIError = Union[openai.APIError, openai.RateLimitError, Exception]
SkillMetrics = Dict[str, Dict[str, Union[float, datetime]]]
ResponseQueue = asyncio.Queue[Dict[str, Any]]


class FormatPattern(TypedDict):
    """Type definition for format patterns."""
    indentation: Dict[str, int]  # Maps line number (as str) to indentation level
    bullet_points: Dict[str, List[str]]  # Maps line number to bullet point markers
    line_breaks: Dict[str, int]  # Maps position (as str) to line break index
    capitalization: Dict[str, bool]  # Maps word position (as str) to capitalization flag
