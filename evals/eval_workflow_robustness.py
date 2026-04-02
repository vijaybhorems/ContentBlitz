"""Eval: End-to-End Workflow Robustness.

Runs the full LangGraph pipeline on diverse queries with mocked LLM/Tavily
and verifies:
- Workflow completes without error
- Correct agents are invoked (processing_log)
- Expected output fields are populated (not None)
- Unexpected output fields remain None (no cross-contamination)
- State has no error entries

Metrics:
- Completion rate
- Agent routing accuracy
- Output validity rate

Run:
    pytest evals/eval_workflow_robustness.py -v --tb=short
"""

import json
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.config import Settings
from src.workflow.graph import build_graph


DATA_PATH = Path(__file__).parent / "data" / "workflow_cases.json"


def _load_cases() -> list[dict]:
    with open(DATA_PATH) as f:
        return json.load(f)


CASES = _load_cases()

# Canned LLM responses keyed by intent.
INTENT_RESPONSES = {
    "blog": [
        '{{"intent": "blog", "topic": "{topic}", "keywords": ["{kw}"]}}',
        '{{"queries": ["{topic} trends", "{topic} best practices"]}}',
        '{{"summary": "Research summary about {topic}.", "key_findings": ["Finding 1", "Finding 2"], "content_angles": ["Angle 1"]}}',
        '{{"title": "{topic} Guide", "meta_description": "Guide to {topic}.", '
        '"body_markdown": "# {topic}\\n\\n## Introduction\\n\\nIntroduction to {topic}.\\n\\n## Details\\n\\nDetails about {topic}. '
        + "word " * 500
        + '", "keywords_used": ["{kw}"], "headers": ["Introduction", "Details"]}}',
        '{{"claims": [{{"text": "claim about {topic}", "status": "verified", "source_match": "source 1", "confidence": 0.9}}], "recommendations": []}}',
        # ab_variant_generator
        '{{"variants": [{{"hook_type": "question", "headline": "Is {topic} the future?", "body_preview": "What if...", '
        '"score": 80, "score_breakdown": {{"engagement": 16, "clarity": 16, "emotional_impact": 16, "curiosity_gap": 16, "audience_fit": 16}}, '
        '"rationale": "Questions drive clicks."}}], "recommendation": "Use question hook."}}',
    ],
    "linkedin": [
        '{{"intent": "linkedin", "topic": "{topic}", "keywords": ["{kw}"]}}',
        '{{"queries": ["{topic} trends"]}}',
        '{{"summary": "Research summary about {topic}.", "key_findings": ["Finding 1"], "content_angles": ["Angle 1"]}}',
        '{{"post_text": "Excited to share insights about {topic}!\\n\\n1. Key point one\\n2. Key point two\\n\\n#Innovation", '
        '"hashtags": ["#Innovation", "#Tech"], "hook_type": "question", "character_count": 180}}',
        '{{"claims": [{{"text": "claim about {topic}", "status": "verified", "source_match": "source 1", "confidence": 0.85}}], "recommendations": []}}',
        # ab_variant_generator
        '{{"variants": [{{"hook_type": "statistic", "headline": "The numbers on {topic}", "body_preview": "Data shows...", '
        '"score": 75, "score_breakdown": {{"engagement": 15, "clarity": 15, "emotional_impact": 15, "curiosity_gap": 15, "audience_fit": 15}}, '
        '"rationale": "Statistics build trust."}}], "recommendation": "Use statistic hook."}}',
    ],
    "research": [
        '{{"intent": "research", "topic": "{topic}", "keywords": ["{kw}"]}}',
        '{{"queries": ["{topic} trends", "{topic} analysis"]}}',
        '{{"summary": "Research summary about {topic}.", "key_findings": ["Finding 1", "Finding 2"], "content_angles": ["Angle 1"]}}',
        '{{"title": "{topic} Strategy", "executive_summary": "Strategic insights about {topic}.", '
        '"sections": [{{"heading": "Overview", "content": "Overview of {topic}.", "data_points": ["Data 1"]}}], '
        '"content_angles": ["Angle 1", "Angle 2"]}}',
    ],
    "strategy": [
        '{{"intent": "strategy", "topic": "{topic}", "keywords": ["{kw}"]}}',
        '{{"queries": ["{topic} trends", "{topic} strategy"]}}',
        '{{"summary": "Strategic research about {topic}.", "key_findings": ["Finding 1"], "content_angles": ["Angle 1"]}}',
        '{{"title": "{topic} Strategy", "executive_summary": "Strategic brief on {topic}.", '
        '"sections": [{{"heading": "Analysis", "content": "Analysis of {topic}.", "data_points": ["Point 1"]}}], '
        '"content_angles": ["Angle 1"]}}',
    ],
    "image": [
        '{{"intent": "image", "topic": "{topic}", "keywords": ["{kw}"]}}',
        '{{"prompt": "A professional illustration of {topic}, digital art style, clean and modern"}}',
    ],
}


def _make_openai_response(content: str):
    mock = MagicMock()
    mock.choices = [MagicMock(message=MagicMock(content=content))]
    mock.usage = MagicMock(prompt_tokens=10, completion_tokens=20, total_tokens=30)
    return mock


def _build_mock_sequence(intent: str, topic: str, keyword: str):
    """Build the sequence of LLM responses for a given intent."""
    templates = INTENT_RESPONSES.get(intent, INTENT_RESPONSES["research"])
    return [t.format(topic=topic, kw=keyword) for t in templates]


@pytest.fixture
def settings():
    return Settings(
        openai_api_key="sk-test",
        anthropic_api_key="sk-ant-test",
        tavily_api_key="tvly-test",
        stability_api_key="sk-test-stability",
        redis_url=None,
    )


def _make_openai_mock(side_effect):
    """Create a mock OpenAI client that supports both chat completions and image generation.

    Because llm_client and openai_image_client both import the same `openai` module,
    patching openai.AsyncOpenAI once covers both. The mock must support both
    .chat.completions.create() and .images.generate().
    """
    mock = MagicMock()
    mock.chat.completions.create = AsyncMock(side_effect=side_effect)

    # Image generation mock
    img_response = MagicMock()
    img_response.data = [MagicMock(
        b64_json=None,
        url="https://example.com/image.png",
        revised_prompt=None,
    )]
    mock.images.generate = AsyncMock(return_value=img_response)
    return mock


class TestWorkflowRobustness:
    """Parameterized end-to-end workflow tests."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "case",
        CASES,
        ids=[c["name"] for c in CASES],
    )
    async def test_workflow_case(self, settings, case):
        """Run a single workflow case and verify all assertions."""
        intent = case["expected_intent"]
        topic = case["query"][:40].replace('"', '\\"')
        keyword = topic.split()[-1] if topic.split() else "topic"

        responses = _build_mock_sequence(intent, topic, keyword)
        call_count = {"n": 0}

        async def mock_create(**kwargs):
            idx = call_count["n"]
            call_count["n"] += 1
            content = responses[idx] if idx < len(responses) else "{}"
            return _make_openai_response(content)

        mock_tavily_results = {
            "results": [
                {
                    "title": f"Source about {topic}",
                    "url": "https://example.com/source",
                    "content": f"Information about {topic} from research.",
                    "score": 0.9,
                },
            ]
        }

        # Patch openai.AsyncOpenAI once (shared by llm_client and openai_image_client)
        with (
            patch("openai.AsyncOpenAI") as MockOpenAI,
            patch("anthropic.AsyncAnthropic") as MockAnthropic,
            patch("src.integrations.tavily_client.AsyncTavilyClient") as MockTavily,
        ):
            MockOpenAI.return_value = _make_openai_mock(mock_create)
            MockAnthropic.return_value = MagicMock()

            mock_tavily = MagicMock()
            mock_tavily.search = AsyncMock(return_value=mock_tavily_results)
            MockTavily.return_value = mock_tavily

            graph = build_graph(settings)
            config = {"configurable": {"thread_id": uuid.uuid4().hex}}
            result = await graph.ainvoke(
                {
                    "user_query": case["query"],
                    "errors": [],
                    "processing_log": [],
                },
                config=config,
            )

        # 1. Verify no errors
        errors = result.get("errors", [])
        assert len(errors) == 0, f"Workflow errors: {errors}"

        # 2. Verify correct intent classification
        assert result.get("intent") == intent, (
            f"Expected intent '{intent}', got '{result.get('intent')}'"
        )

        # 3. Verify expected agents ran (check processing_log)
        log = result.get("processing_log", [])
        for agent in case["expected_agents"]:
            assert agent in log, (
                f"Agent '{agent}' not in processing_log: {log}"
            )

        # 4. Verify expected outputs are populated
        for output_key in case["expected_outputs"]:
            assert result.get(output_key) is not None, (
                f"Expected output '{output_key}' is None. "
                f"Processing log: {log}"
            )

        # 5. Verify unexpected outputs are NOT populated (no cross-contamination)
        for output_key in case.get("unexpected_outputs", []):
            assert result.get(output_key) is None, (
                f"Unexpected output '{output_key}' is present but shouldn't be. "
                f"Intent: {intent}, Processing log: {log}"
            )


class TestWorkflowErrorRecovery:
    """Test that the workflow handles agent failures gracefully."""

    @pytest.mark.asyncio
    async def test_llm_failure_produces_error_in_state(self, settings):
        """If the LLM fails during an agent, the error is recorded in state."""
        async def mock_create_fail(**kwargs):
            raise Exception("LLM timeout")

        with (
            patch("openai.AsyncOpenAI") as MockOpenAI,
            patch("anthropic.AsyncAnthropic") as MockAnthropic,
            patch("src.integrations.tavily_client.AsyncTavilyClient") as MockTavily,
        ):
            mock_openai = MagicMock()
            mock_openai.chat.completions.create = AsyncMock(side_effect=mock_create_fail)
            MockOpenAI.return_value = mock_openai

            mock_anthropic = MagicMock()
            mock_anthropic.messages.create = AsyncMock(side_effect=Exception("Anthropic down"))
            MockAnthropic.return_value = mock_anthropic

            mock_tavily = MagicMock()
            mock_tavily.search = AsyncMock(return_value={"results": []})
            MockTavily.return_value = mock_tavily

            graph = build_graph(settings)
            config = {"configurable": {"thread_id": uuid.uuid4().hex}}
            result = await graph.ainvoke(
                {
                    "user_query": "Write a blog about AI",
                    "errors": [],
                    "processing_log": [],
                },
                config=config,
            )

        # Should have errors in state from the failed agent
        errors = result.get("errors", [])
        assert len(errors) > 0, "Expected errors in state when LLM fails"

    @pytest.mark.asyncio
    async def test_empty_query_still_completes(self, settings):
        """Workflow should handle an empty/minimal query without crashing."""
        responses = _build_mock_sequence("research", "general", "general")
        call_count = {"n": 0}

        async def mock_create(**kwargs):
            idx = call_count["n"]
            call_count["n"] += 1
            return _make_openai_response(responses[idx] if idx < len(responses) else "{}")

        with (
            patch("openai.AsyncOpenAI") as MockOpenAI,
            patch("anthropic.AsyncAnthropic") as MockAnthropic,
            patch("src.integrations.tavily_client.AsyncTavilyClient") as MockTavily,
        ):
            MockOpenAI.return_value = _make_openai_mock(mock_create)
            MockAnthropic.return_value = MagicMock()

            mock_tavily = MagicMock()
            mock_tavily.search = AsyncMock(return_value={"results": []})
            MockTavily.return_value = mock_tavily

            graph = build_graph(settings)
            config = {"configurable": {"thread_id": uuid.uuid4().hex}}
            result = await graph.ainvoke(
                {
                    "user_query": "",
                    "errors": [],
                    "processing_log": [],
                },
                config=config,
            )

        # Should complete (may have errors, but shouldn't crash)
        assert "processing_log" in result


class TestWorkflowMetrics:
    """Aggregate metrics across all cases."""

    @pytest.mark.asyncio
    async def test_all_intents_covered_in_cases(self):
        """Every intent type has at least 2 workflow test cases."""
        intent_counts = {}
        for case in CASES:
            intent = case["expected_intent"]
            intent_counts[intent] = intent_counts.get(intent, 0) + 1

        for intent in ["blog", "linkedin", "research", "image", "strategy"]:
            assert intent_counts.get(intent, 0) >= 2, (
                f"Intent '{intent}' has only {intent_counts.get(intent, 0)} cases (need >= 2)"
            )

    @pytest.mark.asyncio
    async def test_edge_cases_included(self):
        """Dataset includes edge cases (minimal, vague, long, special chars)."""
        names = {c["name"] for c in CASES}
        edge_cases = [n for n in names if n.startswith("edge_")]
        assert len(edge_cases) >= 3, (
            f"Only {len(edge_cases)} edge cases found: {edge_cases}"
        )
