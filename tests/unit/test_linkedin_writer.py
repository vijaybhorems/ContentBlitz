"""Tests for the LinkedIn Post Writer Agent."""

from unittest.mock import AsyncMock

import pytest

from src.agents.linkedin_writer import LinkedInWriterAgent


@pytest.fixture
def agent(settings, mock_llm_client):
    return LinkedInWriterAgent(settings, mock_llm_client)


class TestLinkedInWriter:
    @pytest.mark.asyncio
    async def test_generates_linkedin_post(self, agent, sample_state):
        agent.llm.generate_json = AsyncMock(return_value={
            "post_text": "Did you know AI can detect cancer with 94.5% accuracy?\n\nHere's why that matters...",
            "hashtags": ["#AIHealthcare", "#HealthTech"],
            "hook_type": "statistic",
        })

        result = await agent.process(sample_state)

        assert "linkedin_content" in result
        li = result["linkedin_content"]
        assert li.hook_type == "statistic"
        assert li.character_count > 0
        assert all(h.startswith("#") for h in li.hashtags)

    @pytest.mark.asyncio
    async def test_fixes_hashtags_without_hash(self, agent, sample_state):
        agent.llm.generate_json = AsyncMock(return_value={
            "post_text": "Test post",
            "hashtags": ["AIHealthcare", "#HealthTech", "Innovation"],
            "hook_type": "question",
        })

        result = await agent.process(sample_state)
        hashtags = result["linkedin_content"].hashtags
        assert hashtags == ["#AIHealthcare", "#HealthTech", "#Innovation"]

    @pytest.mark.asyncio
    async def test_handles_empty_hashtags(self, agent, sample_state):
        agent.llm.generate_json = AsyncMock(return_value={
            "post_text": "Test post",
            "hashtags": [],
            "hook_type": "story",
        })

        result = await agent.process(sample_state)
        assert result["linkedin_content"].hashtags == []
