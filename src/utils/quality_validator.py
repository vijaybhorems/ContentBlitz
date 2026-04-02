"""Content quality validation utilities."""

from dataclasses import dataclass, field


@dataclass
class ValidationResult:
    """Result of content quality validation."""

    is_valid: bool
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def validate_blog(title: str, body: str, meta: str, min_words: int = 800) -> ValidationResult:
    """Validate a blog post meets minimum quality standards."""
    issues: list[str] = []
    warnings: list[str] = []

    if not title or len(title) < 10:
        issues.append("Title is missing or too short (min 10 chars)")
    elif len(title) > 70:
        warnings.append(f"Title is {len(title)} chars — may be truncated in search results (aim for <70)")

    word_count = len(body.split())
    if word_count < min_words:
        issues.append(f"Body is {word_count} words — minimum is {min_words}")
    if word_count < 200:
        issues.append("Body appears to be empty or stub content")

    if not meta:
        warnings.append("Missing meta description")
    elif len(meta) > 160:
        warnings.append(f"Meta description is {len(meta)} chars — will be truncated (max 160)")

    if "##" not in body:
        warnings.append("No subheadings (H2) found — consider adding for readability")

    return ValidationResult(is_valid=len(issues) == 0, issues=issues, warnings=warnings)


def validate_linkedin(post_text: str, min_chars: int = 100, max_chars: int = 3000) -> ValidationResult:
    """Validate a LinkedIn post meets quality standards."""
    issues: list[str] = []
    warnings: list[str] = []

    char_count = len(post_text)
    if char_count < min_chars:
        issues.append(f"Post is {char_count} chars — minimum is {min_chars}")
    if char_count > max_chars:
        issues.append(f"Post is {char_count} chars — maximum is {max_chars}")

    if not post_text.strip():
        issues.append("Post text is empty")

    # Check for a hook (first line should be engaging)
    first_line = post_text.strip().split("\n")[0] if post_text.strip() else ""
    if len(first_line) < 20:
        warnings.append("Opening hook may be too short — first line should grab attention")

    return ValidationResult(is_valid=len(issues) == 0, issues=issues, warnings=warnings)
