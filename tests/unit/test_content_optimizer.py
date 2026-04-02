"""Tests for SEO content optimization utilities."""

import pytest

from src.utils.content_optimizer import calculate_seo_score, estimate_reading_time


class TestSEOScore:
    def test_perfect_blog(self):
        title = "AI in Healthcare: Complete Guide to Medical AI"
        body = (
            "# AI in Healthcare\n\n"
            "AI in healthcare is transforming medicine. " * 20 + "\n\n"
            "## Key Trends in AI Healthcare\n\n"
            "Here are the trends:\n\n"
            "- **Trend 1**: Diagnostics improvement\n"
            "- **Trend 2**: Drug discovery acceleration\n\n" +
            "The AI in healthcare market continues to grow. " * 50 + "\n\n"
            "## Challenges of AI in Healthcare\n\n"
            "Some challenges include:\n\n"
            "1. Data privacy\n"
            "2. Algorithmic bias\n\n" +
            "More content about AI in healthcare here. " * 30 + "\n\n"
            "### Implementation Strategies\n\n"
            "Strategies for implementing AI in healthcare:\n\n" +
            "Additional content. " * 20
        )
        meta = "Discover how AI in healthcare transforms medicine with improved diagnostics and drug discovery."

        score = calculate_seo_score(title, body, meta, "AI in healthcare")
        assert score.overall >= 60
        assert score.keyword_in_title is True
        assert score.heading_structure is True

    def test_missing_keyword_in_title(self):
        score = calculate_seo_score(
            "Complete Guide to Medical Technology",
            "## Section\n\nContent about AI in healthcare " * 100,
            "Meta description about AI.",
            "AI in healthcare",
        )
        assert score.keyword_in_title is False

    def test_empty_body(self):
        score = calculate_seo_score("Title", "", "Meta", "keyword")
        assert score.overall < 50
        assert score.word_count_ok is False

    def test_meta_description_length(self):
        # Good length
        score = calculate_seo_score("T", "body " * 300, "x" * 140, "keyword")
        assert score.meta_description_length is True

        # Too short
        score = calculate_seo_score("T", "body " * 300, "short", "keyword")
        assert score.meta_description_length is False


class TestReadingTime:
    def test_typical_article(self):
        assert estimate_reading_time(1500) == 6

    def test_short_content(self):
        assert estimate_reading_time(100) == 1

    def test_zero_words(self):
        assert estimate_reading_time(0) == 1
