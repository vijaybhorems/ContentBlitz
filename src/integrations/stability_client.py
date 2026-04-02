"""Stability AI image generation client (fallback provider)."""

import base64
import time

from src.core.config import Settings
from src.core.exceptions import APIError
from src.core.models import ImageResult
from src.integrations.base_client import BaseClient
from src.integrations.circuit_breaker import CircuitBreakerRegistry
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class StabilityClient(BaseClient):
    """Generates images using Stability AI SDXL API."""

    API_BASE = "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0"

    def __init__(self, settings: Settings, breakers: CircuitBreakerRegistry | None = None):
        super().__init__(settings)
        self._breaker = (breakers or CircuitBreakerRegistry()).get("stability")

    async def generate(
        self,
        prompt: str,
        width: int = 1024,
        height: int = 1024,
        steps: int = 30,
    ) -> ImageResult:
        """Generate an image using Stability AI SDXL.

        Args:
            prompt: Image generation prompt.
            width: Image width.
            height: Image height.
            steps: Number of diffusion steps.

        Returns:
            ImageResult with base64 image data.

        Raises:
            APIError: On generation failure.
        """
        if not self._breaker.allow_request():
            raise APIError("stability", f"Circuit breaker OPEN (retry in {self._breaker.time_until_retry():.0f}s)")

        start = time.monotonic()

        try:
            response = await self._request(
                "POST",
                f"{self.API_BASE}/text-to-image",
                headers={
                    "Authorization": f"Bearer {self.settings.stability_api_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                json={
                    "text_prompts": [{"text": prompt, "weight": 1.0}],
                    "cfg_scale": 7,
                    "width": width,
                    "height": height,
                    "steps": steps,
                    "samples": 1,
                },
            )

            duration_ms = (time.monotonic() - start) * 1000
            data = response.json()
            artifacts = data.get("artifacts", [])

            if not artifacts:
                raise APIError("stability", "No image generated")

            result = ImageResult(
                image_base64=artifacts[0]["base64"],
                prompt_used=prompt,
                provider="stability",
            )

            self._breaker.record_success()
            logger.info(
                "image_generated",
                provider="stability",
                duration_ms=round(duration_ms, 1),
            )
            return result

        except APIError:
            self._breaker.record_failure()
            raise
        except Exception as e:
            self._breaker.record_failure()
            logger.error("stability_generation_failed", error=str(e))
            raise APIError("stability", str(e))
