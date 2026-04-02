"""DALL-E 3 image generation client."""

import time
from typing import Optional

import openai

from src.core.config import Settings
from src.core.exceptions import APIError
from src.core.models import ImageResult
from src.integrations.circuit_breaker import CircuitBreaker, CircuitBreakerRegistry
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class OpenAIImageClient:
    """Generates images using DALL-E 3 via OpenAI API."""

    def __init__(self, settings: Settings, breakers: CircuitBreakerRegistry | None = None):
        self.settings = settings
        self._client: Optional[openai.AsyncOpenAI] = None
        self._breaker = (breakers or CircuitBreakerRegistry()).get("dalle3")

    @property
    def client(self) -> openai.AsyncOpenAI:
        if self._client is None:
            self._client = openai.AsyncOpenAI(
                api_key=self.settings.openai_api_key,
                timeout=self.settings.api_timeout,
            )
        return self._client

    async def generate(
        self,
        prompt: str,
        size: str | None = None,
        quality: str | None = None,
    ) -> ImageResult:
        """Generate an image using DALL-E 3.

        Args:
            prompt: Image generation prompt.
            size: Image size (default from settings).
            quality: "standard" or "hd".

        Returns:
            ImageResult with URL and prompt details.

        Raises:
            APIError: On generation failure.
        """
        if not self._breaker.allow_request():
            raise APIError("dalle3", f"Circuit breaker OPEN (retry in {self._breaker.time_until_retry():.0f}s)")

        start = time.monotonic()

        try:
            response = await self.client.images.generate(
                model=self.settings.dalle_model,
                prompt=prompt,
                size=size or self.settings.image_size,
                quality=quality or self.settings.image_quality,
                n=1,
            )
            duration_ms = (time.monotonic() - start) * 1000

            image_data = response.data[0]
            result = ImageResult(
                image_url=image_data.url,
                prompt_used=prompt,
                revised_prompt=image_data.revised_prompt,
                provider="dalle3",
            )

            self._breaker.record_success()
            logger.info(
                "image_generated",
                provider="dalle3",
                duration_ms=round(duration_ms, 1),
                has_revised_prompt=bool(image_data.revised_prompt),
            )
            return result

        except openai.BadRequestError as e:
            # Content policy violations are not provider failures — don't trip the breaker
            logger.warning("dalle_content_policy", error=str(e))
            raise APIError("dalle3", f"Content policy violation: {e}")
        except Exception as e:
            self._breaker.record_failure()
            logger.error("dalle_generation_failed", error=str(e))
            raise APIError("dalle3", str(e))
