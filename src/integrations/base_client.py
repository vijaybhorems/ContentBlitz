"""Abstract base client with retry logic, timeouts, and structured logging."""

import time
from abc import ABC
from typing import Any, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from src.core.config import Settings
from src.utils.logging_config import get_logger


class BaseClient(ABC):
    """Base class for all external API clients.

    Provides httpx session management, retry logic, and structured logging.
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = get_logger(self.__class__.__name__)
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.settings.api_timeout),
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
            )
        return self._client

    async def _request(
        self,
        method: str,
        url: str,
        max_retries: int | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """Make an HTTP request with retry and logging.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            max_retries: Override default retry count
            **kwargs: Passed to httpx request

        Returns:
            httpx.Response on success

        Raises:
            httpx.HTTPStatusError: On non-2xx response after retries
        """
        retries = max_retries or self.settings.max_retries
        last_error: Exception | None = None

        for attempt in range(1, retries + 1):
            start = time.monotonic()
            try:
                response = await self.client.request(method, url, **kwargs)
                duration_ms = (time.monotonic() - start) * 1000

                self.logger.info(
                    "api_request",
                    method=method,
                    url=url,
                    status_code=response.status_code,
                    duration_ms=round(duration_ms, 1),
                    attempt=attempt,
                )

                response.raise_for_status()
                return response

            except (httpx.HTTPStatusError, httpx.RequestError, httpx.TimeoutException) as e:
                duration_ms = (time.monotonic() - start) * 1000
                last_error = e
                self.logger.warning(
                    "api_request_failed",
                    method=method,
                    url=url,
                    error=str(e),
                    attempt=attempt,
                    max_retries=retries,
                    duration_ms=round(duration_ms, 1),
                )

                if attempt < retries:
                    backoff = self.settings.retry_backoff * (2 ** (attempt - 1))
                    import asyncio
                    await asyncio.sleep(backoff)

        raise last_error  # type: ignore[misc]

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
