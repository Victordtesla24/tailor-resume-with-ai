"""UI components for the resume tailoring app."""

import difflib
from typing import Dict, List

import streamlit as st
from docx.document import Document


def setup_custom_styling():
    """Set up custom CSS styling for the app."""
    st.markdown(
        """
        <style>
        .comparison-container {
            display: flex;
            gap: 2rem;
        }
        .original, .tailored {
            flex: 1;
            padding: 1rem;
            border-radius: 0.5rem;
            background: #f8f9fa;
        }
        .diff-add {
            background-color: #e6ffe6;
        }
        .diff-remove {
            background-color: #ffe6e6;
            text-decoration: line-through;
        }
        .progress-container {
            margin: 1rem 0;
        }
        </style>
    """,
        unsafe_allow_html=True,
    )


class ComparisonView:
    """Enhanced side-by-side comparison with diff highlighting."""

    def __init__(self):
        """Initialize comparison view."""
        self.differ = difflib.Differ()

    def _highlight_differences(self, original: str, modified: str) -> tuple[str, str]:
        """Highlight differences between original and modified text."""
        diff = list(self.differ.compare(original.splitlines(), modified.splitlines()))

        orig_html = []
        mod_html = []

        for line in diff:
            if line.startswith("  "):
                orig_html.append(f"<div>{line[2:]}</div>")
                mod_html.append(f"<div>{line[2:]}</div>")
            elif line.startswith("- "):
                orig_html.append(f'<div class="diff-remove">{line[2:]}</div>')
            elif line.startswith("+ "):
                mod_html.append(f'<div class="diff-add">{line[2:]}</div>')

        return "\n".join(orig_html), "\n".join(mod_html)

    def display_comparison(
        self,
        original_doc: Document,
        modified_text: str,
        *,
        preserve_formatting: bool = True,
    ) -> None:
        """Display side-by-side comparison with highlighting."""
        original_text = "\n".join(p.text for p in original_doc.paragraphs)
        orig_html, mod_html = self._highlight_differences(original_text, modified_text)

        st.markdown(
            f"""
            <div class="comparison-container">
                <div class="original">
                    <h3>Original Resume</h3>
                    {orig_html}
                </div>
                <div class="tailored">
                    <h3>Tailored Resume</h3>
                    {mod_html}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


class ProgressIndicator:
    """Progress indicator for resume processing."""

    def __init__(self):
        """Initialize progress tracking."""
        if "progress_step" not in st.session_state:
            st.session_state.progress_step = 0
        self.total_steps = 5

    def start(self) -> None:
        """Start progress tracking."""
        st.session_state.progress_step = 0
        self._update_progress()

    def next_step(self) -> None:
        """Move to next step."""
        st.session_state.progress_step += 1
        self._update_progress()

    def _update_progress(self) -> None:
        """Update progress bar."""
        progress = st.session_state.progress_step / self.total_steps
        st.progress(progress)

        steps = [
            "Extracting resume content...",
            "Analyzing job requirements...",
            "Matching skills...",
            "Generating tailored content...",
            "Preserving formatting...",
        ]

        if st.session_state.progress_step < len(steps):
            st.markdown(
                f'<div class="progress-container">'
                f"{steps[st.session_state.progress_step]}"
                f"</div>",
                unsafe_allow_html=True,
            )


class SectionSelector:
    """Enhanced section selection with preview."""

    def display_selector(self, sections: Dict[str, str]) -> List[str]:
        """Display enhanced section selection interface."""
        st.subheader("Select Sections to Tailor")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### Available Sections")
            selected = []
            for section, content in sections.items():
                preview = content[:100] + "..." if len(content) > 100 else content
                if st.checkbox(f"{section.title()}", help=f"Preview: {preview}"):
                    selected.append(section)

        with col2:
            if selected:
                st.markdown("### Selected Sections Preview")
                for section in selected:
                    with st.expander(f"{section.title()} Preview"):
                        st.text(sections[section])
            else:
                st.warning("Please select at least one section to tailor")

        # Show optimization suggestions
        if selected:
            st.markdown("### Optimization Suggestions")
            for section in selected:
                with st.expander(f"Tips for {section.title()}"):
                    if "summary" in section.lower():
                        st.info(
                            "• Focus on solution architecture experience\n"
                            "• Highlight cloud transformation expertise"
                        )
                    elif "experience" in section.lower():
                        st.info(
                            "• Quantify architectural achievements\n"
                            "• Emphasize technical leadership"
                        )
                    elif "skills" in section.lower():
                        st.info("• Add cloud platforms expertise\n" "• Include architecture tools")
                    elif "education" in section.lower():
                        st.info(
                            "• Highlight relevant certifications\n"
                            "• Emphasize technical background"
                        )

        return selected
