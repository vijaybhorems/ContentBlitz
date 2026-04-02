"""Integration tests for LLM and image generation fallback chains."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.config import Settings
from src.core.exceptions import LLMFallbackExhausted
from src.integrations.llm_client import LLMClient


@pytest.fixture
def settings():
    return Settings(
        openai_api_key="sk-test",
        anthropic_api_key="sk-ant-test",
    )


def _make_anthropic_response(content: str):
    mock = MagicMock()
    mock.content = [MagicMock(text=content)]
    mock.usage = MagicMock(input_tokens=10, output_tokens=20)
    return mock


@pytest.mark.asyncio
@pytest.mark.integration
async def test_llm_openai_to_anthropic_fallback(settings):
    """OpenAI fails → Anthropic succeeds."""
    client = LLMClient(settings)

    mock_openai = MagicMock()
    mock_openai.chat.completions.create = AsyncMock(side_effect=Exception("Rate limited"))
    client._openai = mock_openai

    mock_anthropic = MagicMock()
    mock_anthropic.messages.create = AsyncMock(
        return_value=_make_anthropic_response("Fallback response")
    )
    client._anthropic = mock_anthropic

    result = await client.generate([
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "Hello"},
    ])

    assert result.provider == "anthropic"
    assert result.content == "Fallback response"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_llm_both_providers_fail(settings):
    """Both OpenAI and Anthropic fail → raises LLMFallbackExhausted."""
    client = LLMClient(settings)

    mock_openai = MagicMock()
    mock_openai.chat.completions.create = AsyncMock(side_effect=Exception("OpenAI down"))
    client._openai = mock_openai

    mock_anthropic = MagicMock()
    mock_anthropic.messages.create = AsyncMock(side_effect=Exception("Anthropic down"))
    client._anthropic = mock_anthropic

    with pytest.raises(LLMFallbackExhausted) as exc_info:
        await client.generate([{"role": "user", "content": "Hello"}])

    assert "OpenAI" in str(exc_info.value)
    assert "Anthropic" in str(exc_info.value)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_anthropic_system_message_extraction(settings):
    """Verify system messages are extracted correctly for Anthropic."""
    client = LLMClient(settings)

    # Force Anthropic by disabling OpenAI
    client.settings.openai_api_key = ""

    mock_anthropic = MagicMock()
    mock_anthropic.messages.create = AsyncMock(
        return_value=_make_anthropic_response("Response")
    )
    client._anthropic = mock_anthropic

    await client.generate([
        {"role": "system", "content": "Be helpful"},
        {"role": "user", "content": "Hello"},
    ])

    # Verify system was passed separately
    call_kwargs = mock_anthropic.messages.create.call_args[1]
    assert call_kwargs["system"] == "Be helpful"
    assert len(call_kwargs["messages"]) == 1  # Only user message
    assert call_kwargs["messages"][0]["role"] == "user"
