"""Integration test: Blog post workflow end-to-end with mocked APIs."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.config import Settings
from src.core.models import Source
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
async def test_blog_workflow_end_to_end(settings):
    """Test: user asks for blog → query_handler → deep_research → blog_writer → hallucination_guard."""

    # Sequence of LLM responses for each agent call
    llm_responses = [
        # 1. Query handler
        '{"intent": "blog", "topic": "AI in healthcare", "keywords": ["AI healthcare"]}',
        # 2. Deep research - query generation
        '{"queries": ["AI healthcare trends", "AI medical diagnosis"]}',
        # 3. Deep research - synthesis
        '{"summary": "AI is transforming healthcare.", "key_findings": ["Finding 1"], "content_angles": ["Angle 1"]}',
        # 4. SEO blog writer
        '{"title": "AI in Healthcare Guide", "meta_description": "Complete guide to AI in healthcare.", '
        '"body_markdown": "# AI in Healthcare\\n\\n## Introduction\\n\\nAI is transforming healthcare.\\n\\n'
        '## Key Trends\\n\\n- Trend 1\\n- Trend 2\\n\\n### Details\\n\\nMore details here. ' + 'word ' * 500 + '",'
        '"keywords_used": ["AI healthcare"], "headers": ["Introduction", "Key Trends"]}',
        # 5. Hallucination guard
        '{"claims": [{"text": "AI is transforming healthcare", "status": "verified", "source_match": "source 1", "confidence": 0.9}], '
        '"recommendations": []}',
        # 6. A/B variant generator
        '{"variants": [{"hook_type": "question", "headline": "Is AI the Future of Healthcare?", "body_preview": "What if...", '
        '"score": 82, "score_breakdown": {"engagement": 17, "clarity": 16, "emotional_impact": 17, "curiosity_gap": 16, "audience_fit": 16}, '
        '"rationale": "Questions drive engagement."}], "recommendation": "Use the question hook."}',
    ]
    call_count = {"n": 0}

    async def mock_openai_create(**kwargs):
        idx = call_count["n"]
        call_count["n"] += 1
        content = llm_responses[idx] if idx < len(llm_responses) else '{"error": "unexpected call"}'
        return _make_openai_response(content)

    # Mock Tavily
    mock_tavily_results = {
        "results": [
            {"title": "AI Healthcare", "url": "https://example.com/1", "content": "AI transforms healthcare.", "score": 0.9},
        ]
    }

    with patch("src.integrations.llm_client.openai.AsyncOpenAI") as MockOpenAI, \
         patch("src.integrations.tavily_client.AsyncTavilyClient") as MockTavily:

        mock_openai = MagicMock()
        mock_openai.chat.completions.create = AsyncMock(side_effect=mock_openai_create)
        MockOpenAI.return_value = mock_openai

        mock_tavily = MagicMock()
        mock_tavily.search = AsyncMock(return_value=mock_tavily_results)
        MockTavily.return_value = mock_tavily

        graph = build_graph(settings)
        config = {"configurable": {"thread_id": uuid.uuid4().hex}}
        result = await graph.ainvoke(
            {
                "user_query": "Write a blog about AI in healthcare",
                "errors": [],
                "processing_log": [],
            },
            config=config,
        )

    # Verify the workflow executed correctly
    assert result["intent"] == "blog"
    assert result["target_topic"] == "AI in healthcare"

    # Verify processing log has all expected agents
    log = result.get("processing_log", [])
    assert "query_handler" in log
    assert "deep_research" in log
    assert "seo_blog_writer" in log
    assert "hallucination_guard" in log
    assert "ab_variant_generator" in log

    # Verify blog was generated
    assert result.get("blog_content") is not None
    assert result["blog_content"].title == "AI in Healthcare Guide"

    # Verify fact check ran
    assert result.get("fact_check_result") is not None
    assert result["fact_check_result"].trust_score > 0

    # Verify A/B variants generated
    assert result.get("ab_variants") is not None
    assert len(result["ab_variants"].variants) >= 1
