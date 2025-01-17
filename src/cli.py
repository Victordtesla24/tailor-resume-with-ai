"""Command line interface for smart resume app."""

import argparse
import sys

from smart_resume_app.src.keyword_matcher import KeywordMatcher


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(description="Smart Resume Analysis and Tailoring Tool")
    parser.add_argument("--resume", type=str, help="Path to resume file")
    parser.add_argument("--job", type=str, help="Path to job description file")

    args = parser.parse_args()

    if not args.resume or not args.job:
        parser.print_help()
        sys.exit(1)

    # Read files
    try:
        with open(args.resume, "r", encoding="utf-8") as f:
            resume_text = f.read()
        with open(args.job, "r", encoding="utf-8") as f:
            job_text = f.read()
    except FileNotFoundError as e:
        print(f"Error: Could not find file - {e}")
        sys.exit(1)

    # Process resume
    matcher = KeywordMatcher()
    scores = matcher.match_skills(resume_text, job_text)

    # Print results
    print("\nSkill Matches:")
    for skill, score in scores.items():
        status = "✓" if score > 0 else "✗"
        print(f"{status} {skill}")


if __name__ == "__main__":
    main()
