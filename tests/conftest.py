"""Shared test fixtures for ContentBlitz."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.config import Settings
from src.core.models import (
    BlogContent,
    Claim,
    FactCheckResult,
    ImageResult,
    LinkedInContent,
    LLMResponse,
    ResearchResult,
    Source,
    StrategyReport,
)
from src.core.state import ContentState


@pytest.fixture
def settings():
    """Test settings with dummy API keys."""
    return Settings(
        openai_api_key="sk-test-openai-key",
        anthropic_api_key="sk-ant-test-key",
        tavily_api_key="tvly-test-key",
        stability_api_key="sk-test-stability",
        environment="development",
        log_level="DEBUG",
        redis_url=None,
    )


@pytest.fixture
def sample_sources():
    """Realistic research sources."""
    return [
        Source(
            url="https://example.com/ai-healthcare-2024",
            title="AI in Healthcare: 2024 Trends and Innovations",
            snippet="Artificial intelligence is transforming healthcare through improved diagnostics, "
            "personalized treatment plans, and streamlined administrative processes. "
            "The global AI in healthcare market is projected to reach $187.95 billion by 2030.",
            relevance_score=0.95,
        ),
        Source(
            url="https://example.com/machine-learning-diagnosis",
            title="Machine Learning for Medical Diagnosis",
            snippet="Recent studies show ML algorithms achieving 94.5% accuracy in detecting early-stage "
            "cancers from medical imaging, outperforming human radiologists in several blind tests.",
            relevance_score=0.88,
        ),
        Source(
            url="https://example.com/ai-drug-discovery",
            title="AI-Powered Drug Discovery Revolution",
            snippet="AI-driven drug discovery has reduced the average time from target identification to "
            "clinical trials from 4.5 years to approximately 18 months, saving pharmaceutical "
            "companies an estimated $2.6 billion per drug.",
            relevance_score=0.82,
        ),
        Source(
            url="https://example.com/healthcare-challenges",
            title="Challenges of Implementing AI in Healthcare",
            snippet="Key challenges include data privacy concerns with HIPAA compliance, algorithmic bias "
            "in underrepresented populations, and the need for regulatory frameworks that keep pace "
            "with technological advancement.",
            relevance_score=0.75,
        ),
        Source(
            url="https://example.com/future-health-ai",
            title="The Future of AI-Assisted Healthcare",
            snippet="Experts predict that by 2028, 90% of hospitals in developed nations will employ "
            "AI-powered clinical decision support systems, fundamentally changing how physicians "
            "diagnose and treat patients.",
            relevance_score=0.70,
        ),
    ]


@pytest.fixture
def sample_research_result(sample_sources):
    """A complete ResearchResult fixture."""
    return ResearchResult(
        query="AI in healthcare",
        sources=sample_sources,
        summary="AI is revolutionizing healthcare through improved diagnostics, drug discovery, "
        "and clinical decision support. The market is projected to reach $187.95B by 2030. "
        "Key advances include ML algorithms achieving 94.5% accuracy in cancer detection "
        "and AI reducing drug discovery timelines from 4.5 years to 18 months.",
        key_findings=[
            "Global AI healthcare market projected at $187.95B by 2030",
            "ML algorithms achieve 94.5% accuracy in early cancer detection",
            "AI reduces drug discovery timeline from 4.5 years to 18 months",
            "90% of hospitals expected to use AI clinical decision support by 2028",
            "Key challenges: data privacy (HIPAA), algorithmic bias, regulatory frameworks",
        ],
        raw_snippets=[s.snippet for s in sample_sources],
        search_queries_used=[
            "AI in healthcare trends 2024",
            "machine learning medical diagnosis accuracy",
            "AI drug discovery timeline reduction",
        ],
    )


@pytest.fixture
def sample_blog_content():
    """A sample blog post output."""
    return BlogContent(
        title="AI in Healthcare: How Artificial Intelligence is Revolutionizing Medicine in 2024",
        meta_description="Discover how AI is transforming healthcare with improved diagnostics, "
        "faster drug discovery, and personalized treatment plans. Market projected at $187.95B by 2030.",
        body_markdown="# AI in Healthcare\n\n## Introduction\n\nArtificial intelligence is reshaping..."
        "\n\n## Key Trends\n\n### Improved Diagnostics\n\n..."
        "\n\n## Conclusion\n\nThe future of healthcare is AI-powered.",
        word_count=1500,
        keywords_used=["AI in healthcare", "machine learning diagnosis", "AI drug discovery"],
        seo_score=82.5,
        headers=["AI in Healthcare", "Key Trends", "Improved Diagnostics", "Conclusion"],
    )


@pytest.fixture
def sample_linkedin_content():
    """A sample LinkedIn post output."""
    return LinkedInContent(
        post_text="Did you know AI algorithms now detect cancer with 94.5% accuracy?\n\n"
        "That's not a futuristic prediction. It's happening right now.\n\n"
        "Here's what's changing in healthcare AI:\n\n"
        "1. Drug discovery timelines cut from 4.5 years to 18 months\n"
        "2. $187.95B market projected by 2030\n"
        "3. 90% of hospitals will use AI decision support by 2028\n\n"
        "The question isn't IF AI will transform healthcare.\n"
        "It's whether your organization is ready.\n\n"
        "What's your take? Drop a comment below.",
        hashtags=["#AIinHealthcare", "#HealthTech", "#MachineLearning", "#DigitalHealth", "#Innovation"],
        hook_type="statistic",
        character_count=520,
    )


@pytest.fixture
def sample_state(sample_research_result) -> ContentState:
    """A pre-populated ContentState for mid-workflow testing."""
    return ContentState(
        user_query="Write a blog post about AI in healthcare",
        intent="blog",
        target_topic="AI in healthcare",
        target_keywords=["AI in healthcare", "machine learning diagnosis"],
        research_results=sample_research_result,
        errors=[],
        processing_log=["query_handler", "deep_research"],
    )


@pytest.fixture
def mock_llm_response():
    """Factory for creating mock LLM responses."""

    def _make(content: str, model: str = "gpt-4o", provider: str = "openai"):
        return LLMResponse(
            content=content,
            model=model,
            provider=provider,
            usage={"prompt_tokens": 100, "completion_tokens": 200, "total_tokens": 300},
        )

    return _make


@pytest.fixture
def mock_llm_client(mock_llm_response):
    """A mock LLM client that returns configurable responses."""
    client = AsyncMock()
    client.generate = AsyncMock(
        return_value=mock_llm_response('{"intent": "blog", "topic": "AI in healthcare", "keywords": []}')
    )
    return client


@pytest.fixture
def mock_tavily_response():
    """Realistic Tavily API search response."""
    return {
        "query": "AI in healthcare trends 2024",
        "results": [
            {
                "title": "AI in Healthcare: 2024 Trends and Innovations",
                "url": "https://example.com/ai-healthcare-2024",
                "content": "Artificial intelligence is transforming healthcare through improved diagnostics, "
                "personalized treatment plans, and streamlined administrative processes. "
                "The global AI in healthcare market is projected to reach $187.95 billion by 2030.",
                "score": 0.95,
            },
            {
                "title": "Machine Learning for Medical Diagnosis",
                "url": "https://example.com/machine-learning-diagnosis",
                "content": "Recent studies show ML algorithms achieving 94.5% accuracy in detecting early-stage "
                "cancers from medical imaging, outperforming human radiologists.",
                "score": 0.88,
            },
        ],
    }
