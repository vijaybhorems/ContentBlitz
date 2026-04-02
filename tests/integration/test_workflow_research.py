"""Integration test: Research workflow end-to-end with mocked APIs."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.config import Settings
from src.workflow.graph import build_graph


@pytest.fixture
def settings():
    return Settings(
        openai_api_key="sk-test",
        anthropic_api_key="sk-ant-test",
        tavily_api_key="tvly-test",
        redis_url=None,
    )


def _make_openai_response(content: str):
    mock = MagicMock()
    mock.choices = [MagicMock(message=MagicMock(content=content))]
    mock.usage = MagicMock(prompt_tokens=10, completion_tokens=20, total_tokens=30)
    return mock


@pytest.mark.asyncio
@pytest.mark.integration
async def test_research_workflow(settings):
    """Test: research intent → query_handler → deep_research → content_strategist → END."""

    llm_responses = [
        # Query handler
        '{"intent": "research", "topic": "quantum computing", "keywords": ["quantum"]}',
        # Deep research - queries
        '{"queries": ["quantum computing advances", "quantum computing applications"]}',
        # Deep research - synthesis
        '{"summary": "Quantum computing is advancing rapidly.", "key_findings": ["Finding 1"], "content_angles": ["Angle 1"]}',
        # Content strategist
        '{"title": "Quantum Computing Strategy", "executive_summary": "Key insights into quantum computing.", '
        '"sections": [{"heading": "Overview", "content": "Quantum computing overview.", "data_points": ["Data 1"]}], '
        '"content_angles": ["Enterprise angle", "Research angle"]}',
    ]
    call_count = {"n": 0}

    async def mock_create(**kwargs):
        idx = call_count["n"]
        call_count["n"] += 1
        return _make_openai_response(llm_responses[idx] if idx < len(llm_responses) else '{}')

    mock_tavily_results = {
        "results": [
            {"title": "Quantum Advances", "url": "https://example.com/q", "content": "Quantum is advancing.", "score": 0.85},
        ]
    }

    with patch("src.integrations.llm_client.openai.AsyncOpenAI") as MockOpenAI, \
         patch("src.integrations.tavily_client.AsyncTavilyClient") as MockTavily:

        mock_openai = MagicMock()
        mock_openai.chat.completions.create = AsyncMock(side_effect=mock_create)
        MockOpenAI.return_value = mock_openai

        mock_tavily = MagicMock()
        mock_tavily.search = AsyncMock(return_value=mock_tavily_results)
        MockTavily.return_value = mock_tavily

        graph = build_graph(settings)
        config = {"configurable": {"thread_id": uuid.uuid4().hex}}
        result = await graph.ainvoke(
            {
                "user_query": "Research quantum computing",
                "errors": [],
                "processing_log": [],
            },
            config=config,
        )

    assert result["intent"] == "research"
    log = result.get("processing_log", [])
    assert "query_handler" in log
    assert "deep_research" in log
    assert "content_strategist" in log

    # Should NOT have blog or linkedin content
    assert result.get("blog_content") is None
    assert result.get("linkedin_content") is None

    # Should have strategy report
    assert result.get("strategy_report") is not None
    assert result["strategy_report"].title == "Quantum Computing Strategy"
