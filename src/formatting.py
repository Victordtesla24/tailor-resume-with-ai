"""Format preservation and section handling."""

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class SectionFormat:
    """Format information for a resume section."""

    indent: str
    bullet_style: str
    spacing: int
    heading_style: str


class FormatPreserver:
    """Handles format preservation for resume sections."""

    def __init__(self) -> None:
        """Initialize format preserver."""
        self.section_patterns = {
            "header": r"^(?:#*\s*)?([A-Z][A-Z\s]+)(?:\s*:)?$",
            "bullet": r"^(\s*)[-•*]\s",
            "numbered": r"^(\s*)\d+\.\s",
        }

    def extract_section(
        self, text: str, section_name: str
    ) -> Tuple[Optional[str], Optional[SectionFormat]]:
        """Extract section content and format."""
        lines = text.split("\n")
        section_start = -1
        section_end = -1

        # Find section boundaries
        for i, line in enumerate(lines):
            if re.match(
                rf"^(?:#*\s*)?{section_name}(?:\s*:)?$", line.strip(), re.IGNORECASE
            ):
                section_start = i
                break

        if section_start == -1:
            return None, None

        # Find section end
        for i in range(section_start + 1, len(lines)):
            if re.match(self.section_patterns["header"], lines[i].strip()):
                section_end = i
                break

        section_end = section_end if section_end != -1 else len(lines)
        section_content = "\n".join(lines[section_start:section_end])

        # Extract format
        format_info = self._extract_format(section_content)

        return section_content, format_info

    def _extract_format(self, content: str) -> SectionFormat:
        """Extract formatting information from content."""
        lines = content.split("\n")

        # Determine heading style
        heading_match = re.match(r"^(#+\s*)?([A-Z][A-Z\s]+)", lines[0])
        heading_style = (
            heading_match.group(1) if heading_match and heading_match.group(1) else ""
        )

        # Find bullet style and indentation
        bullet_style = "-"
        indent = ""
        for line in lines[1:]:
            bullet_match = re.match(self.section_patterns["bullet"], line)
            if bullet_match:
                indent = bullet_match.group(1)
                bullet_style = line[len(indent)]
                break

            numbered_match = re.match(self.section_patterns["numbered"], line)
            if numbered_match:
                indent = numbered_match.group(1)
                bullet_style = "1."
                break

        # Calculate spacing
        spacing = 1
        for i in range(1, len(lines) - 1):
            if not lines[i].strip() and lines[i + 1].strip():
                spacing = max(spacing, 1)
                for j in range(i, 0, -1):
                    if not lines[j].strip():
                        spacing += 1
                    else:
                        break

        return SectionFormat(
            indent=indent,
            bullet_style=bullet_style,
            spacing=spacing,
            heading_style=heading_style,
        )

    def apply_format(self, content: str, format_info: SectionFormat) -> str:
        """Apply formatting to content."""
        lines = content.split("\n")
        formatted = []

        # Format heading
        if lines:
            heading = lines[0].strip()
            if format_info.heading_style:
                heading = f"{format_info.heading_style}{heading}"
            formatted.append(heading)

        # Format content
        in_list = False
        for line in lines[1:]:
            stripped = line.strip()
            if not stripped:
                if in_list:
                    formatted.append("")
                continue

            # Handle bullet points
            if re.match(r"^[-•*]\s", stripped):
                in_list = True
                line = re.sub(
                    r"^[-•*]\s",
                    f"{format_info.indent}{format_info.bullet_style} ",
                    stripped,
                )
            elif re.match(r"^\d+\.\s", stripped):
                in_list = True
                line = re.sub(r"^\d+\.\s", f"{format_info.indent}1. ", stripped)
            else:
                in_list = False
                line = f"{format_info.indent}{stripped}"

            # Add spacing
            if formatted and not formatted[-1] and not in_list:
                for _ in range(format_info.spacing - 1):
                    formatted.append("")

            formatted.append(line)

        return "\n".join(formatted)

    def merge_sections(self, original: str, updates: Dict[str, str]) -> str:
        """Merge updated sections into original text."""
        result = original
        for section, content in updates.items():
            orig_content, format_info = self.extract_section(result, section)
            if orig_content and format_info:
                formatted = self.apply_format(content, format_info)
                result = result.replace(orig_content, formatted)

        return result

    def validate_format(self, content: str) -> Tuple[bool, List[str]]:
        """Validate content formatting."""
        issues = []

        # Check section headers
        if not re.search(r"^#*\s*[A-Z][A-Z\s]+", content, re.M):
            issues.append("Missing or invalid section headers")

        # Check bullet points and their consistency
        bullet_points = re.finditer(r"^\s*([-•*])\s", content, re.M)
        bullet_styles = set(match.group(1) for match in bullet_points)
        if not bullet_styles:
            issues.append("Missing bullet points")
        elif len(bullet_styles) > 1:
            issues.append("Inconsistent bullet point styles")

        # Check spacing between sections and items
        lines = content.split("\n")
        for i in range(1, len(lines) - 1):
            if not lines[i].strip():
                prev_empty = not lines[i - 1].strip()
                next_empty = not lines[i + 1].strip()
                if prev_empty or next_empty:
                    issues.append("Incorrect spacing between sections")
                    break

        # Check indentation consistency
        indents = {}
        for line in content.split("\n"):
            if line.strip() and line[0].isspace():
                indent_size = len(line) - len(line.lstrip())
                if indent_size not in indents:
                    indents[indent_size] = line
                elif not line.startswith(indents[indent_size][:indent_size]):
                    issues.append("Inconsistent indentation style")
                    break

        # Check bullet point alignment
        bullet_lines = [
            line for line in content.split("\n") if re.match(r"^\s*[-•*]\s", line)
        ]
        if bullet_lines:
            first_indent = len(bullet_lines[0]) - len(bullet_lines[0].lstrip())
            for line in bullet_lines[1:]:
                if len(line) - len(line.lstrip()) != first_indent:
                    issues.append("Misaligned bullet points")
                    break

        # Check metric formatting
        metrics_pattern = (
            r"\b\d+(?:\.\d+)?%|\$\d+(?:,\d{3})*(?:\.\d{2})?|\d+x|"
            r"\b\d+\s*(?:users|customers|clients)\b"
        )
        metrics = re.finditer(metrics_pattern, content)
        for metric in metrics:
            if not re.search(rf"\*\*{re.escape(metric.group())}\*\*", content):
                issues.append("Incorrect formatting of metrics")
                break

        return not bool(issues), issues


class MarkdownFormatter:
    """Handles Markdown-specific formatting."""

    def __init__(self) -> None:
        """Initialize markdown formatter."""
        self.heading_levels = {"main": "#", "sub": "##", "subsub": "###"}

    def format_section(self, title: str, content: str, level: str = "main") -> str:
        """Format a section with proper Markdown."""
        heading = f"{self.heading_levels[level]} {title}\n\n"
        formatted_content = content.strip()

        # Ensure bullet points
        if not re.search(r"^\s*[-•*]\s", formatted_content, re.M):
            formatted_content = "\n".join(
                f"- {line.strip()}"
                for line in formatted_content.split("\n")
                if line.strip()
            )

        return f"{heading}{formatted_content}\n"

    def highlight_metrics(self, content: str) -> str:
        """Highlight metrics in content."""
        patterns = [
            (r"(\d+(?:\.\d+)?%)", r"**\1**"),  # Percentages
            # Money with optional million
            (
                r"(\$\d+(?:,\d{3})*(?:\.\d{2})?(?:\s*[Mm]illion)?)",
                r"**\1**",
            ),
            (r"(\d+)x", r"**\1x**"),  # Multipliers
            # Quantities with various units
            (
                r"(\d+)(?=\s*(?:users|customers|clients|employees|teams|"
                r"projects|features))",
                r"**\1**",
            ),
            # Time periods
            (
                r"(\d+(?:\.\d+)?)\s*(?:hours|days|weeks|months|years)",
                r"**\1**",
            ),
            # Changes and improvements
            (
                r"(\d+(?:\.\d+)?)\s*(?:increase|decrease|improvement|reduction)",
                r"**\1**",
            ),
            (r"(>\s*\d+(?:\.\d+)?%)", r"**\1**"),  # Greater than percentages
        ]

        result = content
        for pattern, replacement in patterns:
            result = re.sub(pattern, replacement, result)

        # Ensure consistent spacing around metrics
        result = re.sub(r"\*\*(\S+)\*\*", r"**\1**", result)  # Remove internal spaces
        result = re.sub(r"(\S)\*\*", r"\1 **", result)  # Add space before
        result = re.sub(r"\*\*(\S)", r"** \1", result)  # Add space after

        return result

    def format_list(self, items: List[str], style: str = "bullet") -> str:
        """Format a list with consistent style."""
        if style == "bullet":
            prefix = "-"
        elif style == "numbered":
            return "\n".join(f"{i + 1}. {item}" for i, item in enumerate(items))
        else:
            prefix = style

        return "\n".join(f"{prefix} {item}" for item in items)

    def clean_whitespace(self, content: str) -> str:
        """Clean up whitespace while preserving formatting."""
        # Remove trailing whitespace
        lines = [line.rstrip() for line in content.split("\n")]

        # Normalize line spacing
        result: List[str] = []
        for i, line in enumerate(lines):
            if not line and i > 0 and i < len(lines) - 1:
                # Keep single blank line between sections
                if result and result[-1] and lines[i + 1]:
                    result.append(line)
            else:
                result.append(line)

        return "\n".join(result)
