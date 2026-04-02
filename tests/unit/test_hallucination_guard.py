"""Tests for the Hallucination Guard Agent."""

from unittest.mock import AsyncMock

import pytest

from src.agents.hallucination_guard import HallucinationGuardAgent
from src.core.models import BlogContent, LinkedInContent


@pytest.fixture
def agent(settings, mock_llm_client):
    return HallucinationGuardAgent(settings, mock_llm_client)


class TestHallucinationGuard:
    @pytest.mark.asyncio
    async def test_fact_checks_blog_content(self, agent, sample_state, sample_blog_content):
        sample_state["blog_content"] = sample_blog_content

        agent.llm.generate_json = AsyncMock(return_value={
            "claims": [
                {"text": "Market projected at $187.95B", "status": "verified", "source_match": "source 1", "confidence": 0.95},
                {"text": "94.5% accuracy in detection", "status": "verified", "source_match": "source 2", "confidence": 0.9},
                {"text": "Made up statistic", "status": "unsupported", "source_match": None, "confidence": 0.3},
            ],
            "recommendations": ["Consider removing unsupported claim about made up statistic"],
        })

        result = await agent.process(sample_state)

        fc = result["fact_check_result"]
        assert fc.total_claims == 3
        assert fc.verified_claims == 2
        assert len(fc.flagged_claims) == 1
        assert 60 < fc.trust_score < 70  # 2/3 ≈ 66.7

    @pytest.mark.asyncio
    async def test_no_content_returns_perfect_score(self, agent):
        state = {"errors": [], "processing_log": []}
        result = await agent.process(state)
        assert result["fact_check_result"].trust_score == 100.0

    @pytest.mark.asyncio
    async def test_no_research_returns_warning(self, agent, sample_blog_content):
        state = {"blog_content": sample_blog_content, "errors": [], "processing_log": []}
        result = await agent.process(state)
        assert result["fact_check_result"].trust_score == 50.0
        assert len(result["fact_check_result"].recommendations) > 0

    @pytest.mark.asyncio
    async def test_all_claims_verified(self, agent, sample_state, sample_blog_content):
        sample_state["blog_content"] = sample_blog_content

        agent.llm.generate_json = AsyncMock(return_value={
            "claims": [
                {"text": "Claim 1", "status": "verified", "source_match": "s1", "confidence": 0.9},
                {"text": "Claim 2", "status": "verified", "source_match": "s2", "confidence": 0.95},
            ],
            "recommendations": [],
        })

        result = await agent.process(sample_state)
        assert result["fact_check_result"].trust_score == 100.0
        assert len(result["fact_check_result"].flagged_claims) == 0

    def test_get_content_to_check_blog(self, agent, sample_blog_content):
        state = {"blog_content": sample_blog_content}
        content = agent._get_content_to_check(state)
        assert sample_blog_content.title in content

    def test_get_content_to_check_linkedin(self, agent, sample_linkedin_content):
        state = {"linkedin_content": sample_linkedin_content}
        content = agent._get_content_to_check(state)
        assert content == sample_linkedin_content.post_text

    def test_get_content_to_check_empty(self, agent):
        state = {}
        content = agent._get_content_to_check(state)
        assert content == ""
