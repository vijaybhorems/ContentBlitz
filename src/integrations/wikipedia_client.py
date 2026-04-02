"""Wikipedia API client for fact verification in the Hallucination Guard."""

import time

from src.core.config import Settings
from src.integrations.base_client import BaseClient
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"


class WikipediaClient(BaseClient):
    """Queries Wikipedia for fact verification."""

    def __init__(self, settings: Settings):
        super().__init__(settings)

    async def search_summary(self, query: str, sentences: int = 3) -> str | None:
        """Get a Wikipedia summary for a query.

        Args:
            query: Search term.
            sentences: Max sentences in the summary.

        Returns:
            Summary text if found, None otherwise.
        """
        try:
            response = await self._request(
                "GET",
                WIKIPEDIA_API,
                params={
                    "action": "query",
                    "list": "search",
                    "srsearch": query,
                    "format": "json",
                    "srlimit": 1,
                },
                max_retries=2,
            )
            data = response.json()
            results = data.get("query", {}).get("search", [])

            if not results:
                return None

            title = results[0]["title"]

            # Fetch the actual summary
            summary_response = await self._request(
                "GET",
                WIKIPEDIA_API,
                params={
                    "action": "query",
                    "titles": title,
                    "prop": "extracts",
                    "exsentences": sentences,
                    "explaintext": True,
                    "format": "json",
                },
                max_retries=2,
            )

            pages = summary_response.json().get("query", {}).get("pages", {})
            for page_id, page_data in pages.items():
                if page_id != "-1":
                    return page_data.get("extract", "")

            return None

        except Exception as e:
            logger.warning("wikipedia_search_failed", query=query, error=str(e))
            return None
