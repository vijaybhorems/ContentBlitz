"""Tests for the Query Handler Agent."""

import json
from unittest.mock import AsyncMock

import pytest

from src.agents.query_handler import QueryHandlerAgent, VALID_INTENTS
from src.core.config import Settings
from src.core.models import LLMResponse


@pytest.fixture
def agent(settings, mock_llm_client):
    return QueryHandlerAgent(settings, mock_llm_client)


class TestQueryHandler:
    @pytest.mark.asyncio
    async def test_classify_blog_intent(self, agent, mock_llm_response):
        agent.llm.generate_json = AsyncMock(
            return_value={"intent": "blog", "topic": "AI in healthcare", "keywords": ["AI", "healthcare"]}
        )
        state = {"user_query": "Write a blog about AI in healthcare", "errors": [], "processing_log": []}

        result = await agent.process(state)

        assert result["intent"] == "blog"
        assert result["target_topic"] == "AI in healthcare"
        assert isinstance(result["target_keywords"], list)

    @pytest.mark.asyncio
    async def test_classify_linkedin_intent(self, agent):
        agent.llm.generate_json = AsyncMock(
            return_value={"intent": "linkedin", "topic": "remote work", "keywords": ["remote"]}
        )
        state = {"user_query": "Create a LinkedIn post about remote work", "errors": [], "processing_log": []}

        result = await agent.process(state)
        assert result["intent"] == "linkedin"

    @pytest.mark.asyncio
    async def test_classify_image_intent(self, agent):
        agent.llm.generate_json = AsyncMock(
            return_value={"intent": "image", "topic": "sustainable energy", "keywords": []}
        )
        state = {"user_query": "Generate an image for sustainable energy", "errors": [], "processing_log": []}

        result = await agent.process(state)
        assert result["intent"] == "image"

    @pytest.mark.asyncio
    async def test_invalid_intent_defaults_to_research(self, agent):
        agent.llm.generate_json = AsyncMock(
            return_value={"intent": "invalid_type", "topic": "test", "keywords": []}
        )
        state = {"user_query": "something ambiguous", "errors": [], "processing_log": []}

        result = await agent.process(state)
        assert result["intent"] == "research"

    @pytest.mark.asyncio
    async def test_missing_intent_defaults_to_research(self, agent):
        agent.llm.generate_json = AsyncMock(return_value={"topic": "test", "keywords": []})
        state = {"user_query": "something", "errors": [], "processing_log": []}

        result = await agent.process(state)
        assert result["intent"] == "research"

    @pytest.mark.asyncio
    async def test_keywords_defaults_to_list(self, agent):
        agent.llm.generate_json = AsyncMock(
            return_value={"intent": "blog", "topic": "test", "keywords": "not_a_list"}
        )
        state = {"user_query": "test", "errors": [], "processing_log": []}

        result = await agent.process(state)
        assert result["target_keywords"] == []

    def test_valid_intents_constant(self):
        assert "blog" in VALID_INTENTS
        assert "linkedin" in VALID_INTENTS
        assert "research" in VALID_INTENTS
        assert "image" in VALID_INTENTS
        assert "strategy" in VALID_INTENTS
