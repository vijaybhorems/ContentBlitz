"""Tavily AI search client for web research."""

import asyncio
from typing import Any

from tavily import AsyncTavilyClient

from src.core.config import Settings
from src.core.models import Source
from src.integrations.circuit_breaker import CircuitBreakerRegistry
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class TavilySearchClient:
    """Wrapper around Tavily AI search API."""

    def __init__(self, settings: Settings, breakers: CircuitBreakerRegistry | None = None):
        self.settings = settings
        self._client: AsyncTavilyClient | None = None
        self._breaker = (breakers or CircuitBreakerRegistry()).get("tavily")

    @property
    def client(self) -> AsyncTavilyClient:
        if self._client is None:
            self._client = AsyncTavilyClient(api_key=self.settings.tavily_api_key)
        return self._client

    async def search(
        self,
        query: str,
        search_depth: str | None = None,
        max_results: int | None = None,
    ) -> list[Source]:
        """Execute a Tavily search and return structured sources.

        Args:
            query: Search query string.
            search_depth: "basic" or "advanced" (default from settings).
            max_results: Override default max results.

        Returns:
            List of Source objects with URL, title, snippet, and relevance score.
        """
        depth = search_depth or self.settings.tavily_search_depth
        limit = max_results or self.settings.tavily_max_results

        logger.info("tavily_search", query=query, depth=depth, max_results=limit)

        if not self._breaker.allow_request():
            logger.warning(
                "tavily_circuit_open",
                query=query,
                retry_after_s=round(self._breaker.time_until_retry(), 1),
            )
            return []

        try:
            response = await self.client.search(
                query=query,
                search_depth=depth,
                max_results=limit,
                include_raw_content=False,
            )
            self._breaker.record_success()
        except Exception as e:
            self._breaker.record_failure()
            logger.error("tavily_search_failed", query=query, error=str(e))
            return []

        results = response.get("results", [])

        sources = []
        for r in results:
            sources.append(
                Source(
                    url=r.get("url", ""),
                    title=r.get("title", ""),
                    snippet=r.get("content", ""),
                    relevance_score=r.get("score", 0.0),
                )
            )

        logger.info("tavily_search_complete", query=query, results_count=len(sources))
        return sources

    async def search_multiple(self, queries: list[str], **kwargs: Any) -> list[Source]:
        """Execute multiple searches in parallel and deduplicate results.

        All queries are fired concurrently with asyncio.gather() instead of
        sequentially, cutting research latency from O(n) to O(1) wall-clock time.

        Args:
            queries: List of search queries.
            **kwargs: Passed to each search call.

        Returns:
            Deduplicated list of Source objects, sorted by relevance.
        """
        # Run all searches concurrently
        results_per_query: list[list[Source]] = await asyncio.gather(
            *[self.search(query, **kwargs) for query in queries]
        )

        # Deduplicate by URL while preserving relevance order
        all_sources: list[Source] = []
        seen_urls: set[str] = set()
        for sources in results_per_query:
            for source in sources:
                if source.url not in seen_urls:
                    seen_urls.add(source.url)
                    all_sources.append(source)

        # Sort by relevance score descending
        all_sources.sort(key=lambda s: s.relevance_score, reverse=True)

        logger.info(
            "tavily_multi_search_complete",
            queries_count=len(queries),
            total_unique_results=len(all_sources),
        )
        return all_sources
