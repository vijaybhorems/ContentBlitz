"""Tests for the A/B Variant Generator Agent."""

from unittest.mock import AsyncMock

import pytest

from src.agents.ab_variant_generator import ABVariantGeneratorAgent
from src.core.models import BlogContent, LinkedInContent, ResearchResult, Source


@pytest.fixture
def agent(settings):
    mock_llm = AsyncMock()
    mock_llm.generate_json = AsyncMock(
        return_value={
            "variants": [
                {
                    "hook_type": "question",
                    "headline": "Are You Missing the AI Healthcare Revolution?",
                    "body_preview": "What if the next breakthrough in your diagnosis came from an algorithm?",
                    "score": 85,
                    "score_breakdown": {
                        "engagement": 18,
                        "clarity": 16,
                        "emotional_impact": 17,
                        "curiosity_gap": 18,
                        "audience_fit": 16,
                    },
                    "rationale": "Question hooks drive 2x more clicks in healthcare content.",
                },
                {
                    "hook_type": "statistic",
                    "headline": "94.5% Accuracy: How AI Outperforms Radiologists",
                    "body_preview": "ML algorithms now detect early-stage cancers with 94.5% accuracy.",
                    "score": 78,
                    "score_breakdown": {
                        "engagement": 16,
                        "clarity": 18,
                        "emotional_impact": 14,
                        "curiosity_gap": 15,
                        "audience_fit": 15,
                    },
                    "rationale": "Statistics build credibility for evidence-based audiences.",
                },
                {
                    "hook_type": "story",
                    "headline": "A Startup's AI Caught What Doctors Missed",
                    "body_preview": "Last quarter, a small medtech startup's algorithm flagged a tumor...",
                    "score": 72,
                    "score_breakdown": {
                        "engagement": 15,
                        "clarity": 14,
                        "emotional_impact": 17,
                        "curiosity_gap": 14,
                        "audience_fit": 12,
                    },
                    "rationale": "Story hooks create emotional connection but may feel less authoritative.",
                },
            ],
            "recommendation": "The question hook variant scores highest because...",
        }
    )
    return ABVariantGeneratorAgent(settings, mock_llm)


@pytest.fixture
def blog_state(sample_research_result):
    return {
        "user_query": "Write a blog about AI in healthcare",
        "intent": "blog",
        "target_topic": "AI in healthcare",
        "target_keywords": ["AI healthcare", "medical AI"],
        "research_results": sample_research_result,
        "blog_content": BlogContent(
            title="AI in Healthcare: Transforming Medicine in 2024",
            meta_description="How AI is revolutionizing diagnostics and treatment.",
            body_markdown="# AI in Healthcare\n\nAI is transforming healthcare through improved diagnostics...",
            word_count=1500,
            keywords_used=["AI healthcare"],
            headers=["AI in Healthcare", "Key Trends"],
        ),
        "errors": [],
        "processing_log": ["query_handler", "deep_research", "seo_blog_writer", "hallucination_guard"],
    }


@pytest.fixture
def linkedin_state(sample_research_result):
    return {
        "user_query": "Create a LinkedIn post about AI in healthcare",
        "intent": "linkedin",
        "target_topic": "AI in healthcare",
        "target_keywords": ["AI healthcare"],
        "research_results": sample_research_result,
        "linkedin_content": LinkedInContent(
            post_text="Did you know AI algorithms now detect cancer with 94.5% accuracy?\n\nKey takeaways...",
            hashtags=["#AIinHealthcare", "#HealthTech"],
            hook_type="statistic",
            character_count=300,
        ),
        "errors": [],
        "processing_log": ["query_handler", "deep_research", "linkedin_writer", "hallucination_guard"],
    }


class TestABVariantGenerator:
    @pytest.mark.asyncio
    async def test_generates_variants_from_blog(self, agent, blog_state):
        """Should produce ranked variants from blog content."""
        result = await agent.process(blog_state)

        assert "ab_variants" in result
        ab = result["ab_variants"]
        assert ab.content_type == "blog"
        assert ab.original_headline == "AI in Healthcare: Transforming Medicine in 2024"
        assert len(ab.variants) == 3
        assert ab.recommendation != ""

    @pytest.mark.asyncio
    async def test_generates_variants_from_linkedin(self, agent, linkedin_state):
        """Should produce ranked variants from LinkedIn content."""
        result = await agent.process(linkedin_state)

        ab = result["ab_variants"]
        assert ab.content_type == "linkedin"
        assert "94.5%" in ab.original_headline
        assert len(ab.variants) == 3

    @pytest.mark.asyncio
    async def test_variants_sorted_by_score(self, agent, blog_state):
        """Variants should be sorted by score descending."""
        result = await agent.process(blog_state)
        scores = [v.score for v in result["ab_variants"].variants]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_each_variant_has_different_hook(self, agent, blog_state):
        """Each variant should use a unique hook type."""
        result = await agent.process(blog_state)
        hooks = [v.hook_type for v in result["ab_variants"].variants]
        assert len(hooks) == len(set(hooks)), f"Duplicate hooks: {hooks}"

    @pytest.mark.asyncio
    async def test_score_breakdown_present(self, agent, blog_state):
        """Each variant should have a score breakdown."""
        result = await agent.process(blog_state)
        for v in result["ab_variants"].variants:
            assert len(v.score_breakdown) > 0
            assert "engagement" in v.score_breakdown

    @pytest.mark.asyncio
    async def test_no_content_returns_empty(self, settings):
        """If no blog or linkedin content in state, return empty."""
        mock_llm = AsyncMock()
        agent = ABVariantGeneratorAgent(settings, mock_llm)

        state = {"user_query": "test", "errors": [], "processing_log": []}
        result = await agent.process(state)
        assert result == {}

    @pytest.mark.asyncio
    async def test_score_clamped_to_range(self, settings):
        """Scores above 100 or below 0 should be clamped."""
        mock_llm = AsyncMock()
        mock_llm.generate_json = AsyncMock(
            return_value={
                "variants": [
                    {"hook_type": "question", "headline": "Test", "score": 150},
                    {"hook_type": "story", "headline": "Test 2", "score": -5},
                ],
                "recommendation": "test",
            }
        )
        agent = ABVariantGeneratorAgent(settings, mock_llm)

        state = {
            "user_query": "test",
            "blog_content": BlogContent(
                title="Test Title",
                meta_description="meta",
                body_markdown="# Test\n\nBody text here.",
                word_count=100,
                keywords_used=["test"],
                headers=["Test"],
            ),
            "errors": [],
            "processing_log": [],
        }
        result = await agent.process(state)
        scores = [v.score for v in result["ab_variants"].variants]
        assert all(0 <= s <= 100 for s in scores)


class TestExtractContent:
    def test_extracts_blog_content(self):
        blog = BlogContent(
            title="Blog Title",
            meta_description="meta",
            body_markdown="# Blog\n\nBody here.",
            word_count=100,
            keywords_used=["test"],
            headers=["Blog"],
        )
        state = {"blog_content": blog}
        content_type, headline, hook, text = ABVariantGeneratorAgent._extract_content(state)
        assert content_type == "blog"
        assert headline == "Blog Title"
        assert hook == "informational"
        assert "Body here" in text

    def test_extracts_linkedin_content(self):
        li = LinkedInContent(
            post_text="Hook line here\n\nMore content follows.",
            hashtags=["#test"],
            hook_type="question",
            character_count=50,
        )
        state = {"linkedin_content": li}
        content_type, headline, hook, text = ABVariantGeneratorAgent._extract_content(state)
        assert content_type == "linkedin"
        assert headline == "Hook line here"
        assert hook == "question"

    def test_empty_state_returns_empty(self):
        state = {}
        content_type, headline, hook, text = ABVariantGeneratorAgent._extract_content(state)
        assert content_type == ""
        assert headline == ""

    def test_blog_preferred_over_linkedin(self):
        """When both are present, blog is extracted."""
        state = {
            "blog_content": BlogContent(
                title="Blog",
                meta_description="meta",
                body_markdown="body",
                word_count=10,
                keywords_used=[],
                headers=[],
            ),
            "linkedin_content": LinkedInContent(
                post_text="LinkedIn",
                hashtags=[],
                hook_type="stat",
                character_count=8,
            ),
        }
        content_type, headline, _, _ = ABVariantGeneratorAgent._extract_content(state)
        assert content_type == "blog"
        assert headline == "Blog"
