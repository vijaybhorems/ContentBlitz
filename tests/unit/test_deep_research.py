"""Tests for the Deep Research Agent."""

from unittest.mock import AsyncMock

import pytest

from src.agents.deep_research import DeepResearchAgent
from src.core.models import Source


@pytest.fixture
def mock_tavily():
    tavily = AsyncMock()
    tavily.search_multiple = AsyncMock(return_value=[
        Source(url="https://example.com/1", title="Source 1", snippet="Snippet 1 content", relevance_score=0.9),
        Source(url="https://example.com/2", title="Source 2", snippet="Snippet 2 content", relevance_score=0.8),
    ])
    return tavily


@pytest.fixture
def agent(settings, mock_llm_client, mock_tavily):
    return DeepResearchAgent(settings, mock_llm_client, mock_tavily)


class TestDeepResearch:
    @pytest.mark.asyncio
    async def test_generates_search_queries(self, agent):
        agent.llm.generate_json = AsyncMock(
            return_value={"queries": ["query 1", "query 2", "query 3"]}
        )
        queries = await agent._generate_search_queries("AI healthcare", ["AI"])
        assert len(queries) == 3

    @pytest.mark.asyncio
    async def test_fallback_queries_on_llm_failure(self, agent):
        from src.core.exceptions import LLMFallbackExhausted
        agent.llm.generate_json = AsyncMock(side_effect=LLMFallbackExhausted(["LLM down"]))
        queries = await agent._generate_search_queries("AI healthcare", [])
        assert len(queries) >= 2
        assert any("AI healthcare" in q for q in queries)

    @pytest.mark.asyncio
    async def test_process_returns_research_result(self, agent):
        agent.llm.generate_json = AsyncMock(side_effect=[
            {"queries": ["q1", "q2"]},
            {"summary": "Test summary", "key_findings": ["Finding 1"], "content_angles": ["Angle 1"]},
        ])
        state = {
            "target_topic": "AI healthcare",
            "target_keywords": ["AI"],
            "errors": [],
            "processing_log": [],
        }

        result = await agent.process(state)

        assert "research_results" in result
        research = result["research_results"]
        assert research.summary == "Test summary"
        assert len(research.sources) == 2

    @pytest.mark.asyncio
    async def test_empty_results_handled(self, agent, mock_tavily):
        mock_tavily.search_multiple = AsyncMock(return_value=[])
        agent.llm.generate_json = AsyncMock(return_value={"queries": ["q1"]})

        state = {"target_topic": "obscure topic", "errors": [], "processing_log": []}
        result = await agent.process(state)

        assert result["research_results"].summary != ""
        assert len(result["research_results"].sources) == 0

    @pytest.mark.asyncio
    async def test_limits_search_queries(self, agent):
        agent.llm.generate_json = AsyncMock(
            return_value={"queries": ["q1", "q2", "q3", "q4", "q5", "q6", "q7"]}
        )
        queries = await agent._generate_search_queries("test", [])
        assert len(queries) <= 5
