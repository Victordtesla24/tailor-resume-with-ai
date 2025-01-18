"""UI components for the resume tailoring app."""

import difflib
from typing import Dict, List, Optional, Tuple
import streamlit as st
from docx.document import Document


def setup_custom_styling() -> None:
    """Set up custom CSS styling for the app."""
    st.markdown(
        """
        <style>
        /* Modern UI Theme */
        .stApp {
            background: linear-gradient(to bottom right, #ffffff, #f8f9fa);
        }
        
        /* Card-like containers */
        .container {
            background: white;
            padding: 2rem;
            border-radius: 1rem;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            margin: 1rem 0;
            transition: transform 0.2s ease;
        }
        
        .container:hover {
            transform: translateY(-2px);
        }
        
        /* Comparison View */
        .comparison-container {
            display: flex;
            gap: 2rem;
            margin: 1rem 0;
        }
        
        .original, .tailored {
            flex: 1;
            padding: 1.5rem;
            border-radius: 1rem;
            background: white;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
            transition: all 0.3s ease;
        }
        
        .original:hover, .tailored:hover {
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
        }
        
        /* Diff Highlighting */
        .diff-add {
            background-color: #e6ffe6;
            padding: 0.2rem 0.4rem;
            border-radius: 0.2rem;
            animation: highlight-add 0.5s ease;
        }
        
        .diff-remove {
            background-color: #ffe6e6;
            text-decoration: line-through;
            padding: 0.2rem 0.4rem;
            border-radius: 0.2rem;
            animation: highlight-remove 0.5s ease;
        }
        
        /* Progress Indicator */
        .progress-container {
            margin: 1rem 0;
            padding: 1rem;
            background: white;
            border-radius: 0.5rem;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        }
        
        /* Inline Editing */
        .editable-section {
            padding: 1rem;
            border: 1px solid #e9ecef;
            border-radius: 0.5rem;
            margin: 0.5rem 0;
            transition: border-color 0.3s ease;
        }
        
        .editable-section:focus-within {
            border-color: #80bdff;
            box-shadow: 0 0 0 0.2rem rgba(0, 123, 255, 0.25);
        }
        
        /* ATS Score */
        .ats-score {
            text-align: center;
            padding: 1rem;
            background: white;
            border-radius: 1rem;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
            transition: transform 0.3s ease;
        }
        
        .ats-score:hover {
            transform: scale(1.02);
        }
        
        /* Animations */
        @keyframes highlight-add {
            from { background-color: transparent; }
            to { background-color: #e6ffe6; }
        }
        
        @keyframes highlight-remove {
            from { background-color: transparent; }
            to { background-color: #ffe6e6; }
        }
        
        /* Button Styling */
        .stButton button {
            border-radius: 0.5rem;
            transition: all 0.3s ease;
        }
        
        .stButton button:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


class ATSScorer:
    """ATS scoring and keyword analysis."""

    def __init__(self):
        """Initialize ATS scorer."""
        self.previous_score = None

    def calculate_score(
        self, resume_text: str, job_description: str
    ) -> Tuple[float, Dict[str, float]]:
        """Calculate ATS match score and keyword matches."""
        # Extract keywords from job description
        job_keywords = self._extract_keywords(job_description)

        # Calculate matches
        keyword_scores = {}
        total_matches = 0

        for keyword in job_keywords:
            if keyword.lower() in resume_text.lower():
                score = 1.0
                total_matches += 1
            else:
                score = 0.0
            keyword_scores[keyword] = score

        # Calculate overall score
        overall_score = (total_matches / len(job_keywords)) * 100 if job_keywords else 0

        return overall_score, keyword_scores

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract relevant keywords from text."""
        # Simple keyword extraction (can be enhanced with NLP)
        words = set(
            word.strip().lower() for word in text.split() if len(word) > 3 and word.isalnum()
        )
        return list(words)

    def display_score(self, score: float, keyword_scores: Dict[str, float]) -> None:
        """Display ATS score and keyword matches."""
        with st.container():
            st.markdown('<div class="ats-score">', unsafe_allow_html=True)

            # Display overall score
            delta = None
            if self.previous_score is not None:
                delta = score - self.previous_score

            st.metric("ATS Match Score", f"{score:.1f}%", delta=f"{delta:.1f}%" if delta else None)

            # Display keyword matches
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("### Keyword Matches")
                for keyword, match_score in keyword_scores.items():
                    if match_score > 0:
                        st.markdown(f"✅ {keyword}")

            with col2:
                st.markdown("### Missing Keywords")
                for keyword, match_score in keyword_scores.items():
                    if match_score == 0:
                        st.markdown(f"❌ {keyword}")

            st.markdown("</div>", unsafe_allow_html=True)

            self.previous_score = score


class InlineEditor:
    """Inline editing component with change tracking."""

    def edit_section(self, section_name: str, content: str) -> Optional[str]:
        """Create an inline-editable section with change tracking."""
        if f"edit_{section_name}" not in st.session_state:
            st.session_state[f"edit_{section_name}"] = content
            st.session_state[f"history_{section_name}"] = [content]
            st.session_state[f"history_index_{section_name}"] = 0

        st.markdown('<div class="editable-section">', unsafe_allow_html=True)

        # Edit area
        edited_content = st.text_area(
            f"Edit {section_name}",
            value=st.session_state[f"edit_{section_name}"],
            height=200,
            key=f"textarea_{section_name}",
        )

        # Control buttons
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("Save Changes", key=f"save_{section_name}"):
                if edited_content != st.session_state[f"edit_{section_name}"]:
                    st.session_state[f"edit_{section_name}"] = edited_content
                    history = st.session_state[f"history_{section_name}"]
                    history.append(edited_content)
                    st.session_state[f"history_index_{section_name}"] = len(history) - 1
                    return str(edited_content)

        with col2:
            if st.button("Undo", key=f"undo_{section_name}"):
                history_index = st.session_state[f"history_index_{section_name}"]
                if history_index > 0:
                    history_index -= 1
                    st.session_state[f"history_index_{section_name}"] = history_index
                    st.session_state[f"edit_{section_name}"] = st.session_state[
                        f"history_{section_name}"
                    ][history_index]

        with col3:
            if st.button("Redo", key=f"redo_{section_name}"):
                history_index = st.session_state[f"history_index_{section_name}"]
                history = st.session_state[f"history_{section_name}"]
                if history_index < len(history) - 1:
                    history_index += 1
                    st.session_state[f"history_index_{section_name}"] = history_index
                    st.session_state[f"edit_{section_name}"] = history[history_index]

        st.markdown("</div>", unsafe_allow_html=True)
        return None


class ComparisonView:
    """Enhanced side-by-side comparison with diff highlighting."""

    def __init__(self):
        """Initialize comparison view."""
        self.differ = difflib.Differ()

    def _highlight_differences(self, original: str, modified: str) -> Tuple[str, str]:
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

    def display_comparison(  # type: ignore
        self, original_doc: Document, modified_text: str, *, preserve_formatting: bool = True
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
        st.markdown('<div class="container">', unsafe_allow_html=True)
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

        st.markdown("</div>", unsafe_allow_html=True)
        return selected
