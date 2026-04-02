"""Tests for the Image Generation Agent."""

from unittest.mock import AsyncMock

import pytest

from src.agents.image_generation import ImageGenerationAgent
from src.core.exceptions import APIError, ImageGenerationError
from src.core.models import ImageResult


@pytest.fixture
def mock_dalle():
    client = AsyncMock()
    client.generate = AsyncMock(return_value=ImageResult(
        image_url="https://example.com/image.png",
        prompt_used="test prompt",
        provider="dalle3",
    ))
    return client


@pytest.fixture
def mock_stability():
    client = AsyncMock()
    client.generate = AsyncMock(return_value=ImageResult(
        image_base64="base64data",
        prompt_used="test prompt",
        provider="stability",
    ))
    return client


@pytest.fixture
def agent(settings, mock_llm_client, mock_dalle, mock_stability):
    return ImageGenerationAgent(settings, mock_llm_client, mock_dalle, mock_stability)


class TestImageGeneration:
    @pytest.mark.asyncio
    async def test_generates_image_with_dalle(self, agent):
        agent.llm.generate_json = AsyncMock(return_value={"prompt": "A futuristic city"})

        state = {"target_topic": "future cities", "errors": [], "processing_log": []}
        result = await agent.process(state)

        assert "image_result" in result
        assert result["image_result"].provider == "dalle3"
        assert result["image_result"].image_url is not None

    @pytest.mark.asyncio
    async def test_falls_back_to_stability(self, agent, mock_dalle):
        mock_dalle.generate = AsyncMock(side_effect=APIError("dalle3", "Rate limited"))
        agent.llm.generate_json = AsyncMock(return_value={"prompt": "A futuristic city"})

        state = {"target_topic": "future cities", "errors": [], "processing_log": []}
        result = await agent.process(state)

        assert result["image_result"].provider == "stability"

    @pytest.mark.asyncio
    async def test_both_providers_fail(self, agent, mock_dalle, mock_stability):
        mock_dalle.generate = AsyncMock(side_effect=APIError("dalle3", "Error"))
        mock_stability.generate = AsyncMock(side_effect=APIError("stability", "Error"))
        agent.llm.generate_json = AsyncMock(return_value={"prompt": "test"})

        state = {"target_topic": "test", "errors": [], "processing_log": []}

        # The base agent's run() catches exceptions and returns errors
        result = await agent.run(state)
        assert result.get("errors")

    @pytest.mark.asyncio
    async def test_prompt_engineering_fallback(self, agent):
        from src.core.exceptions import LLMFallbackExhausted
        agent.llm.generate_json = AsyncMock(side_effect=LLMFallbackExhausted(["LLM failed"]))

        prompt = await agent._engineer_prompt("test topic")
        assert "test topic" in prompt.lower()
