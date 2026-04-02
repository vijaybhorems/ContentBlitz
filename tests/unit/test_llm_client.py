"""Tests for the LLM client with fallback logic."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.config import Settings
from src.core.exceptions import LLMError, LLMFallbackExhausted
from src.integrations.llm_client import LLMClient


@pytest.fixture
def llm_client(settings):
    return LLMClient(settings)


def _make_openai_response(content: str):
    mock = MagicMock()
    mock.choices = [MagicMock(message=MagicMock(content=content))]
    mock.usage = MagicMock(prompt_tokens=10, completion_tokens=20, total_tokens=30)
    return mock


def _make_anthropic_response(content: str):
    mock = MagicMock()
    mock.content = [MagicMock(text=content)]
    mock.usage = MagicMock(input_tokens=10, output_tokens=20)
    return mock


class TestLLMClient:
    @pytest.mark.asyncio
    async def test_openai_success(self, llm_client):
        mock_openai = MagicMock()
        mock_openai.chat.completions.create = AsyncMock(
            return_value=_make_openai_response("Hello world")
        )
        llm_client._openai = mock_openai

        result = await llm_client.generate([{"role": "user", "content": "Hi"}])
        assert result.content == "Hello world"
        assert result.provider == "openai"

    @pytest.mark.asyncio
    async def test_fallback_to_anthropic(self, llm_client):
        mock_openai = MagicMock()
        mock_openai.chat.completions.create = AsyncMock(side_effect=Exception("OpenAI down"))
        llm_client._openai = mock_openai

        mock_anthropic = MagicMock()
        mock_anthropic.messages.create = AsyncMock(
            return_value=_make_anthropic_response("Anthropic response")
        )
        llm_client._anthropic = mock_anthropic

        result = await llm_client.generate([{"role": "user", "content": "Hi"}])
        assert result.content == "Anthropic response"
        assert result.provider == "anthropic"

    @pytest.mark.asyncio
    async def test_both_fail_raises(self, llm_client):
        mock_openai = MagicMock()
        mock_openai.chat.completions.create = AsyncMock(side_effect=Exception("OpenAI down"))
        llm_client._openai = mock_openai

        mock_anthropic = MagicMock()
        mock_anthropic.messages.create = AsyncMock(side_effect=Exception("Anthropic down"))
        llm_client._anthropic = mock_anthropic

        with pytest.raises(LLMFallbackExhausted) as exc_info:
            await llm_client.generate([{"role": "user", "content": "Hi"}])
        assert len(exc_info.value.errors) == 2

    @pytest.mark.asyncio
    async def test_no_api_keys(self):
        client = LLMClient(Settings(openai_api_key="", anthropic_api_key=""))
        with pytest.raises(LLMFallbackExhausted):
            await client.generate([{"role": "user", "content": "Hi"}])

    @pytest.mark.asyncio
    async def test_generate_json_valid(self, llm_client):
        mock_openai = MagicMock()
        mock_openai.chat.completions.create = AsyncMock(
            return_value=_make_openai_response('{"key": "value"}')
        )
        llm_client._openai = mock_openai

        result = await llm_client.generate_json([{"role": "user", "content": "Give JSON"}])
        assert result == {"key": "value"}

    @pytest.mark.asyncio
    async def test_generate_json_code_block(self, llm_client):
        mock_openai = MagicMock()
        mock_openai.chat.completions.create = AsyncMock(
            return_value=_make_openai_response('```json\n{"key": "value"}\n```')
        )
        llm_client._openai = mock_openai

        result = await llm_client.generate_json([{"role": "user", "content": "Give JSON"}])
        assert result == {"key": "value"}

    @pytest.mark.asyncio
    async def test_generate_json_invalid_raises(self, llm_client):
        mock_openai = MagicMock()
        mock_openai.chat.completions.create = AsyncMock(
            return_value=_make_openai_response("not json at all")
        )
        llm_client._openai = mock_openai

        with pytest.raises(LLMError):
            await llm_client.generate_json([{"role": "user", "content": "Give JSON"}])

    @pytest.mark.asyncio
    async def test_anthropic_system_extraction(self, llm_client):
        """Verify system messages are extracted for Anthropic API format."""
        llm_client.settings.openai_api_key = ""  # Force Anthropic

        mock_anthropic = MagicMock()
        mock_anthropic.messages.create = AsyncMock(
            return_value=_make_anthropic_response("Response")
        )
        llm_client._anthropic = mock_anthropic

        await llm_client.generate([
            {"role": "system", "content": "Be helpful"},
            {"role": "user", "content": "Hello"},
        ])

        call_kwargs = mock_anthropic.messages.create.call_args[1]
        assert call_kwargs["system"] == "Be helpful"
        assert len(call_kwargs["messages"]) == 1
