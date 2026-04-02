"""Tests for the SEO Blog Writer Agent."""

from unittest.mock import AsyncMock

import pytest

from src.agents.seo_blog_writer import SEOBlogWriterAgent


@pytest.fixture
def agent(settings, mock_llm_client):
    return SEOBlogWriterAgent(settings, mock_llm_client)


class TestSEOBlogWriter:
    @pytest.mark.asyncio
    async def test_generates_blog_content(self, agent, sample_state):
        agent.llm.generate_json = AsyncMock(return_value={
            "title": "AI in Healthcare: A Complete Guide",
            "meta_description": "Discover how AI transforms healthcare with diagnostics and drug discovery.",
            "body_markdown": "# AI in Healthcare\n\n## Introduction\n\nAI is transforming " + "word " * 1400,
            "keywords_used": ["AI healthcare"],
            "headers": ["Introduction", "Key Trends"],
        })

        result = await agent.process(sample_state)

        assert "blog_content" in result
        blog = result["blog_content"]
        assert blog.title == "AI in Healthcare: A Complete Guide"
        assert blog.word_count > 0
        assert len(blog.meta_description) <= 160

    @pytest.mark.asyncio
    async def test_extracts_headers_from_markdown(self, agent):
        headers = agent._extract_headers(
            "# Title\n\n## Section One\n\nText\n\n### Subsection\n\n## Section Two\n\nMore text"
        )
        assert "Section One" in headers
        assert "Subsection" in headers
        assert "Section Two" in headers
        # H1 should NOT be extracted (we only extract H2 and H3)
        assert "Title" not in headers

    @pytest.mark.asyncio
    async def test_handles_missing_research(self, agent):
        agent.llm.generate_json = AsyncMock(return_value={
            "title": "Test Title",
            "meta_description": "Test meta",
            "body_markdown": "# Test\n\nContent here " + "word " * 200,
            "keywords_used": [],
            "headers": [],
        })

        state = {"target_topic": "test topic", "target_keywords": [], "errors": [], "processing_log": []}
        result = await agent.process(state)
        assert result["blog_content"].title == "Test Title"

    @pytest.mark.asyncio
    async def test_truncates_meta_description(self, agent, sample_state):
        agent.llm.generate_json = AsyncMock(return_value={
            "title": "Test",
            "meta_description": "x" * 200,  # Over 160 chars
            "body_markdown": "# Test\n\nContent",
            "keywords_used": [],
            "headers": [],
        })

        result = await agent.process(sample_state)
        assert len(result["blog_content"].meta_description) <= 160
