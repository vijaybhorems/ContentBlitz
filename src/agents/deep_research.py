"""Deep Research Agent — conducts comprehensive web research using Tavily."""

from typing import Any

from src.agents.base_agent import BaseAgent
from src.core.exceptions import ContentBlitzError
from src.core.models import ResearchResult, Source
from src.core.state import ContentState
from src.integrations.tavily_client import TavilySearchClient


class DeepResearchAgent(BaseAgent):
    """Performs multi-query web research, deduplicates sources, and synthesizes findings."""

    agent_name = "deep_research"

    def __init__(self, settings, llm_client, tavily_client: TavilySearchClient):
        super().__init__(settings, llm_client)
        self.tavily = tavily_client

    async def process(self, state: ContentState) -> dict[str, Any]:
        topic = state.get("target_topic", state.get("user_query", ""))
        keywords = state.get("target_keywords", [])

        # Step 1: Generate diverse search queries
        search_queries = await self._generate_search_queries(topic, keywords)
        self.logger.info("search_queries_generated", count=len(search_queries), queries=search_queries)

        # Step 2: Execute searches and deduplicate
        sources = await self.tavily.search_multiple(search_queries)
        self.logger.info("sources_collected", total=len(sources))

        if not sources:
            self.logger.warning("no_sources_found", topic=topic)
            return {
                "research_results": ResearchResult(
                    query=topic,
                    summary="No research results found for this topic.",
                    search_queries_used=search_queries,
                ),
            }

        # Step 3: Synthesize research
        raw_snippets = [s.snippet for s in sources]
        synthesis = await self._synthesize_research(topic, sources)

        research = ResearchResult(
            query=topic,
            sources=sources,
            summary=synthesis.get("summary", ""),
            key_findings=synthesis.get("key_findings", []),
            raw_snippets=raw_snippets,
            search_queries_used=search_queries,
        )

        self.logger.info(
            "research_complete",
            sources_count=len(sources),
            findings_count=len(research.key_findings),
            summary_length=len(research.summary),
        )

        return {"research_results": research}

    async def _generate_search_queries(self, topic: str, keywords: list[str]) -> list[str]:
        """Use LLM to generate diverse search queries for the topic."""
        keyword_context = f"\nRelevant keywords: {', '.join(keywords)}" if keywords else ""

        messages = self._build_messages(
            f"Generate 4 diverse search queries to research the following topic thoroughly.\n\n"
            f"Topic: {topic}{keyword_context}\n\n"
            f"Create queries from different angles: factual/definitional, trends/statistics, "
            f"challenges/criticism, and future outlook.\n\n"
            f'Respond with JSON: {{"queries": ["query1", "query2", "query3", "query4"]}}'
        )

        try:
            result = await self.llm.generate_json(messages)
            queries = result.get("queries", [])
            if queries and isinstance(queries, list):
                return queries[:5]
        except ContentBlitzError as e:
            self.logger.warning("query_generation_failed", error=str(e))

        # Fallback: generate basic queries from the topic
        return [
            f"{topic} overview",
            f"{topic} latest trends statistics",
            f"{topic} challenges and opportunities",
        ]

    async def _synthesize_research(self, topic: str, sources: list[Source]) -> dict:
        """Use LLM to synthesize research from collected sources."""
        source_text = "\n\n".join(
            f"Source: {s.title} ({s.url})\n{s.snippet}" for s in sources[:10]
        )

        messages = self._build_messages(
            f"Synthesize the following research sources about '{topic}' into a comprehensive summary.\n\n"
            f"SOURCES:\n{source_text}\n\n"
            f"Provide a JSON response with:\n"
            f'- "summary": A comprehensive 200-400 word synthesis\n'
            f'- "key_findings": A list of 5-8 specific, data-backed findings\n'
            f'- "content_angles": 3-5 suggested angles for content creation'
        )

        try:
            return await self.llm.generate_json(messages)
        except ContentBlitzError as e:
            self.logger.warning("synthesis_failed_using_basic", error=str(e))
            return {
                "summary": f"Research collected {len(sources)} sources about {topic}.",
                "key_findings": [s.snippet[:200] for s in sources[:5]],
                "content_angles": [f"Overview of {topic}"],
            }
