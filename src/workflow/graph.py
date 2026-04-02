"""LangGraph StateGraph definition — the heart of ContentBlitz orchestration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from src.agents.ab_variant_generator import ABVariantGeneratorAgent
from src.agents.content_strategist import ContentStrategistAgent
from src.agents.deep_research import DeepResearchAgent
from src.agents.hallucination_guard import HallucinationGuardAgent
from src.agents.image_generation import ImageGenerationAgent
from src.agents.linkedin_writer import LinkedInWriterAgent
from src.agents.query_handler import QueryHandlerAgent
from src.agents.seo_blog_writer import SEOBlogWriterAgent
from src.core.config import Settings
from src.core.state import ContentState
from src.integrations.circuit_breaker import CircuitBreakerRegistry
from src.integrations.llm_client import LLMClient
from src.integrations.openai_image_client import OpenAIImageClient
from src.integrations.stability_client import StabilityClient
from src.integrations.tavily_client import TavilySearchClient
from src.utils.logging_config import get_logger
from src.workflow.conditions import route_after_content, route_after_research, route_by_intent
from src.workflow.nodes import WorkflowNodes

if TYPE_CHECKING:
    from langgraph.checkpoint.base import BaseCheckpointSaver

logger = get_logger(__name__)


def build_agents(settings: Settings) -> dict:
    """Instantiate all agents with their dependencies.

    A shared CircuitBreakerRegistry is used so that all clients report
    to the same per-provider breakers, preventing cascading failures.
    """
    breakers = CircuitBreakerRegistry(failure_threshold=5, recovery_timeout=60.0)

    llm = LLMClient(settings, breakers=breakers)
    tavily = TavilySearchClient(settings, breakers=breakers)
    dalle = OpenAIImageClient(settings, breakers=breakers)
    stability = StabilityClient(settings, breakers=breakers)

    return {
        "query_handler": QueryHandlerAgent(settings, llm),
        "deep_research": DeepResearchAgent(settings, llm, tavily),
        "seo_blog_writer": SEOBlogWriterAgent(settings, llm),
        "linkedin_writer": LinkedInWriterAgent(settings, llm),
        "image_generation": ImageGenerationAgent(settings, llm, dalle, stability),
        "content_strategist": ContentStrategistAgent(settings, llm),
        "hallucination_guard": HallucinationGuardAgent(settings, llm),
        "ab_variant_generator": ABVariantGeneratorAgent(settings, llm),
    }


def create_checkpointer(settings: Settings) -> "BaseCheckpointSaver":
    """Create the appropriate checkpoint saver based on configuration.

    - If ``settings.redis_url`` is set, returns an ``AsyncRedisSaver`` backed by
      Redis — suitable for production where state must survive restarts.
    - Otherwise, returns an in-memory ``MemorySaver`` (great for local dev and
      tests where persistence isn't needed).

    Returns:
        A LangGraph ``BaseCheckpointSaver`` instance.
    """
    if settings.redis_url:
        try:
            from langgraph.checkpoint.redis.aio import AsyncRedisSaver

            saver = AsyncRedisSaver(redis_url=settings.redis_url)
            logger.info(
                "checkpointer_created",
                backend="redis",
                redis_url=settings.redis_url.split("@")[-1],  # hide credentials
            )
            return saver
        except Exception as exc:
            logger.warning(
                "redis_checkpointer_failed_falling_back_to_memory",
                error=str(exc),
            )

    logger.info("checkpointer_created", backend="memory")
    return MemorySaver()


def build_graph(
    settings: Settings | None = None,
    checkpointer: "BaseCheckpointSaver | None" = None,
):
    """Build and compile the ContentBlitz LangGraph workflow.

    Args:
        settings: Application settings.  Defaults to ``Settings()``.
        checkpointer: Optional pre-built checkpoint saver.  When *None*,
            one is created automatically via :func:`create_checkpointer`
            (Redis when ``redis_url`` is configured, otherwise in-memory).

    Graph topology:
        START → query_handler → [route_by_intent]
          ├─ deep_research → [route_after_research]
          │   ├─ seo_blog_writer → [route_after_content] → hallucination_guard → ab_variant_generator → END
          │   ├─ linkedin_writer → [route_after_content] → hallucination_guard → ab_variant_generator → END
          │   └─ content_strategist → END
          └─ image_generation → END

    Returns:
        Compiled LangGraph runnable.
    """
    if settings is None:
        settings = Settings()

    if checkpointer is None:
        checkpointer = create_checkpointer(settings)

    agents = build_agents(settings)
    nodes = WorkflowNodes(agents)

    graph = StateGraph(ContentState)

    # Add all nodes
    graph.add_node("query_handler", nodes.query_handler)
    graph.add_node("deep_research", nodes.deep_research)
    graph.add_node("seo_blog_writer", nodes.seo_blog_writer)
    graph.add_node("linkedin_writer", nodes.linkedin_writer)
    graph.add_node("image_generation", nodes.image_generation)
    graph.add_node("content_strategist", nodes.content_strategist)
    graph.add_node("hallucination_guard", nodes.hallucination_guard)
    graph.add_node("ab_variant_generator", nodes.ab_variant_generator)

    # Entry point
    graph.set_entry_point("query_handler")

    # After query_handler: route by intent
    graph.add_conditional_edges(
        "query_handler",
        route_by_intent,
        {
            "deep_research": "deep_research",
            "image_generation": "image_generation",
        },
    )

    # After deep_research: route to content agent
    graph.add_conditional_edges(
        "deep_research",
        route_after_research,
        {
            "seo_blog_writer": "seo_blog_writer",
            "linkedin_writer": "linkedin_writer",
            "content_strategist": "content_strategist",
        },
    )

    # After content generation: route to fact-check or end
    graph.add_conditional_edges(
        "seo_blog_writer",
        route_after_content,
        {
            "hallucination_guard": "hallucination_guard",
            "__end__": END,
        },
    )

    graph.add_conditional_edges(
        "linkedin_writer",
        route_after_content,
        {
            "hallucination_guard": "hallucination_guard",
            "__end__": END,
        },
    )

    # hallucination_guard → ab_variant_generator → END
    graph.add_edge("hallucination_guard", "ab_variant_generator")

    # Terminal nodes
    graph.add_edge("content_strategist", END)
    graph.add_edge("image_generation", END)
    graph.add_edge("ab_variant_generator", END)

    logger.info("workflow_graph_built", nodes=8, agents=len(agents))

    return graph.compile(checkpointer=checkpointer)
