import re
from typing import Dict

from .types import FormatPattern


class FormatHandler:
    """Handles text formatting operations."""
    def __init__(self) -> None:
        self.format_cache: Dict[str, FormatPattern] = {}

    def retain_format(self, original: str, modified: str) -> str:
        """Preserve formatting while updating content."""
        # Cache original format if not already cached
        section_hash = str(hash(original))
        if section_hash not in self.format_cache:
            self.format_cache[section_hash] = self._extract_format_pattern(original)

        return self._apply_format_pattern(modified, self.format_cache[section_hash])

    def _extract_format_pattern(self, text: str) -> FormatPattern:
        """Extract formatting patterns from text."""
        lines = text.splitlines()
        return {
            "indentation": {
                str(i): len(line) - len(line.lstrip())
                for i, line in enumerate(lines)
            },
            "bullet_points": {
                str(i): re.findall(r"^(\s*[-•*]\s*)", line)
                for i, line in enumerate(lines)
            },
            "line_breaks": {
                str(i): i for i, c in enumerate(text) if c == "\n"
            },
            "capitalization": {
                str(i): word.isupper()
                for i, word in enumerate(text.split())
            }
        }

    def _apply_format_pattern(self, text: str, pattern: FormatPattern) -> str:
        """Apply extracted format pattern to new text."""
        lines = text.splitlines()
        formatted_lines = []

        for i, line in enumerate(lines):
            str_i = str(i)
            # Apply indentation if available
            if str_i in pattern["indentation"]:
                line = " " * pattern["indentation"][str_i] + line.lstrip()

            # Apply bullet points if available
            if str_i in pattern["bullet_points"] and pattern["bullet_points"][str_i]:
                if not any(line.startswith(bp.strip()) for bp in pattern["bullet_points"][str_i]):
                    line = pattern["bullet_points"][str_i][0] + line.lstrip()

            formatted_lines.append(line)

        # Join lines and preserve line breaks
        formatted_text = "\n".join(formatted_lines)

        # Apply capitalization
        words = formatted_text.split()
        for i, word in enumerate(words):
            str_i = str(i)
            if str_i in pattern["capitalization"] and pattern["capitalization"][str_i]:
                words[i] = word.upper()

        return " ".join(words)
