"""Unified LLM client with OpenAI primary and Anthropic fallback."""

import json
import time
from typing import Any, Optional

import anthropic
import openai

from src.core.config import Settings
from src.core.exceptions import LLMError, LLMFallbackExhausted
from src.core.models import LLMResponse
from src.integrations.circuit_breaker import CircuitBreakerRegistry, CircuitOpenError
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class LLMClient:
    """Unified interface for LLM generation with automatic fallback.

    Tries OpenAI GPT-4o first; on any failure, falls back to Anthropic Claude.
    Circuit breakers prevent repeated calls to providers that are down.
    """

    def __init__(self, settings: Settings, breakers: CircuitBreakerRegistry | None = None):
        self.settings = settings
        self._openai: Optional[openai.AsyncOpenAI] = None
        self._anthropic: Optional[anthropic.AsyncAnthropic] = None
        self._breakers = breakers or CircuitBreakerRegistry(
            failure_threshold=3, recovery_timeout=30.0,
        )

    @property
    def openai_client(self) -> openai.AsyncOpenAI:
        if self._openai is None:
            self._openai = openai.AsyncOpenAI(
                api_key=self.settings.openai_api_key,
                timeout=self.settings.api_timeout,
            )
        return self._openai

    @property
    def anthropic_client(self) -> anthropic.AsyncAnthropic:
        if self._anthropic is None:
            self._anthropic = anthropic.AsyncAnthropic(
                api_key=self.settings.anthropic_api_key,
                timeout=self.settings.api_timeout,
            )
        return self._anthropic

    async def generate(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        json_mode: bool = False,
    ) -> LLMResponse:
        """Generate a response using LLM with automatic fallback.

        Args:
            messages: List of {"role": "...", "content": "..."} dicts.
            model: Override default model (provider auto-detected).
            temperature: Override default temperature.
            max_tokens: Override default max_tokens.
            json_mode: Request JSON output format.

        Returns:
            LLMResponse with content, model, provider, and usage.

        Raises:
            LLMFallbackExhausted: If both providers fail.
        """
        temp = temperature if temperature is not None else self.settings.llm_temperature
        tokens = max_tokens or self.settings.llm_max_tokens
        errors: list[str] = []

        # Try OpenAI first
        openai_breaker = self._breakers.get("openai")
        if self.settings.openai_api_key and openai_breaker.allow_request():
            try:
                result = await self._call_openai(
                    messages,
                    model=model or self.settings.openai_model,
                    temperature=temp,
                    max_tokens=tokens,
                    json_mode=json_mode,
                )
                openai_breaker.record_success()
                return result
            except Exception as e:
                openai_breaker.record_failure()
                error_msg = f"OpenAI: {e}"
                errors.append(error_msg)
                logger.warning("openai_failed", error=str(e), falling_back_to="anthropic")
        elif self.settings.openai_api_key:
            errors.append(f"OpenAI: circuit breaker OPEN (retry in {openai_breaker.time_until_retry():.0f}s)")
            logger.warning(
                "openai_circuit_open",
                retry_after_s=round(openai_breaker.time_until_retry(), 1),
            )

        # Fallback to Anthropic
        anthropic_breaker = self._breakers.get("anthropic")
        if self.settings.anthropic_api_key and anthropic_breaker.allow_request():
            try:
                result = await self._call_anthropic(
                    messages,
                    model=model if model and "claude" in model else self.settings.anthropic_model,
                    temperature=temp,
                    max_tokens=tokens,
                )
                anthropic_breaker.record_success()
                return result
            except Exception as e:
                anthropic_breaker.record_failure()
                error_msg = f"Anthropic: {e}"
                errors.append(error_msg)
                logger.error("anthropic_failed", error=str(e))
        elif self.settings.anthropic_api_key:
            errors.append(f"Anthropic: circuit breaker OPEN (retry in {anthropic_breaker.time_until_retry():.0f}s)")
            logger.warning(
                "anthropic_circuit_open",
                retry_after_s=round(anthropic_breaker.time_until_retry(), 1),
            )

        raise LLMFallbackExhausted(errors or ["No API keys configured"])

    async def _call_openai(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
        json_mode: bool = False,
    ) -> LLMResponse:
        """Call OpenAI API."""
        start = time.monotonic()

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = await self.openai_client.chat.completions.create(**kwargs)
        duration_ms = (time.monotonic() - start) * 1000

        content = response.choices[0].message.content or ""
        usage = {
            "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
            "completion_tokens": response.usage.completion_tokens if response.usage else 0,
            "total_tokens": response.usage.total_tokens if response.usage else 0,
        }

        logger.info(
            "llm_call",
            provider="openai",
            model=model,
            duration_ms=round(duration_ms, 1),
            tokens=usage.get("total_tokens", 0),
        )

        return LLMResponse(content=content, model=model, provider="openai", usage=usage)

    async def _call_anthropic(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> LLMResponse:
        """Call Anthropic API, translating OpenAI message format."""
        start = time.monotonic()

        # Extract system message if present
        system_content = ""
        chat_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_content = msg["content"]
            else:
                chat_messages.append(msg)

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": chat_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if system_content:
            kwargs["system"] = system_content

        response = await self.anthropic_client.messages.create(**kwargs)
        duration_ms = (time.monotonic() - start) * 1000

        content = response.content[0].text if response.content else ""
        usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
        }

        logger.info(
            "llm_call",
            provider="anthropic",
            model=model,
            duration_ms=round(duration_ms, 1),
            tokens=usage.get("total_tokens", 0),
        )

        return LLMResponse(content=content, model=model, provider="anthropic", usage=usage)

    async def generate_json(
        self,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> dict:
        """Generate and parse a JSON response.

        Tries json_mode first (OpenAI), falls back to parsing raw text.

        Returns:
            Parsed JSON dict.

        Raises:
            LLMError: If response is not valid JSON.
        """
        response = await self.generate(messages, json_mode=True, **kwargs)
        try:
            return json.loads(response.content)
        except json.JSONDecodeError:
            # Try extracting JSON from markdown code block
            content = response.content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            try:
                return json.loads(content)
            except json.JSONDecodeError as e:
                raise LLMError(response.provider, f"Invalid JSON response: {e}")

    async def generate_json_fast(
        self,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> dict:
        """Like generate_json() but forces the fast/cheap model (gpt-4o-mini).

        Use for lightweight tasks: intent classification, safety checks,
        fact verification, A/B scoring — anything that doesn't need frontier
        model quality. Typically 5-10x faster and cheaper than generate_json().
        """
        return await self.generate_json(
            messages,
            model=self.settings.openai_model_fast,
            **kwargs,
        )
