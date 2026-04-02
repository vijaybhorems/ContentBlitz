"""Text processing utilities for content formatting and cleaning."""

import re


def clean_markdown(text: str) -> str:
    """Clean up markdown formatting issues."""
    # Remove excessive blank lines (more than 2 consecutive)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    # Fix broken heading formatting
    text = re.sub(r"^(#{1,6})([^\s#])", r"\1 \2", text, flags=re.MULTILINE)
    return text.strip()


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to max_length, breaking at word boundary."""
    if len(text) <= max_length:
        return text
    truncated = text[: max_length - len(suffix)]
    last_space = truncated.rfind(" ")
    if last_space > max_length * 0.5:
        truncated = truncated[:last_space]
    return truncated + suffix


def count_words(text: str) -> int:
    """Count words in text, ignoring markdown formatting."""
    # Strip markdown syntax
    clean = re.sub(r"[#*_`\[\]\(\)>|-]", " ", text)
    return len(clean.split())


def extract_first_paragraph(markdown: str) -> str:
    """Extract the first non-heading paragraph from markdown."""
    paragraphs = markdown.split("\n\n")
    for p in paragraphs:
        stripped = p.strip()
        if stripped and not stripped.startswith("#") and not stripped.startswith("---"):
            return stripped
    return ""


def format_sources_markdown(sources: list) -> str:
    """Format research sources as a markdown reference list."""
    if not sources:
        return ""
    lines = ["## Sources\n"]
    for i, source in enumerate(sources, 1):
        title = getattr(source, "title", "Untitled")
        url = getattr(source, "url", "")
        lines.append(f"{i}. [{title}]({url})")
    return "\n".join(lines)
