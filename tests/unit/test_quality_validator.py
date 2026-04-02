"""Tests for content quality validation."""

from src.utils.quality_validator import validate_blog, validate_linkedin


class TestValidateBlog:
    def test_valid_blog(self):
        result = validate_blog(
            title="AI in Healthcare Guide",
            body="## Intro\n\nThis is a comprehensive guide. " + "Content here with many words to reach the minimum. " * 200,
            meta="Good meta description for the blog post",
        )
        assert result.is_valid is True
        assert len(result.issues) == 0

    def test_short_title(self):
        result = validate_blog(title="Hi", body="Content " * 200, meta="Meta")
        assert result.is_valid is False

    def test_short_body(self):
        result = validate_blog(title="Valid Title Here", body="Short body", meta="Meta")
        assert result.is_valid is False

    def test_missing_headings_warning(self):
        result = validate_blog(title="Valid Title Here", body="Content " * 200, meta="Meta")
        assert any("subheading" in w.lower() or "h2" in w.lower() for w in result.warnings)

    def test_long_meta_warning(self):
        result = validate_blog(title="Valid Title Here", body="Content " * 200, meta="x" * 200)
        assert any("meta" in w.lower() for w in result.warnings)


class TestValidateLinkedIn:
    def test_valid_post(self):
        result = validate_linkedin("This is a LinkedIn post with enough content. " * 5)
        assert result.is_valid is True

    def test_too_short(self):
        result = validate_linkedin("Hi")
        assert result.is_valid is False

    def test_too_long(self):
        result = validate_linkedin("x" * 3500)
        assert result.is_valid is False

    def test_empty(self):
        result = validate_linkedin("")
        assert result.is_valid is False
